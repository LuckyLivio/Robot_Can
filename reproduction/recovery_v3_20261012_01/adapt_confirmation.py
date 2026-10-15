"""Prepare an isolated generator from the previously verified state protocol."""
from pathlib import Path
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1]
def main():
    s=(ROOT/'reproduction/recovery_v2_20261012_01/prepare_confirmation.py').read_text()
    s=s.replace('426101401,426101413','626101401,626101417').replace('526101401','726101401').replace('5000000','7000000').replace('range(12)','range(16)')
    s=s.replace("'groups':['sideways_source']*4+['upright_destination_wall']*4+['sideways_destination']*4", "'groups':['source_far_alignment']*4+['destination_corner']*4+['sideways_source']*4+['sideways_destination']*4")
    s=s.replace('All 12 predetermined starts','All 16 predetermined starts')
    s=s.replace("old=np.stack(previous);env=make_env(False)", "with h5py.File(ROOT/'reproduction/recovery_v2_20261012_01/confirmation_starts.hdf5') as f:\n        previous.extend(d['states'][0] for d in f['data'].values())\n    old=np.stack(previous);env=make_env(False)")
    start=s.index("                elif kind=='upright_destination_wall':")
    end=s.index("                else:position=",start)
    s=s[:start]+"                elif kind=='source_far_alignment':position=[rng.uniform(.20,.25),rng.uniform(-.43,-.35),.88];pitch=0.;yaw=rng.uniform(-180,180)\n                elif kind=='destination_corner':position=[rng.uniform(.147,.158),rng.uniform(.076,.087),.88];pitch=0.;yaw=rng.uniform(-180,180)\n"+s[end:]
    s=s.replace("for version in ['disabled','v1','v2']:","for version in ['disabled','v1','v2','v3']:").replace("if version=='v2' else {}","if version=='v3' else {}")
    s=s.replace("for v in ['v1','v2']","for v in ['v2','v3']").replace('1440','1920').replace("'additional_geometry_episodes':24","'additional_geometry_episodes':32")
    with (RUN/'prepare_confirmation.py').open('x',encoding='utf8') as f:f.write(s)
if __name__=='__main__':main()
