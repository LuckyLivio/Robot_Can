from recovery.recovery_controller import RecoveryController,Config
from reproduction.improvement_v6_20261015_01.recovery.recovery_controller import RecoveryController as V6,Config as C6
from reproduction.improvement_v8_20261015_01.recovery.recovery_controller import RecoveryController as V8,Config as C8
VERSIONS=['v6','v8','joint','bounded','v9']
def controller_class(version):
    if version=='v6':return V6,C6
    if version=='v8':return V8,C8
    assert version in VERSIONS
    return RecoveryController,Config
