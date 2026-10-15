from recovery.recovery_controller import RecoveryController, Config
from reproduction.improvement_v11_20261015_01.recovery.recovery_controller import RecoveryController as V11, Config as C11
VERSIONS = ['v11', 'history', 'v12']
def controller_class(version):
    if version == 'v11':
        return V11, C11
    assert version in VERSIONS
    return RecoveryController, Config
