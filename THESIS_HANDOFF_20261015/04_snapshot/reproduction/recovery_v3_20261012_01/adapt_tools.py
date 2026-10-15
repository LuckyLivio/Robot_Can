"""One-time adaptation of isolated v2 analysis and verification utilities."""
from pathlib import Path
RUN=Path(__file__).resolve().parent
def main():
    for name in ['analyze_stage.py','diagnose_stage.py']:
        p=RUN/name;s=p.read_text();s=s.replace('v2','NEWVERSION').replace('v1','v2').replace('NEWVERSION','v3').replace('20261013','20261014')
        if name=='analyze_stage.py':
            s=s.replace("for version in ['disabled','v2','v3']:","for version in (['disabled','v1','v2','v3'] if stage=='confirmation' else ['disabled','v2','v3']):")
            s=s.replace("for offset,version,color,label in [(-.25,'disabled','#abb5bd','Original'),(0,'v2','#5a8aa5','Recovery v2'),(.25,'v3','#147d69','Recovery v3')]:", "for offset,version,color,label in [(-.25,'disabled','#abb5bd','Original'),(0,'v2','#5a8aa5','Recovery v2'),(.25,'v3','#147d69','Recovery v3')]:")
        p.write_text(s,encoding='utf8')
    p=RUN/'verify_stage.py';s=p.read_text().replace("cls,cfg=(RecoveryController,Config) if job['version']=='v2' else (V1Controller,V1Config)","cls,cfg=(RecoveryController,Config) if job['version']=='v3' else ((V2Controller,V2Config) if job['version']=='v2' else (V1Controller,V1Config))")
    s=s.replace('def audit(directory):', 'from reproduction.recovery_v2_20261012_01.recovery_controller import RecoveryController as V2Controller,Config as V2Config\n\n\ndef audit(directory):')
    s=s.replace("for version in ['v1','v2']:","for version in ['v2','v3']:");p.write_text(s,encoding='utf8')
    p=RUN/'run_stage.py';s=p.read_text().replace("ROOT/'reproduction/recovery_20261012_01/recovery_controller.py',", "ROOT/'reproduction/recovery_20261012_01/recovery_controller.py',ROOT/'reproduction/recovery_v2_20261012_01/recovery_controller.py',")
    p.write_text(s,encoding='utf8')
if __name__=='__main__':main()
