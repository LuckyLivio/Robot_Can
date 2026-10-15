"""Preselected smoke_b diagnostic replay; no added statistical experiments.

Replays stored executed commands in physics, checks every observed state, joint
position, staged reward and success flag, and renders all 20Hz control frames.
"""
from pathlib import Path
import argparse
import gc
import json
import sys
import h5py
import numpy as np
from PIL import Image, ImageDraw

RUN = Path(__file__).resolve().parent
ROOT = RUN.parents[1]
sys.path.insert(0, str(ROOT))
from reproduction.release_20261012_01 import make_demo as renderer
from common import DATA, make_env, restore_demo, pack_obs

VERSIONS = ['v13', 'v14']
CASES = {
    'leaning': {
        'suffix': 'known13_bc_k2_noise005_demo_13000021',
        'demo': 'demo_13000021',
        'caption': 'BC k=2 / 斜靠接近 / demo13000021 / 噪声0.05',
    },
    'edge': {
        'suffix': 'known13_full_s41_noise005_demo_13000022',
        'demo': 'demo_13000022',
        'caption': 'Full s41 / 箱沿路径 / demo13000022 / 噪声0.05',
    },
}
DISCLOSURE = '已知诊断案例，不代表总体成功率'


def panel(frames, rows, step, caption):
    image = Image.new('RGB', (960, 660), '#101318')
    draw = ImageDraw.Draw(image)
    draw.text((20, 12), caption, font=renderer.FONTS[23], fill='white')
    draw.text((20, 46), '同起点、同噪声、400步 · ' + DISCLOSURE,
              font=renderer.FONTS[17], fill='#bdc6d7')
    for index, version in enumerate(VERSIONS):
        current = min(step, len(rows[version]))
        row = rows[version][max(0, current-1)]
        ended = current == len(rows[version])
        success = ended and row['success_after']
        left = 480*index
        draw.rectangle((left, 80, left+479, 110), fill='#aeb8c8' if version == 'v13' else '#a7daca')
        label = 'v13 · 保留基准' if version == 'v13' else 'v14 · 跟踪与间隙候选'
        draw.text((left+15, 82), label, font=renderer.FONTS[20], fill='#0b1220')
        image.paste(Image.fromarray(frames[version][current]), (left, 110))
        status = '成功 · 保持终点' if success else ('400 步未完成' if ended else '运行中')
        color = '#14543b' if success else ('#7f2638' if ended else '#323a48')
        draw.rectangle((left+10, 120, left+220, 153), fill=color)
        draw.text((left+20, 124), status, font=renderer.FONTS[17], fill='white')
        draw.text((left+15, 598), f"{current:03d}/400 · {row['recovery']['mode']}",
                  font=renderer.FONTS[17], fill='white')
    draw.text((20, 632), f'20 fps / 20 Hz · t={step/20:.2f}s · D2 FIFO · 终点停留1秒，无动作插值',
              font=renderer.FONTS[17], fill='#bdc6d7')
    return np.asarray(image)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--case', choices=list(CASES), required=True)
    args = parser.parse_args()
    case = CASES[args.case]
    out = RUN/'demo'/args.case
    receipt_path = RUN/'analysis'/f'demo_replay_{args.case}.json'
    assert not out.exists() and not receipt_path.exists(), 'Existing demonstration outputs will not be overwritten.'
    # Validate selection and both failed endpoints before creating the output.
    inputs = {}
    for version in VERSIONS:
        folder = RUN/'smoke_b'/f"{version}_{case['suffix']}"
        result = json.loads((folder/'result.json').read_text(encoding='utf8'))
        rows = [json.loads(line) for line in (folder/'trace.jsonl').open(encoding='utf8')]
        assert result['status'] == 'complete' and len(rows) == 400
        assert result['job']['steps'] == 400 and result['job']['noise'] == .05
        assert len(result['records']) == 1 and not result['records'][0]['success']
        assert {row['demo'] for row in rows} == {case['demo']}
        assert [row['step'] for row in rows] == list(range(1, 401))
        assert not any(row['success_after'] for row in rows)
        inputs[version] = {'folder': folder, 'job': result['job'], 'rows': rows}
    assert inputs['v13']['job']['dataset'] == inputs['v14']['job']['dataset']
    out.mkdir(parents=True, exist_ok=False)
    with (out/'caption.json').open('x', encoding='utf8') as handle:
        json.dump({'caption': case['caption'], 'disclosure': DISCLOSURE,
                   'source_stage': 'smoke_b', 'demo': case['demo'],
                   'versions': VERSIONS, 'both_failed_at_400_steps': True},
                  handle, indent=2, ensure_ascii=False)
    renderer.FPS = 20
    renderer.WIDTH = 960
    renderer.HEIGHT = 660
    env = make_env(False)
    frames = {}
    checks = []
    initial = None
    try:
        for version in VERSIONS:
            source = inputs[version]
            job, rows, folder = source['job'], source['rows'], source['folder']
            dataset = ROOT/job['dataset'] if job.get('dataset') else DATA
            with h5py.File(dataset) as handle:
                observation = restore_demo(env, handle['data'][case['demo']])
            physical_start = renderer.signature(env)
            if initial is None:
                initial = physical_start.copy()
            else:
                np.testing.assert_array_equal(initial, physical_start)
            joints = [env.sim.model.joint_name2id('robot0_joint'+str(i)) for i in range(1, 8)]
            joint_addresses = env.sim.model.jnt_qposadr[joints]
            first, context = renderer.camera(env)
            version_frames = {0: first}
            for row in rows:
                np.testing.assert_array_equal(pack_obs(observation), row['state_before'])
                np.testing.assert_array_equal(env.sim.data.qpos[joint_addresses], row['joint_positions'])
                observation, *_ = env.step(np.array(row['executed_action'], np.float32))
                np.testing.assert_array_equal(pack_obs(observation), row['state_after'])
                np.testing.assert_array_equal(np.asarray(env.staged_rewards()), row['stages_after'])
                assert bool(env._check_success()) == row['success_after']
                version_frames[row['step']], context = renderer.camera(env, context)
            frames[version] = version_frames
            context.gl_ctx.make_current()
            env.sim._render_context_offscreen = None
            context.sim = None
            del context
            gc.collect()
            checks.append({'version': version, 'steps': len(rows), 'success': False,
                           'physical_states_exact': True, 'joint_positions_exact': True,
                           'staged_rewards_exact': True, 'success_flags_exact': True,
                           'trace_sha256': renderer.digest(folder/'trace.jsonl'),
                           'result_sha256': renderer.digest(folder/'result.json'),
                           'dataset_sha256': renderer.digest(dataset)})
            print(f"Verified {args.case} {version}: 400 physical replay steps, unfinished.", flush=True)
        rows_by_version = {version: inputs[version]['rows'] for version in VERSIONS}
        def iterator():
            for step in range(401):
                yield panel(frames, rows_by_version, step, case['caption'])
            for _ in range(20):
                yield panel(frames, rows_by_version, 400, case['caption'])
        video = out/'comparison.mp4'
        frame_count = renderer.encode(video, iterator())
        assert frame_count == 421
        Image.fromarray(panel(frames, rows_by_version, 0, case['caption'])).save(out/'poster.png')
        Image.fromarray(panel(frames, rows_by_version, 400, case['caption'])).save(out/'final.png')
        receipt = {'passed': True, 'case': args.case, 'source_stage': 'smoke_b',
                   'demo': case['demo'], 'checks': checks, 'same_initial_physics_and_controller_state': True,
                   'same_initial_state': True, 'both_failed_at_400_steps': True,
                   'fps': 20, 'frames': frame_count, 'resolution': [960, 660], 'duration_s': frame_count/20,
                   'video_sha256': renderer.digest(video),
                   'poster_sha256': renderer.digest(out/'poster.png'), 'final_sha256': renderer.digest(out/'final.png'),
                   'render_script_sha256': renderer.digest(Path(__file__)),
                   'selection': 'Two preselected known smoke_b diagnostic failures; exact saved-command physical replay only, excluded from all statistical episode counts.',
                   'disclosure': DISCLOSURE, 'motion_interpolation': False, 'endpoint_hold_frames': 20,
                   'additional_statistical_episodes': 0}
        with receipt_path.open('x', encoding='utf8') as handle:
            json.dump(receipt, handle, indent=2, ensure_ascii=False)
        print(json.dumps(receipt, ensure_ascii=False))
    finally:
        env.close()


if __name__ == '__main__':
    main()
