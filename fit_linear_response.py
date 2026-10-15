"""Fit a transparent action-conditioned local dynamics model for the adaptation baseline."""
import argparse,json
import numpy as np
from common import ROOT

def main(args):
    with np.load(ROOT/'data'/f'response_train_{args.dataset}.npz') as f:
        x,a,y=[f[k] for k in ['x','a','y']]
    # Ridge multivariate linear response for EEF and object positions.
    n=x.shape[0];k=a.shape[1]
    xx=np.repeat(x,k,axis=0);aa=a.reshape(n*k,-1);yy=y.reshape(n*k,-1)
    X=np.concatenate([xx,aa,np.ones((len(xx),1),np.float32)],1)
    Y=yy[:,[0,1,2,16,17,18]]
    ridge=args.ridge*np.eye(X.shape[1]);ridge[-1,-1]=0
    coef=np.linalg.solve(X.T@X+ridge,X.T@Y)
    out=ROOT/'models'/args.run;out.mkdir(parents=True,exist_ok=True)
    np.savez(out/'linear_model.npz',coef=coef)
    cfg={'input':'PRIVILEGED_STATE_DIAGNOSTIC','dataset':args.dataset,'ridge':args.ridge,
         'dim':x.shape[1],'output_indices':[0,1,2,16,17,18]}
    (out/'config.json').write_text(json.dumps(cfg,indent=2))
    pred=X@coef;print(json.dumps({'eef_rmse_mm':float(np.sqrt(np.mean((pred[:,:3]-Y[:,:3])**2))*1000),
                                  'object_rmse_mm':float(np.sqrt(np.mean((pred[:,3:]-Y[:,3:])**2))*1000)}))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--dataset',default='v2');p.add_argument('--run',default='linear_response_v2');p.add_argument('--ridge',type=float,default=1e-3);main(p.parse_args())
