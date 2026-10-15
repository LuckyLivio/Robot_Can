"""Same-state symmetric action interventions identify local dynamics response."""
import argparse,json,time
import h5py
import numpy as np
from common import ROOT,DATA,make_env,restore_demo
from adaptive_model import full_obs


def main(args):
    env=make_env(False)
    names=json.loads((ROOT/'data/splits.json').read_text())[args.split][:args.demos]
    rng=np.random.default_rng(args.seed)
    xx=[];aa=[];yy=[];parents=[];points=[]
    out=ROOT/'data'/f'response_{args.split}_{args.name}.npz'
    start=time.perf_counter()
    with h5py.File(DATA,'r') as file:
        for name in names:
            d=file['data'][name];restore_demo(env,d,0,xml=True)
            for t in np.linspace(4,len(d['actions'])-2,args.points,dtype=int):
                base=d['actions'][t].copy()
                # Seven actions: nominal and +/- perturbations in each translation axis.
                actions=[base.copy()]
                for axis in range(3):
                    distance=rng.uniform(.12,.3)
                    for sign in [-1,1]:
                        action=base.copy();action[axis]+=sign*distance
                        actions.append(np.clip(action,-1,1))
                x=full_obs(restore_demo(env,d,int(t),xml=False))
                future=[]
                for action in actions:
                    restore_demo(env,d,int(t),xml=False)
                    obs,*_=env.step(action);future.append(full_obs(obs))
                xx.append(x);aa.append(actions);yy.append(future);parents.append(name);points.append(int(t))
            np.savez_compressed(out,x=np.asarray(xx,np.float32),a=np.asarray(aa,np.float32),
                                y=np.asarray(yy,np.float32),parent=np.asarray(parents),point=np.asarray(points))
            print(json.dumps({'demo':name,'groups':len(xx),'elapsed_s':time.perf_counter()-start}),flush=True)
    env.close()
    out.with_suffix('.json').write_text(json.dumps({'args':vars(args),'groups':len(xx),
        'input':'PRIVILEGED_STATE_DIAGNOSTIC','elapsed_s':time.perf_counter()-start},indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--split',choices=['train','dev'],default='train')
    p.add_argument('--demos',type=int,default=60);p.add_argument('--points',type=int,default=12)
    p.add_argument('--seed',type=int,default=918);p.add_argument('--name',default='v2')
    main(p.parse_args())
