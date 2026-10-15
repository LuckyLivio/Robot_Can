from recovery.recovery_controller import RecoveryController, Config
from reproduction.improvement_v11_20261015_01.recovery.recovery_controller import RecoveryController as V11, Config as C11
from reproduction.improvement_v6_20261015_01.recovery.recovery_controller import RecoveryController as V6, Config as C6
VERSIONS = ['v6', 'v11', 'history', 'v12']
def controller_class(version):
    if version == 'v6':
        return V6, C6
    if version == 'v11':
        return V11, C11
    assert version in VERSIONS
    return RecoveryController, Config
