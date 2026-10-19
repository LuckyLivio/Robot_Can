"""Observed achieved-delta pose feedback with bounded, committed memory.

The certificate covers the Cartesian product of a straight translation segment
and a sampled orientation arc, not merely the two endpoints or separate pure
moves. Rotation-sample margins are reduced by a radius-based arc displacement
bound. This covers any relative timing of those two nominal motions. It does
not certify unbounded controller tracking error, queued unknown motion, changing
object poses, force closure or full-arm collision safety. Recheck each control
step and retain the caller's joint/pose/hold/aperture/age/timeout protections.

No simulator, case identity, contact, reward, success or future-state input.
No phase, clock, queue or settling-counter mutation. ServoState changes only
after the caller commits the exact certified action it actually submits.
"""
import numpy as np
from scipy.spatial.transform import Rotation
from reproduction.improvement_v9_20261015_01.recovery.geometry import LOCAL, CENTERS, HALVES
from reproduction.improvement_v11_20261015_01.recovery.object_clearance import object_margin
from reproduction.improvement_v15_20261016_01.recovery.carry_path import HeldEnvelope

BOX_MARGIN_M = .001
EXECUTION_CAN_MARGIN_M = .001
PLANNING_CAN_MARGIN_M = .003
MAX_TRANSLATION_M = .035
MAX_ROTATION_RAD = .15
MAX_ROTATION_INTERVAL_RAD = .08
MAX_WORK_UNITS = 16
NUMERICAL_PADDING_M = 1e-8
BIAS_LIMIT_M = .009
BIAS_GAIN_PER_CONTROL = .1
NEAR_POSITION_M = .06


class ServoState:
    """Small feedback memory, never controller timing or a simulator cache."""
    def __init__(self):
        self.reset()

    def reset(self):
        self.phase = None
        self.held = None
        self.goal = None
        self.rotation = None
        self.bias = np.zeros(3)
        self.last_action = None

    def commit(self, action, receipt):
        """Commit only a receipt's exact accepted float32 action; else reset.

        Returns False for a guard-replaced or rejected command, without storing
        its proposed bias. Call once after all parent guards and pulses.
        """
        action = np.asarray(action)
        expected = receipt.get('submitted_action')
        update = receipt.get('state_update')
        if (not receipt.get('accepted') or expected is None or update is None
                or action.shape != (7,) or not np.array_equal(action, np.asarray(expected))):
            self.reset()
            return False
        self.phase = update['phase']
        self.held = bool(update['held'])
        self.goal = np.asarray(update['goal'], float).copy()
        self.rotation = np.asarray(update['rotation'], float).copy()
        self.bias = np.asarray(update['bias'], float).copy()
        self.last_action = action.astype(np.float32).copy()
        return True


def observed_motion(x, previous):
    """Per-control observed displacement in world coordinates, not m/s."""
    if previous is None:
        return np.zeros(6)
    x, previous = np.asarray(x, float), np.asarray(previous, float)
    if x.shape != (23,) or previous.shape != (23,) or not np.isfinite(np.r_[x, previous]).all():
        raise ValueError('Motion requires two finite 23-dimensional observations')
    current_r = Rotation.from_quat(x[3:7]).as_matrix()
    previous_r = Rotation.from_quat(previous[3:7]).as_matrix()
    return np.r_[x[:3]-previous[:3], Rotation.from_matrix(current_r @ previous_r.T).as_rotvec()]


def _cap(vector, maximum):
    vector = np.asarray(vector, float)
    return vector * min(1., maximum/max(float(np.linalg.norm(vector)), 1e-15))


def _rotation_valid(rotation):
    return (rotation.shape == (3, 3) and np.isfinite(rotation).all()
            and np.max(np.abs(rotation @ rotation.T-np.eye(3))) < 1e-6
            and abs(np.linalg.det(rotation)-1.) < 1e-6)


def _rotation_grid(rotation, vector):
    angle = float(np.linalg.norm(vector))
    intervals = max(1, int(np.ceil(angle/MAX_ROTATION_INTERVAL_RAD)))
    fractions = [0.] if angle <= 1e-12 else np.linspace(0., 1., intervals+1)
    samples = [Rotation.from_rotvec(vector*fraction).as_matrix() @ rotation for fraction in fractions]
    return samples, angle, intervals


def arc_displacement_bound(radius, angle, intervals):
    """Nearest-sample distance: 2*r*sin(half interval angle / 2)."""
    if not np.isfinite([radius, angle]).all() or radius < 0 or not 0 <= angle <= np.pi or intervals < 1:
        raise ValueError('Invalid bounded rotation arc')
    return float(2*radius*np.sin(angle/(4*intervals)))


def _hand_box_translation_envelope(start, end, rotation, maximum_gap):
    """One separating-plane check including the entire 0..gap aperture range.

    Taking independent extrema of translation and finger displacement gives
    the convex Minkowski envelope. Checking aperture endpoints separately could
    otherwise use different separators while missing an intermediate opening.
    Missing additional SAT axes only makes this check conservative.
    """
    worst = float('inf')
    displacement = end-start
    for name, vertices, normals, edges in LOCAL:
        world_vertices, world_edges = vertices @ rotation.T, edges @ rotation.T
        axes = np.r_[np.eye(3), normals @ rotation.T, np.cross(world_edges, displacement),
                     np.cross(world_edges[:, None, :], np.eye(3)[None, :, :]).reshape(-1, 3)]
        lengths = np.linalg.norm(axes, axis=1)
        axes = axes[lengths > 1e-8]/lengths[lengths > 1e-8, None]
        # Do not round unit axes: the arc-displacement deduction uses unit normals.
        projection = world_vertices @ axes.T
        centers, radii = CENTERS @ axes.T, HALVES @ np.abs(axes).T
        y_projection = rotation[:, 1] @ axes.T
        sign = 1. if 'finger1' in name else (-1. if 'finger2' in name else 0.)
        shifts = np.array([sign*(-.06)/2, sign*(maximum_gap-.06)/2])[:, None]*y_projection
        low = projection.min(0)+np.minimum(start @ axes.T, end @ axes.T)+shifts.min(0)
        high = projection.max(0)+np.maximum(start @ axes.T, end @ axes.T)+shifts.max(0)
        margins = np.max(np.maximum(low[None, :]-centers-radii, centers-radii-high[None, :]), axis=1)
        worst = min(worst, float(margins.min()))
        if worst < BOX_MARGIN_M:
            return worst
    return worst


def mixed_certificate(x, translation, rotation_vector, *, held=False,
                      can_margin_m=EXECUTION_CAN_MARGIN_M, work_limit=MAX_WORK_UNITS,
                      aperture_motion=False):
    """Certify one capped nominal mixed step using at most six geometry units.

    For each orientation sample, both entire translation endpoints are passed
    to the existing convex swept-shape test. Its separating margin then loses
    the largest distance of any rotating point to its nearest sampled pose.
    Thus all translations along the segment and all orientations on the arc
    are covered together, including asynchronous linear/rotation progression.
    A positive separator is sufficient; rejection need not imply a collision.
    """
    if can_margin_m not in (EXECUTION_CAN_MARGIN_M, PLANNING_CAN_MARGIN_M):
        raise ValueError('Keep the original fixed 1 mm execution / 3 mm planning can margins')
    if not isinstance(work_limit, int) or not 0 <= work_limit <= MAX_WORK_UNITS:
        raise ValueError('Geometry budget must be an integer from 0 to 16')
    x = np.asarray(x, float)
    delta, turn = np.asarray(translation, float), np.asarray(rotation_vector, float)
    receipt = {'kind': 'mixed_pose', 'accepted': False, 'held': bool(held), 'work_units': 0, 'work': 0,
               'box_margin_m': None, 'can_margin_m': None,
               'required_can_margin_m': BOX_MARGIN_M if held else can_margin_m,
               'required_hand_box_margin_m': BOX_MARGIN_M,
               'required_second_margin_m': BOX_MARGIN_M if held else can_margin_m,
               'certificate_scope': 'Current-observation straight-segment x orientation-arc envelope; excludes tracking/queued-motion uncertainty and full arm',
               'samples': [], 'arc_bounds_applied': True,
               'aperture_motion': bool(aperture_motion)}
    if held and aperture_motion:
        return {**receipt, 'reason': 'held_aperture_opening_requires_separate_release_control'}
    if (x.shape != (23,) or delta.shape != (3,) or turn.shape != (3,)
            or not np.isfinite(np.r_[x, delta, turn]).all()):
        return {**receipt, 'reason': 'invalid_nonfinite_or_shape_input'}
    if (np.linalg.norm(delta) > MAX_TRANSLATION_M+1e-12
            or np.linalg.norm(turn) > MAX_ROTATION_RAD+1e-12):
        return {**receipt, 'reason': 'command_exceeds_unchanged_motion_caps'}
    try:
        rotation = Rotation.from_quat(x[3:7]).as_matrix()
        Rotation.from_quat(x[19:23])
    except ValueError:
        return {**receipt, 'reason': 'invalid_observed_quaternion'}
    observed_gap = abs(float(x[7]-x[8]))
    if observed_gap > .085:
        return {**receipt, 'reason': 'observed_aperture_outside_bounded_geometry'}
    # While empty and adjusting aperture, include the entire legal range,
    # not just a guessed pulse increment. Panda's hidden gripper target and
    # in-flight D2 pulses cannot then escape this nominal aperture envelope.
    gap = .085 if aperture_motion else min(.085, observed_gap+.002)
    gaps = [0., .085] if aperture_motion else [max(0., observed_gap-.002), min(.085, observed_gap+.002)]
    receipt['aperture_range_m'] = gaps
    if gaps[0] > gaps[1]:
        return {**receipt, 'reason': 'observed_aperture_outside_bounded_geometry'}
    samples, angle, intervals = _rotation_grid(rotation, turn)
    required_work = 2*len(samples)
    if required_work > work_limit:
        return {**receipt, 'reason': 'geometry_budget_insufficient', 'required_work_units': required_work}
    # v11's .03 padding covers the closed-to-open finger shift in sweep_margin.
    hand_radius = max(float(np.linalg.norm(v, axis=1).max()) for _, v, _, _ in LOCAL)+abs(gap-.06)/2+.03
    hand_bound = arc_displacement_bound(hand_radius, angle, intervals)+NUMERICAL_PADDING_M
    envelope = HeldEnvelope.from_state(x) if held else None
    can_radius = float(np.linalg.norm(envelope.vertices, axis=1).max()) if held else None
    can_bound = arc_displacement_bound(can_radius, angle, intervals)+NUMERICAL_PADDING_M if held else hand_bound
    end = x[:3]+delta
    for sample in samples:
        hand_margin = _hand_box_translation_envelope(x[:3], end, sample, gap)-hand_bound
        receipt['work_units'] += 1
        if held:
            second_margin = envelope.sweep_margin(x[:3], end, sample)-can_bound
        else:
            second_margin = float(object_margin(x[:3], end, sample, gaps, x))-hand_bound
        receipt['work_units'] += 1
        receipt['samples'].append({'hand_margin_m': hand_margin,
                                    'carried_can_margin_m' if held else 'can_margin_m': second_margin})
    second_key = 'carried_can_margin_m' if held else 'can_margin_m'
    receipt.update(hand_margin_m=min(row['hand_margin_m'] for row in receipt['samples']),
                   **{second_key: min(row[second_key] for row in receipt['samples'])},
                   rotation_samples=len(samples), translation_m=delta.tolist(), rotation_vector_rad=turn.tolist(),
                   hand_arc_bound_m=hand_bound, second_arc_bound_m=can_bound,
                   whole_translation_sweep_at_each_orientation=True)
    receipt.update(work=receipt['work_units'], box_margin_m=receipt['hand_margin_m'],
                   can_margin_m=receipt[second_key])
    receipt['accepted'] = bool(receipt['hand_margin_m'] >= BOX_MARGIN_M
                               and receipt[second_key] >= receipt['required_second_margin_m'])
    receipt['reason'] = 'mixed_envelope_validated' if receipt['accepted'] else 'mixed_envelope_clearance_unconfirmed'
    return receipt


def _quantized_action(delta, turn, grip, max_delta, max_rotation):
    """Return the actual float32 command and certify its decoded physical step."""
    action = np.r_[delta/.05, turn/.5, grip].astype(np.float32)
    for section, unit, cap in [(slice(0, 3), .05, max_delta), (slice(3, 6), .5, max_rotation)]:
        length = np.linalg.norm(action[section].astype(float)*unit)
        if length > cap:
            action[section] *= cap/length*(1.-1e-6)
    return action


def certify_action(x, action, *, held=False, aperture_motion=False,
                   can_margin_m=EXECUTION_CAN_MARGIN_M, work_limit=MAX_WORK_UNITS):
    """Certify the actual submitted delta command, including a grip pulse.

    Nonzero empty-hand grip requires the full 0..85 mm aperture envelope.
    Held closing keeps the observed rigid-can envelope; release is a separate
    phase. The product certificate remains nominal, not a dynamics proof.
    """
    action = np.asarray(action, np.float32)
    if action.shape != (7,) or not np.isfinite(action).all() or np.abs(action).max() > 1:
        return {'kind': 'mixed_pose', 'accepted': False, 'held': bool(held), 'work': 0,
                'work_units': 0, 'reason': 'invalid_submitted_action'}
    if not held and action[6] != 0 and not aperture_motion:
        return {'kind': 'mixed_pose', 'accepted': False, 'held': False, 'work': 0,
                'work_units': 0, 'reason': 'empty_grip_pulse_requires_full_aperture_certificate'}
    if held and action[6] < 0:
        return {'kind': 'mixed_pose', 'accepted': False, 'held': True, 'work': 0,
                'work_units': 0, 'reason': 'held_open_command_requires_separate_release_control'}
    receipt = mixed_certificate(x, action[:3].astype(float)*.05, action[3:6].astype(float)*.5,
                                held=held, aperture_motion=aperture_motion,
                                can_margin_m=can_margin_m, work_limit=work_limit)
    receipt['submitted_action'] = action.tolist()
    receipt['grip_command'] = float(action[6])
    return receipt


def propose(x, goal, rotation, motion, cfg, *, held=False, grip=0.,
            can_margin_m=EXECUTION_CAN_MARGIN_M, state=None, phase=None,
            previous_action=None, aperture_motion=False):
    """Certified achieved-delta feedback, with optional bounded residual bias.

    OSC resets its desired pose to the achieved pose plus this action. It
    already damps velocity internally. Near a goal, retain one external
    observed-motion damping term rather than damping a D2 extrapolation again.
    The D2 FIFO and five-frame arrival checks still belong to the caller.
    A <=9 mm integral command bias addresses persistent near-goal error without
    changing the 9 mm success threshold. Bias is proposed, never auto-committed.
    Held command changes are bounded by one third of the unchanged step caps;
    this limits abrupt starts/reversals without reducing steady motion caps.
    Geometry uses full/half/quarter actions, <=14 units in all three trials.
    """
    if cfg.delay != 2 or cfg.max_delta_m > MAX_TRANSLATION_M or cfg.max_rotation_rad > MAX_ROTATION_RAD:
        raise ValueError('v17 pose servo requires unchanged D2 and motion caps')
    if not -1. <= grip <= 1.:
        raise ValueError('Invalid grip command')
    if state is not None and not isinstance(state, ServoState):
        raise TypeError('state must be ServoState or None')
    x, goal, rotation, motion = map(lambda item: np.asarray(item, float), (x, goal, rotation, motion))
    stationary = np.r_[np.zeros(6), grip].astype(np.float32)
    receipt = {'kind': 'mixed_pose', 'accepted': False, 'held': bool(held), 'work_units': 0, 'work': 0, 'trials': [],
               'box_margin_m': None, 'can_margin_m': None,
               'required_can_margin_m': BOX_MARGIN_M if held else can_margin_m,
               'translation_m': [0., 0., 0.], 'rotation_vector_rad': [0., 0., 0.],
               'certificate_scope': 'Current-observation nominal envelope only; not future D2 execution or full-arm safety',
               'delay': 2, 'observation_prediction_only': False,
               'servo_semantics': 'achieved_pose_plus_command',
               'aperture_motion': bool(aperture_motion),
               'settling_and_clock_owned_by_caller': True}
    if (x.shape != (23,) or goal.shape != (3,) or motion.shape != (6,) or not _rotation_valid(rotation)
            or not np.isfinite(np.r_[x, goal, motion]).all()):
        return stationary, {**receipt, 'reason': 'invalid_nonfinite_or_shape_input'}
    try:
        current_r = Rotation.from_quat(x[3:7]).as_matrix()
    except ValueError:
        return stationary, {**receipt, 'reason': 'invalid_observed_quaternion'}
    error = goal-x[:3]
    angle_error = Rotation.from_matrix(rotation @ current_r.T).as_rotvec()
    distance = float(np.linalg.norm(error))
    phase_key = repr(phase)
    reset_reason = None
    bias = np.zeros(3)
    if state is not None:
        if state.goal is None:
            reset_reason = 'new_servo_state'
        elif state.phase != phase_key or state.held != bool(held):
            reset_reason = 'phase_or_held_state_changed'
        elif not np.array_equal(goal, state.goal) or not np.array_equal(rotation, state.rotation):
            reset_reason = 'target_changed'
        elif previous_action is not None and not np.array_equal(np.asarray(previous_action), state.last_action):
            reset_reason = 'interrupted_by_uncertified_command'
        else:
            bias = state.bias.copy()
    near = distance <= NEAR_POSITION_M
    if near and state is not None:
        # Do not preserve bias that now pushes away from the target. This is
        # an anti-windup reset of controller memory, not an arrival decision.
        bias[bias*error < 0] = 0.
        bias = _cap(bias + BIAS_GAIN_PER_CONTROL*error, BIAS_LIMIT_M)
    else:
        bias[:] = 0.
    delta = cfg.position_gain*error + bias
    if near:
        delta -= cfg.tracking_velocity_damping*motion[:3]
    turn = cfg.orientation_gain*angle_error-cfg.tracking_angular_damping*motion[3:]
    delta, turn = _cap(delta, cfg.max_delta_m), _cap(turn, cfg.max_rotation_rad)
    reference = previous_action
    if reference is None and state is not None and reset_reason is None:
        reference = state.last_action
    reference = np.zeros(7) if reference is None else np.asarray(reference, float)
    if reference.shape != (7,) or not np.isfinite(reference).all() or np.abs(reference).max() > 1:
        return stationary, {**receipt, 'reason': 'invalid_previous_submitted_action'}
    if held:
        delta = reference[:3]*.05 + _cap(delta-reference[:3]*.05, cfg.max_delta_m/(cfg.delay+1))
        turn = reference[3:6]*.5 + _cap(turn-reference[3:6]*.5, cfg.max_rotation_rad/(cfg.delay+1))
        delta, turn = _cap(delta, cfg.max_delta_m), _cap(turn, cfg.max_rotation_rad)
    receipt.update(position_error_m=distance,
                   orientation_error_rad=float(np.linalg.norm(angle_error)),
                   observed_translation_per_step_m=motion[:3].tolist(),
                   observed_rotation_per_step_rad=motion[3:].tolist(),
                   position_bias_m=bias.tolist(), bias_limit_m=BIAS_LIMIT_M,
                   bias_gain_per_control=BIAS_GAIN_PER_CONTROL, near_goal_feedback=near,
                   state_reset_reason=reset_reason, previous_submitted_action=reference.tolist(),
                   held_command_slew_limited=bool(held),
                   state_update={'phase': phase_key, 'held': bool(held), 'goal': goal.tolist(),
                                 'rotation': rotation.tolist(), 'bias': bias.tolist()})
    for scale in [1., .5, .25]:
        action = _quantized_action(delta*scale, turn*scale, grip, cfg.max_delta_m, cfg.max_rotation_rad)
        # Scaling toward zero could violate a held slew bound when braking.
        # Such a candidate is not sent; a rejected command remains a guarded
        # stop, which is explicitly outside this voluntary slew protection.
        if held and (np.linalg.norm(action[:3].astype(float)*.05-reference[:3]*.05) > cfg.max_delta_m/3+1e-8
                     or np.linalg.norm(action[3:6].astype(float)*.5-reference[3:6]*.5) > cfg.max_rotation_rad/3+1e-8):
            receipt['trials'].append({'scale': scale, 'accepted': False, 'work': 0,
                                      'work_units': 0, 'reason': 'held_command_slew_unconfirmed'})
            continue
        certificate = certify_action(x, action, held=held, aperture_motion=aperture_motion,
                                     can_margin_m=can_margin_m,
                                     work_limit=MAX_WORK_UNITS-receipt['work_units'])
        receipt['work_units'] += certificate['work_units']
        receipt['work'] = receipt['work_units']
        receipt['trials'].append({'scale': scale, **certificate})
        if certificate['accepted']:
            receipt.update(accepted=True, reason='achieved_delta_feedback_step_validated', selected_scale=scale,
                           box_margin_m=certificate['box_margin_m'],
                           translation_m=certificate['translation_m'], rotation_vector_rad=certificate['rotation_vector_rad'],
                           hand_margin_m=certificate['hand_margin_m'],
                           submitted_action=action.tolist(), grip_command=float(action[6]),
                           aperture_range_m=certificate['aperture_range_m'],
                           **{key: certificate[key] for key in ['can_margin_m','carried_can_margin_m'] if key in certificate})
            assert receipt['work_units'] <= MAX_WORK_UNITS
            return action, receipt
    assert receipt['work_units'] <= MAX_WORK_UNITS
    return stationary, {**receipt, 'reason': 'no_certified_mixed_step'}
