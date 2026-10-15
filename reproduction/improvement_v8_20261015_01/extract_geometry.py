"""Export fixed task collision geometry once; never called by the controller."""
from pathlib import Path
import hashlib,json,sys
import h5py,numpy as np
from scipy.spatial import ConvexHull
ROOT=Path(__file__).resolve().parents[2];RUN=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from common import DATA,make_env,restore_demo
def main():
    env=make_env(False)
    try:
        with h5py.File(DATA) as f:restore_demo(env,f['data']['demo_97'])
        m=env.sim.model;d=env.sim.data;b=m.body_name2id('Can_main');R=d.body_xmat[b].reshape(3,3);p=d.body_xpos[b]
        geoms=[i for i in range(m.body_geomadr[b],m.body_geomadr[b]+m.body_geomnum[b]) if m.geom_contype[i]]
        assert len(geoms)==1;i=geoms[0];mesh=int(m.geom_dataid[i]);adr=int(m.mesh_vertadr[mesh]);n=int(m.mesh_vertnum[mesh])
        v=m.mesh_vert[adr:adr+n];world=v@d.geom_xmat[i].reshape(3,3).T+d.geom_xpos[i];local=(world-p)@R
        hull=ConvexHull(local);vertices=local[hull.vertices]
        boxes=[]
        for i in range(m.ngeom):
            if m.geom_type[i]==6 and m.geom_contype[i] and m.body_id2name(m.geom_bodyid[i]) in ['bin1','bin2']:
                np.testing.assert_allclose(d.geom_xmat[i].reshape(3,3),np.eye(3),atol=1e-9)
                boxes.append({'body':m.body_id2name(m.geom_bodyid[i]),'center':d.geom_xpos[i].tolist(),'half':m.geom_size[i].tolist()})
        result={'source':'Collision geometry after restore_demo; fixed asset, no episode contacts/rewards used.',
                'can_vertices':vertices.tolist(),'can_local_min':local.min(0).tolist(),'can_local_max':local.max(0).tolist(),'boxes':boxes,
                'source_data_sha256':hashlib.sha256(DATA.read_bytes()).hexdigest()}
        with (RUN/'recovery/scene_geometry.json').open('x') as f:json.dump(result,f,indent=2)
        print(json.dumps({k:v for k,v in result.items() if k not in ['can_vertices','boxes']}));print('hull vertices',len(vertices),'boxes',len(boxes))
    finally:env.close()
if __name__=='__main__':main()
