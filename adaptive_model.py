"""Action-conditioned full robot/object dynamics and residual-based adaptation.

Diagnostic state input. Physical execution bias is NEVER supplied to the adapter.
"""
import numpy as np
import torch
from torch import nn
from common import OBS_KEYS

FULL_KEYS=OBS_KEYS+['robot0_joint_pos','robot0_joint_vel']


def full_obs(obs):
    return np.concatenate([np.asarray(obs[k if k in obs else 'object-state']).reshape(-1)
                           for k in FULL_KEYS]).astype(np.float32)


class ResponseWorldModel(nn.Module):
    def __init__(self,dim=37,width=256,affine=False):
        super().__init__()
        self.affine=affine;self.dim=dim
        self.net=nn.Sequential(nn.Linear(dim if affine else dim+7,width),nn.SiLU(),nn.Linear(width,width),nn.SiLU(),
                               nn.Linear(width,width),nn.SiLU(),nn.Linear(width,dim*8 if affine else dim))
        nn.init.zeros_(self.net[-1].weight);nn.init.zeros_(self.net[-1].bias)
        self.register_buffer('mean',torch.zeros(dim))
        self.register_buffer('scale',torch.ones(dim))

    def forward(self,x,a):
        z=(x-self.mean)/self.scale
        if self.affine:
            parts=self.net(z).reshape(-1,self.dim,8)
            delta=parts[:,:,0]+torch.einsum('bdk,bk->bd',parts[:,:,1:],a)
        else:delta=self.net(torch.cat([z,a],-1))
        return x+delta*self.scale*.1

    def rollout(self,x,actions):
        result=[]
        for a in actions.unbind(1):
            x=self(x,a);result.append(x)
        return torch.stack(result,1)


class ResidualAdapter:
    """Estimate latent execution bias through the learned dynamics Jacobian."""
    def __init__(self,model,rate=.2,ridge=1e-5,limit=.4):
        self.model=model
        self.rate=rate;self.ridge=ridge;self.limit=limit
        self.reset()

    def reset(self):
        self.bias=np.zeros(3,np.float32)
        self.previous=None
        self.diagnostics=[]

    def observe(self,current):
        if self.previous is None:return
        xp,command=self.previous
        x=torch.from_numpy(xp[None])
        a=torch.from_numpy(command.copy())
        b=torch.tensor(self.bias,requires_grad=True)
        def predict(v):
            aa=torch.cat([a[:3]+v,a[3:]])[None]
            return self.model(x,aa)[0,:3]
        predicted=predict(b)
        jac=torch.autograd.functional.jacobian(predict,b).detach().numpy()
        residual=current[:3]-predicted.detach().numpy()
        delta=np.linalg.solve(jac.T@jac+self.ridge*np.eye(3),jac.T@residual)
        self.bias=np.clip(self.bias+self.rate*np.clip(delta,-.2,.2),-self.limit,self.limit).astype(np.float32)
        self.diagnostics.append({'innovation_mm':float(np.linalg.norm(residual)*1000),
                                 'estimated_bias':self.bias.tolist(),'jacobian_condition':float(np.linalg.cond(jac))})

    def command(self,state,nominal):
        corrected=nominal.copy()
        corrected[:3]-=self.bias
        corrected=np.clip(corrected,-1,1)
        self.previous=(state.copy(),corrected.copy())
        return corrected
