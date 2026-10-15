from recovery.recovery_controller import RecoveryController,Config
from reproduction.recovery_v5_20261012_01.recovery_controller import RecoveryController as V5,Config as V5Config

def controller_class(version):
    return (V5,V5Config) if version=='v5' else (RecoveryController,Config)
