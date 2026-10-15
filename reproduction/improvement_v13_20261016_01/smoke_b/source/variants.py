from recovery.recovery_controller import RecoveryController,Config
from reproduction.improvement_v12_20261015_01.recovery.recovery_controller import RecoveryController as V12,Config as C12
from reproduction.improvement_v6_20261015_01.recovery.recovery_controller import RecoveryController as V6,Config as C6
VERSIONS=['v6','v12','support','escape','v13']
def controller_class(version):
    if version=='v6':return V6,C6
    if version=='v12':return V12,C12
    assert version in VERSIONS
    return RecoveryController,Config
