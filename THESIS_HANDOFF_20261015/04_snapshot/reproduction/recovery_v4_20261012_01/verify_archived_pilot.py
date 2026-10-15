"""Replay the retained first pilot with its own immutable source snapshot."""
import importlib.util,json,sys
from setup_study import ROOT,RUN,write,digest
import verify_stage
def main():
    folder=RUN/'pilot_a';path=folder/'source/recovery_controller.py'
    saved=json.loads((folder/'complete.json').read_text())['code_sha256']
    for n,h in saved.items():assert digest(folder/'source'/n)==h
    spec=importlib.util.spec_from_file_location('v4_archived_pilot_a',path)
    module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
    verify_stage.RecoveryController=module.RecoveryController;verify_stage.Config=module.Config
    jobs=json.loads((folder/'jobs.json').read_text());audits=[]
    for j in jobs:audits.append(verify_stage.audit(folder/j['id']))
    result={'passed':True,'revision':'pilot_a','source_sha256':saved,'episodes':sum(a['episodes'] for a in audits),
        'control_steps':sum(a['controls'] for a in audits),'audits':audits}
    write(RUN/'validation_pilot_a.json',result)
    print(json.dumps({k:v for k,v in result.items() if k!='audits'}),flush=True)
if __name__=='__main__':main()
