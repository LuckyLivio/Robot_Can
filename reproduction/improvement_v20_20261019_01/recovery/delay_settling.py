"""Target-band conditional integration for the unchanged held D2 servo.

The position tolerance remains the caller's strict 9 mm sphere with five observed
frames. A 9 mm / sqrt(3) axis band is only an integral-control heuristic: an axis
being within that band does not imply 3D arrival or a future state certificate.
No error extrapolation is added to P, and the one original motion damping term
is unchanged. Existing mixed geometry, slew, exact commit and reset semantics
are reused. No new FIFO, simulator, clock, counter, or feedback state.
"""
import numpy as np
from scipy.spatial.transform import Rotation
from reproduction.improvement_v17_20261019_01.recovery.pose_servo import (
    ServoState, EXECUTION_CAN_MARGIN_M, BOX_MARGIN_M, MAX_TRANSLATION_M,
    MAX_ROTATION_RAD, MAX_WORK_UNITS, BIAS_LIMIT_M, BIAS_GAIN_PER_CONTROL,
    NEAR_POSITION_M, _cap, _rotation_valid, _quantized_action, certify_action,
)


ARRIVAL_POSITION_M = .009
AXIS_CAPTURE_BAND_M = ARRIVAL_POSITION_M / np.sqrt(3.)


def propose(x, goal, rotation, motion, cfg, *, held=False, grip=0.,
            can_margin_m=EXECUTION_CAN_MARGIN_M, state=None, phase=None,
            previous_action=None, aperture_motion=False):
    """Certified held feedback with target-band conditional integration.

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
    brake_axes = np.zeros(3, dtype=bool)
    capture_axes = np.zeros(3, dtype=bool)
    pause_axes = np.zeros(3, dtype=bool)
    inside_position_ball = False
    nominal_error_after_delay = error-cfg.delay*motion[:3]
    if near and state is not None:
        # First preserve the inherited sign-reset: a bias opposing the current
        # target error is discarded before considering either brake rule.
        bias[bias*error < 0] = 0.
        if held:
            # Retain the exact v19 event predicate and its original meaning.
            brake_axes = ((error*motion[:3] > 0)
                          & (error*nominal_error_after_delay <= 0))
            # Earlier anti-windup only: the target-band lookahead does not
            # replace the actual error used by P or add another damping term.
            capture_axes = ((error*motion[:3] > 0)
                            & (np.abs(error) <= AXIS_CAPTURE_BAND_M+cfg.delay*np.abs(motion[:3])))
            inside_position_ball = bool(distance < ARRIVAL_POSITION_M)
            pause_axes = capture_axes | inside_position_ball
        if pause_axes.any():
            # Approaching axes are cleared. Other axes keep their surviving
            # bias (including a bias braking away-going motion), but no axis
            # acquires fresh integral while actually inside the old 9 mm ball.
            bias[capture_axes] = 0.
            increment = BIAS_GAIN_PER_CONTROL*error
            increment[pause_axes] = 0.
            bias = _cap(bias+increment, BIAS_LIMIT_M)
        else:
            # Preserve v19 arithmetic exactly for every untriggered control.
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
    if brake_axes.any():
        receipt['settling19'] = {
            'triggered': True, 'integral_brake_axes': brake_axes.tolist(),
            'nominal_error_after_delay_m': nominal_error_after_delay.tolist(),
            'control_heuristic_only': True,
            'scope': 'Current error and observed displacement only; not future geometry or readiness',
            'arrival_thresholds_and_counters_unchanged': True,
        }
    if pause_axes.any():
        receipt['braking20'] = {
            'triggered': True,
            'capture_brake_axes': capture_axes.tolist(),
            'original_crossing_axes': brake_axes.tolist(),
            'integral_pause_axes': pause_axes.tolist(),
            'inside_original_position_ball': inside_position_ball,
            'axis_capture_band_m': AXIS_CAPTURE_BAND_M,
            'original_arrival_position_m': ARRIVAL_POSITION_M,
            'delay_controls': cfg.delay,
            'current_error_m': error.tolist(),
            'observed_motion_per_control_m': motion[:3].tolist(),
            'integral_order': 'original_sign_reset_then_capture_clear_then_pause_or_increment_then_original_norm_cap',
            'retained_bias_scope': 'Surviving non-capture bias is retained; inside the ball every new increment is paused.',
            'control_heuristic_only': True,
            'no_error_extrapolation_or_additional_damping': True,
            'arrival_thresholds_and_counters_unchanged': True,
        }
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
