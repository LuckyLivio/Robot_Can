"""Create a separate, append-only engineering study and protect previous artifacts."""
import os,json,hashlib,datetime
from pathlib import Path
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1];OLD=ROOT/'reproduction/recovery_v2_20261012_01'
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
    for n in ['setup_study.py','recovery_controller.py','evaluate_recovery.py','run_pilot.py','run_stage.py','analyze_stage.py','verify_stage.py','diagnose_stage.py']:
        with (RUN/n).open('xb') as f:f.write((OLD/n).read_bytes())
    p=RUN/'evaluate_recovery.py';s=p.read_text();s=s.replace('def verify_control(env):', 'from reproduction.recovery_v2_20261012_01.recovery_controller import RecoveryController as V2Controller,Config as V2Config\n\n\ndef verify_control(env):')
    s=s.replace("else (RecoveryController,Config)","else ((V2Controller,V2Config) if job.get('version')=='v2' else (RecoveryController,Config))");p.write_text(s,encoding='utf8')
    plan={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'v3 shared observation-only recovery; alignment and corner clearance; no training or paper',
      'protected_files':len(files),'constraints':['Keep v1/v2 and all earlier weights/results byte-identical','23D state and fixed task geometry only in controller','No reward/contact/success/joint limits inside controller','D=2 FIFO never cleared; 400 steps; maximum two attempts; same controller for BC and Full'],
      'known_data':'Original train/dev, earlier confirmation and v2 confirmation are already observed; none reused as independent confirmation.',
      'pilot_gate':['Eight train natural episodes preserve v2 successes','Two forced-loss and one held-stall successes','Preserve four v2 geometry successes','Rescue at least one corner fixture and demonstrate lower alignment residual without simulator truth control inputs'],
      'dev_gate':{'baseline_v2':229,'episodes':240,'min_success':232,'max_regressions':2,'min_bc_clean':28,'min_bc_noise':28,'min_full_clean':84,'min_full_noise':89},
      'confirmation_if_pass':{'native_seeds':list(range(626101201,626101261)),'demo_ids':list(range(6000000,6000060)),'versions':['disabled','v1','v2','v3'],'methods':['bc_k2','full_s17','full_s23','full_s41'],'noises':[0.,.05],'episodes':1920,'bootstrap_unit':'60 unique starts, average Full seeds inside each start','bootstrap_seed':20261014,'freeze_before_generation':True},
      'stress_confirmation_if_pass':{'native_seeds':list(range(626101401,626101417)),'pose_seed':726101401,'demo_ids':list(range(7000000,7000016)),'versions':['v2','v3'],'groups':['source_far_alignment','destination_corner','sideways_source','sideways_destination'],'per_group':4,'force_at':80,'proposal':'stationary_open','separate_from_primary':True},
      'reporting':'Record every pilot and dev revision; if gate fails do not run independent confirmation; no outcome filtering; no guarantee of world-model superiority.'}
    write(RUN/'study_plan.json',plan);print(json.dumps({'protected_files':len(files),'dev_gate':plan['dev_gate']}))
if __name__=='__main__':main()
