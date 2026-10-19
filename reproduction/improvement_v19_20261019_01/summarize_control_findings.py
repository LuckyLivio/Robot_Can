"""Compact v19 smoke control evidence, using saved observations only.

No controller replay, IK, simulator stepping, tuning, or new evaluation samples.
The detailed diagnosis and all old results remain immutable.
"""
from pathlib import Path
from collections import Counter
import hashlib
import json

RUN = Path(__file__).resolve().parent
ROOT = RUN.parents[1]
ORDER = ['v17', 'v18', 'budget', 'transition', 'candidate', 'settling', 'ab', 'v19']


def read(path):
    return json.loads(path.read_text(encoding='utf8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rel(path):
    return path.relative_to(ROOT).as_posix()


def main():
    diagnosis_path = RUN / 'analysis/smoke_a_control_diagnosis.json'
    output_path = RUN / 'analysis/smoke_a_control_findings.json'
    assert not output_path.exists(), 'Do not overwrite existing diagnostic evidence.'
    diagnosis = read(diagnosis_path)
    assert diagnosis['passed'] and diagnosis['selected_evaluation_executions'] == 72
    assert diagnosis['registered_profiles'] == 9 and diagnosis['unique_start_identities'] == 8
    sources = [Path(__file__), diagnosis_path]
    cases = diagnosis['cases']

    def case(version, demo, profile='standard'):
        found = [c for c in cases if c['version'] == version
                 and c['demo'] == 'demo_' + str(demo) and c['comparison_profile'] == profile]
        assert len(found) == 1
        return found[0]

    def compact(c):
        fields = ['job', 'version', 'demo', 'comparison_profile', 'success', 'steps',
                  'first_descend_entry_clock', 'first_close_clock', 'first_descend_to_close_controls',
                  'first_carry_clock', 'first_place_clock', 'first_release_clock',
                  'final_command_mode', 'final_next_mode', 'recenter_controls',
                  'transition_window_active_controls', 'transition_window_inactive_controls',
                  'settling_triggered_events', 'settling_applied_events']
        result = {key: c[key] for key in fields}
        result['descend_command_modes'] = [d['command_modes'] for d in c['descents']]
        result['held_segments'] = [{k: segment[k] for k in [
            'phase', 'first_control', 'last_control', 'controls', 'maximum_consecutive_ready',
            'ready_control_spans', 'last_position_error_m', 'last_angle_error_rad',
            'last_consecutive_ready', 'integral_pause_controls']}
            for segment in c['held_pose_segments']]
        return result

    def control(c, step):
        found = [r for r in c['held_pose_controls'] if r['control_step'] == step]
        assert len(found) == 1
        return found[0]

    def release_tail(c):
        path = RUN / 'smoke_a' / c['job'] / 'trace.jsonl'
        assert sha(path) == diagnosis['source_sha256'][rel(path)]
        sources.append(path)
        rows = [json.loads(line) for line in path.read_text(encoding='utf8').splitlines()]
        event_clock = c['first_release_clock']
        tail = [] if event_clock is None else [r for r in rows if r['step'] > event_clock]
        submitted = [r['step'] for r in tail if r['recovery']['mode'] == 'RELEASE'
                     and r['submitted_action'][6] < 0]
        executed = [r['step'] for r in tail if r['executed_action_before_noise'][6] < 0]
        return {'stored_release_event_clock': event_clock,
                'first_release_open_submitted_control': submitted[0] if submitted else None,
                'first_release_open_executed_control': executed[0] if executed else None,
                'release_open_submitted_controls': len(submitted),
                'release_open_executed_controls': len(executed),
                'final_success_after': rows[-1]['success_after'],
                'scope': 'Only controls after the recorded RELEASE event; actual submitted and executed grip signs. No future rollout.'}

    success = {version: sum(c['success'] for c in cases if c['version'] == version)
               for version in ORDER}
    assert success == dict(zip(ORDER, [3, 2, 7, 2, 2, 2, 2, 2]))
    totals = {version: {
        'triggered': sum(c['settling_triggered_events'] for c in cases if c['version'] == version),
        'actually_submitted': sum(c['settling_applied_events'] for c in cases if c['version'] == version)
    } for version in ['settling', 'v19']}
    assert totals == {'settling': {'triggered': 84, 'actually_submitted': 84},
                      'v19': {'triggered': 85, 'actually_submitted': 85}}

    rows_36 = []
    for version in ORDER:
        c = case(version, 12000036)
        row = compact(c)
        row['release_tail'] = release_tail(c)
        rows_36.append(row)
    assert rows_36[0]['release_tail']['release_open_executed_controls'] == 8
    assert rows_36[-1]['release_tail']['release_open_executed_controls'] == 7

    profiles_5 = {}
    for profile in ['standard', 'clearance_only_parent']:
        profiles_5[profile] = [compact(case(v, 6000005, profile)) for v in ORDER]
    c5, ab5, full5 = case('settling', 6000005), case('ab', 6000005), case('v19', 6000005)
    assert c5['held_pose_segments'][-1]['maximum_consecutive_ready'] == 4
    assert control(c5, 393)['position_error_m'] > .009
    assert full5['held_pose_segments'][-1]['maximum_consecutive_ready'] == 3
    assert control(full5, 400)['consecutive_strict_arrival'] == 2
    assert abs(control(full5, 400)['position_error_m'] - .006083806326084948) < 1e-12
    a5 = case('transition', 6000005)
    assert [(e['event'], e['step']) for e in a5['recenter_events']] == [
        ('recenter_check', 310), ('recenter_ik', 311), ('recenter_settled', 320)]

    selected_controls = {}
    for version, selected in [('v18', [388, 391, 393, 395, 400]),
                              ('settling', [388, 391, 392, 393, 395, 400]),
                              ('ab', [388, 391, 392, 395, 400]),
                              ('v19', [388, 391, 392, 395, 399, 400])]:
        selected_controls[version] = [control(case(version, 6000005), s) for s in selected]

    upstream = [compact(case(version, 13000022)) for version in ORDER]
    assert all(r['first_descend_entry_clock'] == 387 for r in upstream if r['version'] != 'budget')
    assert all(r['first_carry_clock'] is None for r in upstream)
    route_failure = [compact(case(version, 13000021)) for version in ORDER]
    assert case('v19', 13000021)['first_carry_clock'] == 332
    assert case('v19', 13000021)['steps'] == 400
    assert case('v19', 13000021)['settling_triggered_events'] == 0

    evidence = {
        'passed': True, 'stage': 'smoke_a', 'selected_evaluation_executions': 72,
        'registered_profiles_per_variant': 9, 'unique_start_identities_per_variant': 8,
        'new_physical_episodes': 0, 'new_evaluation_samples': 0,
        'saved_controller_replay_performed': False,
        'scope': 'Compact read-only extraction of the immutable detailed control diagnosis and original release-tail traces.',
        'successes_per_9_profiles': success, 'settling_actual_submission_totals': totals,
        'case_12000036': rows_36,
        'case_6000005': {'paired_profiles': profiles_5,
                         'transition_recenter_events': a5['recenter_events'],
                         'transition_recenter_control_spans': a5['recenter_control_spans'],
                         'selected_original_held_controls': selected_controls},
        'case_13000022': upstream, 'case_13000021': route_failure,
        'findings_zh': [
            '12000036：A把下降19步减为13步，但实际v17为12步。C没有缩短5/17/55步的三段搬运。AB与完整v19在363进入PLACE、391进入RELEASE，均比v17晚1步；第400步前实际释放指令执行7次而v17为8次。实际v17成功、完整v19失败，不能据此推断第401步必然成功。',
            'C单项在12000036第400存储时钟才转为RELEASE，当前实际提交仍为PLACE，释放指令提交和执行均为0次；phase事件不能替代实际动作。',
            '6000005：A的固定3步窗口结束后再次触发回正。310为检查事件时钟，311实际IK控制，312–320为9条PATH_RECENTER；25步下降变29步，CARRY358变362，两个profile结论相同但不算两个独立起点。',
            '6000005：C单项把连续3帧提升到4帧，393位置误差10.748mm重新超9mm；完整v19相对AB仍最多3帧，末帧6.084mm只是当前连续第2帧。局部越过减轻和更小末帧误差都没有满足原连续5帧。',
            '6000005的制动变化需经过D2才执行；已提交的在途动作保留，机械臂实测运动未即时停止。这里的预测仅是控制启发式，不能当成未来状态或几何证明。C单项84次、完整v19共85次触发均实际提交，但没有新增成功profile。',
            '13000022：除旧预算参考外，各组首次DESCEND均在387；没有CLOSE、CARRY或持物C触发。后端候选与持物稳定模块没有作用机会，上游接近耗时仍是限制。',
            '13000021：A让CARRY337提前至332；完整v19仍无可选完整路线，末段EXHAUSTED，C没有触发。更早开始搜索不能等同路线可行。'
        ],
        'next_round_only_not_implemented': [
            'A：先按当前抓取轴进展与横向误差分别界定衔接范围，验证是否可避免固定age退出后的回正复发；保持原动作变化限制、几何与姿态保护。',
            'C：依据实际观测速度和已知D2在途提交命令，研究提前停车与目标附近保持；用单项消融验证连续到位，保留9mm/0.08rad、连续5帧和400步预算。',
            '不得清空队列、提前PLACE、减少确认帧、增加步数或放宽关节/相对姿态/抓持/几何保护；这些建议尚未实现或验证。'
        ],
        'limitations': [
            'Registered contrasts are A/B/C/AB/full; AC and BC are absent. This is not a complete three-factor interaction design.',
            'Budget was rerun but lacks some current protections; its 7/9 cannot justify adopting it wholesale.',
            'Stored phase-event clocks differ from submitted/executed control numbers; D2 remains intact.',
            'Arrival spans are retrospective original observed predicates, not new transitions. A smaller final error does not establish a future five-frame run.',
            'Static and retrospective diagnostics add no statistical samples.'
        ],
        'source_sha256': {rel(p): sha(p) for p in sources}
    }
    with output_path.open('x', encoding='utf8') as f:
        json.dump(evidence, f, ensure_ascii=False, indent=2, allow_nan=False)
    print(json.dumps({'passed': True, 'output': rel(output_path),
                      'source_files': len(evidence['source_sha256']),
                      'new_physical_episodes': 0}, ensure_ascii=False))


if __name__ == '__main__':
    main()
