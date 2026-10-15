from recovery.recovery_controller import RecoveryController,Config
from reproduction.improvement_v9_20261015_01.recovery.recovery_controller import RecoveryController as V9,Config as C9
VERSIONS=['v9','height','path','v10']
def controller_class(version):
    if version=='v9':return V9,C9
    assert version in VERSIONS
    return RecoveryController,Config
