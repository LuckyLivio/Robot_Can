"""Observation-only pose and support-domain checks. No simulator queries."""
import numpy as np
from scipy.spatial.transform import Rotation
from reproduction.recovery_v5_20261012_01.clearance import side_cell

def axis(pose):
    return Rotation.from_quat(np.asarray(pose)[3:7]).as_matrix()[:,2]

def difference(a,b):
    # Rotation about a cylinder's own axis does not invalidate this grasp family.
    distance=float(np.linalg.norm(np.asarray(a)[:3]-np.asarray(b)[:3]))
    angle=float(np.arccos(np.clip(axis(a)@axis(b),-1.,1.)))
    return distance,angle

def feasibility(controller,x):
    a=axis(x[16:23]);up=controller.resting_cell(x)
    side=side_cell(x[16:19],a,controller.floor)
    if up is None and side is None:return 'unknown','pose_outside_supported_region'
    if controller.guard_scope and not controller.plan_ok:return 'infeasible','no_feasible_candidate'
    expected='sideways' if abs(a[2])<controller.cfg.sideways_axis_z else 'upright'
    if controller.grasp_kind!=expected:return 'unknown','grasp_family_stale'
    return 'feasible','validated_narrow_plan' if controller.guard_scope else 'supported_legacy_plan'
