"""Observation-only D2 pose servo with a bounded mixed-motion certificate.

The certificate covers the Cartesian product of a straight translation segment
and a sampled orientation arc, not merely the two endpoints or separate pure
moves. Rotation-sample margins are reduced by a radius-based arc displacement
bound. This covers any relative timing of those two nominal motions. It does
not certify unbounded controller tracking error, queued unknown motion, changing
object poses, force closure or full-arm collision safety. Recheck each control
step and retain the caller's joint/pose/hold/aperture/age/timeout protections.

No simulator, case identity, contact, reward, success or future-state input.
No phase, clock, queue or settling-counter mutation.
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
                      can_margin_m=EXECUTION_CAN_MARGIN_M, work_limit=MAX_WORK_UNITS):
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
               'samples': [], 'arc_bounds_applied': True}
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
    # Same gap envelope used by v14/v15 execution certificates.
    gap = min(.085, observed_gap+.002)
    gaps = [max(0., observed_gap-.002), min(.085, observed_gap+.002)]
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


def propose(x, goal, rotation, motion, cfg, *, held=False, grip=0.,
            can_margin_m=EXECUTION_CAN_MARGIN_M):
    """Propose then certify full, half or quarter damped pose steps (<=14 units).

    D2 constant-observed-motion extrapolation is a controller heuristic, never
    a future observation. Arrival remains the caller's unchanged 9 mm/.08 rad
    and five consecutive valid frames. This helper does not change timeouts.
    On rejection return a zero-pose action preserving the requested grip.
    """
    if cfg.delay != 2 or cfg.max_delta_m > MAX_TRANSLATION_M or cfg.max_rotation_rad > MAX_ROTATION_RAD:
        raise ValueError('v16 pose servo requires unchanged D2 and motion caps')
    if not -1. <= grip <= 1.:
        raise ValueError('Invalid grip command')
    x, goal, rotation, motion = map(lambda item: np.asarray(item, float), (x, goal, rotation, motion))
    stationary = np.r_[np.zeros(6), grip].astype(np.float32)
    receipt = {'kind': 'mixed_pose', 'accepted': False, 'held': bool(held), 'work_units': 0, 'work': 0, 'trials': [],
               'box_margin_m': None, 'can_margin_m': None,
               'required_can_margin_m': BOX_MARGIN_M if held else can_margin_m,
               'translation_m': [0., 0., 0.], 'rotation_vector_rad': [0., 0., 0.],
               'certificate_scope': 'Current-observation nominal envelope only; not future D2 execution or full-arm safety',
               'delay': 2, 'observation_prediction_only': True,
               'settling_and_clock_owned_by_caller': True}
    if (x.shape != (23,) or goal.shape != (3,) or motion.shape != (6,) or not _rotation_valid(rotation)
            or not np.isfinite(np.r_[x, goal, motion]).all()):
        return stationary, {**receipt, 'reason': 'invalid_nonfinite_or_shape_input'}
    try:
        current_r = Rotation.from_quat(x[3:7]).as_matrix()
    except ValueError:
        return stationary, {**receipt, 'reason': 'invalid_observed_quaternion'}
    predicted_position = x[:3]+cfg.delay*motion[:3]
    predicted_rotation = Rotation.from_rotvec(cfg.delay*motion[3:]).as_matrix() @ current_r
    delta = cfg.position_gain*(goal-predicted_position)-cfg.tracking_velocity_damping*motion[:3]
    turn = cfg.orientation_gain*Rotation.from_matrix(rotation @ predicted_rotation.T).as_rotvec()-cfg.tracking_angular_damping*motion[3:]
    delta, turn = _cap(delta, cfg.max_delta_m), _cap(turn, cfg.max_rotation_rad)
    receipt.update(position_error_m=float(np.linalg.norm(goal-x[:3])),
                   orientation_error_rad=float(np.linalg.norm(Rotation.from_matrix(rotation @ current_r.T).as_rotvec())),
                   observed_translation_per_step_m=motion[:3].tolist(),
                   observed_rotation_per_step_rad=motion[3:].tolist(),
                   predicted_position=predicted_position.tolist(),
                   predicted_orientation_error_rad=float(np.linalg.norm(Rotation.from_matrix(rotation @ predicted_rotation.T).as_rotvec())))
    for scale in [1., .5, .25]:
        action = _quantized_action(delta*scale, turn*scale, grip, cfg.max_delta_m, cfg.max_rotation_rad)
        certificate = mixed_certificate(x, action[:3].astype(float)*.05, action[3:6].astype(float)*.5,
                                        held=held, can_margin_m=can_margin_m,
                                        work_limit=MAX_WORK_UNITS-receipt['work_units'])
        receipt['work_units'] += certificate['work_units']
        receipt['work'] = receipt['work_units']
        receipt['trials'].append({'scale': scale, **certificate})
        if certificate['accepted']:
            receipt.update(accepted=True, reason='d2_damped_mixed_step_validated', selected_scale=scale,
                           box_margin_m=certificate['box_margin_m'],
                           translation_m=certificate['translation_m'], rotation_vector_rad=certificate['rotation_vector_rad'],
                           hand_margin_m=certificate['hand_margin_m'],
                           **{key: certificate[key] for key in ['can_margin_m','carried_can_margin_m'] if key in certificate})
            assert receipt['work_units'] <= MAX_WORK_UNITS
            return action, receipt
    assert receipt['work_units'] <= MAX_WORK_UNITS
    return stationary, {**receipt, 'reason': 'no_certified_mixed_step'}
