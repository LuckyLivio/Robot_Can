from recovery.recovery_controller import RecoveryController,Config
from reproduction.improvement_v13_20261016_01.recovery.recovery_controller import RecoveryController as V13,Config as C13
from reproduction.improvement_v6_20261015_01.recovery.recovery_controller import RecoveryController as V6,Config as C6
VERSIONS=['v6','v13','track','clearance','v14']
def controller_class(version):
    if version=='v6':return V6,C6
    if version=='v13':return V13,C13
    assert version in VERSIONS
    return RecoveryController,Config
