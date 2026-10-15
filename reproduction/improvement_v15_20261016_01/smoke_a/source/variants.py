from recovery.recovery_controller import RecoveryController,Config
from reproduction.improvement_v14_20261016_01.recovery.recovery_controller import RecoveryController as V14,Config as C14
from reproduction.improvement_v13_20261016_01.recovery.recovery_controller import RecoveryController as V13,Config as C13
from reproduction.improvement_v6_20261015_01.recovery.recovery_controller import RecoveryController as V6,Config as C6
VERSIONS=['v6','v13','v14','carry','edge','budget','v15']
def controller_class(version):
    if version=='v6':return V6,C6
    if version=='v13':return V13,C13
    if version=='v14':return V14,C14
    assert version in VERSIONS
    return RecoveryController,Config
