"""Create an isolated, prospective two-factor recovery study."""
import os, json, hashlib, datetime
from pathlib import Path
RUN=Path(__file__).resolve().parent; ROOT=RUN.parents[1]
def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()
def write(p,v):
    with p.open('x',encoding='utf8') as f:json.dump(v,f,indent=2,ensure_ascii=False)
def main():
    files={}
    for folder,dirs,names in os.walk(ROOT):
        dirs[:]=[d for d in dirs if d not in {'.venv','.git','.idea','__pycache__'} and Path(folder)/d!=RUN]
        for n in names:
            p=Path(folder)/n;files[p.relative_to(ROOT).as_posix()]=digest(p)
    write(RUN/'before_manifest.json',files)
    old=ROOT/'reproduction/recovery_v3_20261012_01'
    for name in ['setup_study.py','evaluate_recovery.py','run_pilot.py','run_stage.py','verify_stage.py']:
        with (RUN/name).open('xb') as f:f.write((old/name).read_bytes())
    base=ROOT/'reproduction/recovery_v2_20261012_01/recovery_controller.py'
    with (RUN/'recovery_controller.py').open('xb') as f:f.write(base.read_bytes())
    plan={'registered_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
      'scope':'v2 plus conditional equivalent-yaw switch (A) and region-guarded corner grasp (B); no training, no paper',
      'protected_files':len(files),'variants':['v2','align_only','region_only','v4'],
      'constraints':['Original weights and all previous artifacts byte-identical','Same D2 FIFO without clearing; 400 steps; max 2 attempts','23D observed state and fixed geometry only; no simulator truth/contact/reward/joints in controller','Keep v2 default nearest orientation; change equivalent yaw only on observed stagnation','Exclude divider/wall/outside/airborne objects from special corner grasp'],
      'known_data':'All previous development and confirmation sets are diagnostic data now, including the three v3 regressions. Never count them as new confirmation.',
      'pilot_gate':['Both-off matches v2 actions/events on replay','Region boundary and stagnation/progress unit checks pass','Preserve 8 natural, 2 loss, 1 held-stall and 4 old geometry successes for each candidate','Preserve all three known v3-regression successes','Demonstrate actual yaw switch only following stagnation and at least one region-only corner rescue'],
      'dev_gate':{'episodes_per_variant':240,'baseline_v2':229,'min_success':232,'max_regressions':2,'min_bc_clean':28,'min_bc_noise':28,'min_full_clean':84,'min_full_noise':89},
      'selection':'Apply gate to A, B and AB independently. Among passing variants choose highest successes, then fewest regressions, then fewest enabled components; tie A before B. AB is not automatically promoted. If none pass, stop and retain v2. Do not adjust gate after results.',
      'confirmation_if_pass':{'native_seeds':list(range(826101201,826101261)),'demo_ids':list(range(8000000,8000060)), 'versions':['v2','align_only','region_only','v4'],'methods':['bc_k2','full_s17','full_s23','full_s41'],'noises':[0.,.05],'episodes':1920,'bootstrap_unit':'60 unique starts with Full training seeds averaged within each start','bootstrap_seed':20261015,'freeze_before_generation':True},
      'stress_confirmation_if_pass':{'native_seeds':list(range(826101401,826101417)),'pose_seed':926101401,'demo_ids':list(range(9000000,9000016)),'versions':['v2','align_only','region_only','v4'],'groups':['source_far_alignment','destination_corner','sideways_source','sideways_destination'],'per_group':4,'force_at':80,'proposal':'stationary_open','separate_from_primary':True},
      'reporting':'Keep failed revisions and all starts. No claim that recovery proves world-model superiority. Promotion is conditional on development; independent confirmation may reject it.'}
    write(RUN/'study_plan.json',plan)
    print(json.dumps({'protected_files':len(files),'directory':str(RUN)}))
if __name__=='__main__':main()
