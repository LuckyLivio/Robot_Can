from recovery.recovery_controller import RecoveryController,Config
from reproduction.improvement_v6_20261015_01.recovery.recovery_controller import RecoveryController as V6,Config as C6
from reproduction.improvement_v7_20261015_01.recovery.recovery_controller import RecoveryController as V7,Config as C7
VERSIONS=['v6','v7','geometry','retreat','v8']
def controller_class(version):
    if version=='v6':return V6,C6
    if version=='v7':return V7,C7
    assert version in VERSIONS
    return RecoveryController,Config
