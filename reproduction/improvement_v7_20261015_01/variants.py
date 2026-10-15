from recovery.recovery_controller import RecoveryController,Config
from reproduction.improvement_v6_20261015_01.recovery.recovery_controller import RecoveryController as V6,Config as V6Config

def controller_class(version):
    assert version in ['v6','pose','unknown','v7']
    return (V6,V6Config) if version=='v6' else (RecoveryController,Config)
