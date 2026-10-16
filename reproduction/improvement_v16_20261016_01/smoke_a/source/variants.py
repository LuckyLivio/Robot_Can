from recovery.recovery_controller import RecoveryController,Config
from reproduction.improvement_v15_20261016_01.recovery.recovery_controller import RecoveryController as V15,Config as C15
from reproduction.improvement_v14_20261016_01.recovery.recovery_controller import RecoveryController as V14,Config as C14
from reproduction.improvement_v13_20261016_01.recovery.recovery_controller import RecoveryController as V13,Config as C13
from reproduction.improvement_v6_20261015_01.recovery.recovery_controller import RecoveryController as V6,Config as C6
VERSIONS=['v6','v13','v14','v15','budget','ik','held','edge','v16']
def controller_class(version):
    if version=='v6':return V6,C6
    if version=='v13':return V13,C13
    if version=='v14':return V14,C14
    if version in ['v15','budget']:return V15,C15
    assert version in VERSIONS
    return RecoveryController,Config
