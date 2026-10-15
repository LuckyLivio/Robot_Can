from recovery.recovery_controller import RecoveryController,Config
from reproduction.improvement_v10_20261015_01.recovery.recovery_controller import RecoveryController as V10,Config as C10
VERSIONS=['v10','axis','guard','v11']
def controller_class(version):
    if version=='v10':return V10,C10
    assert version in VERSIONS
    return RecoveryController,Config
