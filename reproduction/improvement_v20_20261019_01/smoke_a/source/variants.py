"""Actual frozen parents and two repairs to complete actual v19."""
from recovery.recovery_controller import RecoveryController,Config
from reproduction.improvement_v19_20261019_01.recovery.recovery_controller import RecoveryController as V19,Config as C19
from reproduction.improvement_v18_20261019_01.recovery.recovery_controller import RecoveryController as V18,Config as C18
from reproduction.improvement_v17_20261019_01.recovery.recovery_controller import RecoveryController as V17,Config as C17
from reproduction.improvement_v16_20261016_01.recovery.recovery_controller import RecoveryController as V16,Config as C16
from reproduction.improvement_v15_20261016_01.recovery.recovery_controller import RecoveryController as V15,Config as C15
from reproduction.improvement_v14_20261016_01.recovery.recovery_controller import RecoveryController as V14,Config as C14
from reproduction.improvement_v13_20261016_01.recovery.recovery_controller import RecoveryController as V13,Config as C13
from reproduction.improvement_v6_20261015_01.recovery.recovery_controller import RecoveryController as V6,Config as C6
VERSIONS=['v6','v13','v14','v15','v16','v17','v18','v19','budget','directional','braking','v20']
def controller_class(version):
    parents={'v6':(V6,C6),'v13':(V13,C13),'v14':(V14,C14),'v15':(V15,C15),
             'budget':(V15,C15),'v16':(V16,C16),'v17':(V17,C17),'v18':(V18,C18),'v19':(V19,C19)}
    if version in parents:return parents[version]
    assert version in ['directional','braking','v20'],version
    return RecoveryController,Config
