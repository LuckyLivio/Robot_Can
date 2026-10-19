"""Preserve v19 entry feedback and extend only risk-direction feedback.

The caller owns all phase/pose/aperture/joint/timeout/arrival checks and the D2
FIFO. This helper uses only the current observation, measured past motion and
the previous nominal command actually submitted by the controller. It neither
inherits an approach integral bias nor predicts the queue's physical outcome.
Rejection is a guarded stop, explicitly outside the voluntary slew bound; a
nonzero returned grip still requires the caller's original aperture policy.
"""
import numpy as np
from scipy.spatial.transform import Rotation
from reproduction.improvement_v17_20261019_01.recovery.pose_servo import (
    certify_action, _cap, _quantized_action, _rotation_valid,
    MAX_TRANSLATION_M, MAX_ROTATION_RAD, MAX_WORK_UNITS,
)


def propose(x, goal, rotation, motion, cfg, previous_action, grip=0., aperture_motion=False, *,
            descent_controls, descent_axis):
    """Return a final-float32 certified command, without mutating any input.

    Existing DESCEND age 1..3 uses the exact original v19 expression for
    full translation and rotation damping. Later controls retain only the
    original damping in an axial direction that is moving away or nominally
    crosses its goal, and in a lateral direction that moves outward/tangentially
    or nominally crosses its center. Normal progress retains the proportional
    law. This includes return from recenter without restarting the phase age.
    These are current-observation feedback heuristics, never future states,
    clearance proofs, or readiness decisions. Axis sign is irrelevant.

    Every direction and phase age retains motion caps, slew and geometry. Cap each
    command, then bound its change from the preceding submitted command by
    max_delta/(D2+1) and max_rotation/(D2+1). Each full/half/quarter candidate
    must still satisfy those changes after quantization. Geometry covers the
    entire translation x rotation nominal product, plus full aperture range
    whenever opening/closing may be in flight. Total geometry work is <=16.
    """
    try:valid_grip=bool(np.isscalar(grip) and np.isfinite(float(grip)) and -1.<=float(grip)<=1.)
    except (TypeError,ValueError):valid_grip=False
    stationary=np.r_[np.zeros(6),float(grip) if valid_grip else 0.].astype(np.float32)
    receipt={'kind':'mixed_pose','accepted':False,'held':False,'work':0,'work_units':0,'trials':[],
             'box_margin_m':None,'can_margin_m':None,'required_can_margin_m':.001,
             'required_hand_box_margin_m':.001,'required_second_margin_m':.001,
             'translation_m':[0.,0.,0.],'rotation_vector_rad':[0.,0.,0.],
             'handoff_feedback':True,'servo_bias_used':False,'delay':2,
             'aperture_motion':bool(aperture_motion),'settling_and_clock_owned_by_caller':True,
             'certificate_scope':'Current-observation nominal mixed envelope only; excludes unknown D2/noise tracking, moving object, and full-arm safety',
             'previous_reference_scope':'Last controller-submitted nominal command, not measured or predicted delayed execution',
             'rejected_fallback_scope':'Guarded zero pose may exceed voluntary slew bound; caller retains original aperture-pulse safeguards'}
    if not valid_grip:return stationary,{**receipt,'reason':'invalid_grip_command'}
    if (isinstance(descent_controls, (bool, np.bool_)) or not isinstance(descent_controls, (int, np.integer))
            or descent_controls < 1):
        return stationary,{**receipt,'reason':'invalid_existing_descent_age'}
    window = descent_controls <= cfg.delay+1
    receipt['handoff21'] = {'descent_controls':int(descent_controls),
                              'entry_window_active':bool(window),
                              'entry_window_controls':3,'nominal_forecast_only':True,
                              'scope':'Preserve exact v19 entry law; extend only risk-direction feedback afterwards. Existing phase age includes holds. No clock/queue/ready mutation.'}
    try:
        x,goal,rotation,motion,reference,axis=[np.asarray(v,float) for v in [x,goal,rotation,motion,previous_action,descent_axis]]
    except (TypeError,ValueError):
        return stationary,{**receipt,'reason':'invalid_nonfinite_or_shape_input'}
    if (x.shape!=(23,) or goal.shape!=(3,) or motion.shape!=(6,) or reference.shape!=(7,)
            or not _rotation_valid(rotation) or not np.isfinite(np.r_[x,goal,motion,reference]).all()):
        return stationary,{**receipt,'reason':'invalid_nonfinite_or_shape_input'}
    if (axis.shape!=(3,) or not np.isfinite(axis).all()
            or abs(float(np.linalg.norm(axis))-1.)>=1e-6
            or min(float(np.linalg.norm(axis-rotation[:,2])),float(np.linalg.norm(axis+rotation[:,2])))>=1e-6):
        return stationary,{**receipt,'reason':'invalid_or_unaligned_descent_axis'}
    if np.abs(reference).max()>1:
        return stationary,{**receipt,'reason':'invalid_previous_submitted_action'}
    values=np.array([cfg.max_delta_m,cfg.max_rotation_rad,cfg.position_gain,cfg.orientation_gain,
                     cfg.tracking_velocity_damping,cfg.tracking_angular_damping],float)
    if (cfg.delay!=2 or not np.isfinite(values).all() or np.any(values<0)
            or cfg.max_delta_m<=0 or cfg.max_rotation_rad<=0
            or cfg.max_delta_m>MAX_TRANSLATION_M or cfg.max_rotation_rad>MAX_ROTATION_RAD
            or cfg.tracking_velocity_damping!=1.5 or cfg.tracking_angular_damping!=.3):
        return stationary,{**receipt,'reason':'unchanged_delay_caps_or_damping_required'}
    try:r=Rotation.from_quat(x[3:7]).as_matrix()
    except ValueError:return stationary,{**receipt,'reason':'invalid_observed_quaternion'}
    error=goal-x[:3];angle_error=Rotation.from_matrix(rotation@r.T).as_rotvec()
    raw_delta=cfg.position_gain*error
    raw_turn=cfg.orientation_gain*angle_error
    axial_error=float(np.dot(error,axis));axial_motion=float(np.dot(motion[:3],axis))
    lateral_error=error-axis*axial_error;lateral_motion=motion[:3]-axis*axial_motion
    axial_forecast=axial_error-cfg.delay*axial_motion
    lateral_forecast=lateral_error-cfg.delay*lateral_motion
    lateral_closing=float(np.dot(lateral_error,lateral_motion))
    lateral_crossing=float(np.dot(lateral_error,lateral_forecast))
    lateral_moving=bool(np.dot(lateral_motion,lateral_motion)>0.)
    axial_away=bool(axial_error*axial_motion<0.)
    axial_crossed=bool(axial_error*axial_motion>0. and axial_error*axial_forecast<=0.)
    lateral_away=bool(lateral_moving and lateral_closing<=0.)
    lateral_crossed=bool(lateral_moving and lateral_crossing<=0.)
    axial_feedback=bool(window or axial_away or axial_crossed)
    lateral_feedback=bool(window or lateral_away or lateral_crossed)
    if window:
        # Preserve operation order as well as coefficients: entry commands
        # must be bitwise identical to the actual v19 parent after quantization.
        raw_delta=raw_delta-cfg.tracking_velocity_damping*motion[:3]
        raw_turn=raw_turn-cfg.tracking_angular_damping*motion[3:]
    else:
        if axial_feedback:raw_delta=raw_delta-cfg.tracking_velocity_damping*axis*axial_motion
        if lateral_feedback:raw_delta=raw_delta-cfg.tracking_velocity_damping*lateral_motion
    receipt['handoff21'].update(axis=axis.tolist(),axial_error_m=axial_error,
        axial_motion_m=axial_motion,lateral_error_m=lateral_error.tolist(),
        lateral_motion_m=lateral_motion.tolist(),axial_feedback=axial_feedback,
        lateral_feedback=lateral_feedback,axial_moving_away=axial_away,
        lateral_moving_away_or_tangential=lateral_away,
        lateral_nominal_crossing=lateral_crossed,axial_nominal_crossing=axial_crossed,
        axial_nominal_error_after_delay_m=axial_forecast,
        lateral_nominal_error_after_delay_m=lateral_forecast.tolist(),
        lateral_closing_dot_m2=lateral_closing,lateral_nominal_crossing_dot_m2=lateral_crossing)
    delta,turn=_cap(raw_delta,cfg.max_delta_m),_cap(raw_turn,cfg.max_rotation_rad)
    linear_slew=cfg.max_delta_m/(cfg.delay+1);angular_slew=cfg.max_rotation_rad/(cfg.delay+1)
    previous_delta,previous_turn=reference[:3]*.05,reference[3:6]*.5
    delta=previous_delta+_cap(delta-previous_delta,linear_slew)
    turn=previous_turn+_cap(turn-previous_turn,angular_slew)
    delta,turn=_cap(delta,cfg.max_delta_m),_cap(turn,cfg.max_rotation_rad)
    receipt.update(position_error_m=float(np.linalg.norm(error)),orientation_error_rad=float(np.linalg.norm(angle_error)),
                   previous_submitted_action=reference.tolist(),position_slew_limit_m=linear_slew,
                   rotation_slew_limit_rad=angular_slew,raw_translation_m=raw_delta.tolist(),raw_rotation_rad=raw_turn.tolist(),
                   observed_translation_per_step_m=motion[:3].tolist(),observed_rotation_per_step_rad=motion[3:].tolist())
    for scale in [1.,.5,.25]:
        action=_quantized_action(delta*scale,turn*scale,grip,cfg.max_delta_m,cfg.max_rotation_rad)
        change=float(np.linalg.norm(action[:3].astype(float)*.05-previous_delta))
        turn_change=float(np.linalg.norm(action[3:6].astype(float)*.5-previous_turn))
        if change>linear_slew+1e-8 or turn_change>angular_slew+1e-8:
            receipt['trials'].append({'scale':scale,'accepted':False,'work':0,'work_units':0,
                                      'reason':'submitted_command_slew_unconfirmed',
                                      'translation_change_m':change,'rotation_change_rad':turn_change})
            continue
        certificate=certify_action(x,action,held=False,aperture_motion=aperture_motion,
                                   can_margin_m=.001,work_limit=MAX_WORK_UNITS-receipt['work'])
        receipt['work']+=certificate['work'];receipt['work_units']=receipt['work']
        receipt['trials'].append({'scale':scale,**certificate})
        if certificate['accepted']:
            receipt.update(accepted=True,reason='entry_preserving_directional_descent_validated',selected_scale=scale,
                           submitted_action=action.tolist(),grip_command=float(action[6]),
                           box_margin_m=certificate['box_margin_m'],can_margin_m=certificate['can_margin_m'],
                           hand_margin_m=certificate['hand_margin_m'],aperture_range_m=certificate['aperture_range_m'],
                           translation_m=certificate['translation_m'],rotation_vector_rad=certificate['rotation_vector_rad'],
                           translation_change_m=change,rotation_change_rad=turn_change)
            assert receipt['work']<=MAX_WORK_UNITS
            return action,receipt
    assert receipt['work']<=MAX_WORK_UNITS
    return stationary,{**receipt,'reason':'no_certified_handoff_step'}
