"""Build v19 reports, categorical figures and a static evidence page.

Reads completed executions and their receipts only. It neither runs experiments
nor edits root navigation, controllers, old versions, weights or original data.
Figures keep standard conditions separate from the clearance-only budget profile.
After diagnosis, optional analysis/report_findings.json contains the completed
stage name and findings [{title, finding, next_step, sources:[local paths]}].
Its content must be derived from actual stored observations, never a forecast.
"""
from collections import Counter
from pathlib import Path
import csv
import hashlib
import html
import importlib.util
import json
import os
import re

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np

RUN = Path(__file__).resolve().parent
ROOT = RUN.parents[1]
FIGURES = RUN / 'figures'
ORDER = ['v17', 'v18', 'budget', 'transition', 'candidate', 'settling', 'ab', 'v19']
LABELS = {'v17': '实际 v17', 'v18': '完整 v18', 'budget': 'v15 仅预算',
          'transition': 'A · 过渡窗口', 'candidate': 'B · 候选预算',
          'settling': 'C · 终端收敛', 'ab': 'A+B', 'v19': 'v19 · A+B+C'}
SHORT_LABELS = {'v17': 'v17', 'v18': 'v18', 'budget': '旧预算',
                'transition': 'A', 'candidate': 'B', 'settling': 'C', 'ab': 'AB', 'v19': 'ABC'}
COLORS = {'v17': '#82909C', 'v18': '#526779', 'budget': '#248B77',
          'transition': '#B17B32', 'candidate': '#517EB0', 'settling': '#966684',
          'ab': '#608E96', 'v19': '#7061AE'}
TARGETS = [
    ('斜靠抓取后搬运', 'known13_bc_k2_noise005_demo_13000021', 'demo_13000021'),
    ('箱沿分段接近', 'known13_full_s41_noise005_demo_13000022', 'demo_13000022'),
    ('预算专用 profile', 'clearance_profile_6000005', 'demo_6000005'),
]
STAGE_PATTERN = re.compile(r'(?:smoke|pilot|dev)_[a-z0-9]+|confirmation')
PLANNED = {'pilot': 752, 'dev': 720, 'confirmation': 1440}
EXPECTED_EXECUTIONS = {'smoke': 72, **PLANNED}
FAMILY_LABELS = {'smoke': '小测试', 'pilot': '已知条件消融', 'dev': '开发对照', 'confirmation': '独立确认'}
STATIC_ROUTE_RISK = ('执行前对同一保存输入调用搜索器：12000036旧step276状态由v18搜索器的198 work / 13调用降为126 work / 9调用；'
                     'demo87的局部inset机会保留。但12000011旧第二次step311状态的搬运证书不完整，新规则不准入inset，'
                     '由v18搜索器的39 work / 3调用变成125 work / 9调用。这些不是各版本本轮回合的实际规划时间，也不是普遍省时保证；'
                     '已准入可选候选仍可花满48 work后无结果，实际作用须以本轮完整闭环执行判断。')



def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative(path):
    return path.relative_to(ROOT).as_posix()


def checked_receipt_sources(receipt):
    """v19 formal receipts use an explicit standard root-relative mapping."""
    return receipt.get('source_sha256', {})


def esc(value):
    return html.escape(str(value), quote=True)


def family(stage):
    return stage.split('_', 1)[0]


def stage_key(name):
    return ['smoke', 'pilot', 'dev', 'confirmation'].index(family(name)), name


def load_stage(folder):
    name = folder.name
    completion = read(folder / 'completed.json')
    assert completion['source_unchanged'], name
    analysis_path = RUN / 'analysis' / (name + '.json')
    assert analysis_path.is_file(), 'Complete stage needs saved outcome analysis: ' + name
    analysis = read(analysis_path)
    assert analysis['stage'] == name and 'variants' in analysis
    jobs = read(folder / 'jobs.json')
    expected_versions = {'v17', 'v18', 'v19'} if family(name) == 'dev' else set(ORDER)
    if family(name) != 'confirmation':
        assert {job['version'] for job in jobs} == expected_versions, ('Unexpected versions', name)
    assert sum(len(job['demos']) for job in jobs) == EXPECTED_EXECUTIONS[family(name)], ('Execution count differs from registered stage', name)
    sources = [analysis_path, folder/'jobs.json', folder/'started.json', folder/'completed.json']
    snapshot = read(folder / 'started.json')['source_sha256']
    for key, digest in snapshot.items():
        frozen = folder / 'source' / (ROOT / key).relative_to(RUN)
        assert frozen.is_file() and sha(frozen) == digest, ('Snapshot changed', frozen)
    records = []
    for job in jobs:
        path = folder / job['id'] / 'result.json'
        saved = read(path)
        assert saved['status'] == 'complete' and saved['job'] == job
        assert [item['demo'] for item in saved['records']] == job['demos']
        sources.append(path)
        for item in saved['records']:
            assert 1 <= item['steps'] <= 400 and isinstance(item['success'], bool)
            records.append({
                'stage': name, 'version': job['version'], 'job': job['id'],
                'condition': job['id'].split('_', 1)[1], 'demo': item['demo'],
                'comparison_profile': job.get('comparison_profile', 'standard'),
                'dataset': job.get('dataset', 'data/can_ph_lowdim_v15.hdf5'),
                'success': item['success'], 'steps': item['steps'],
                'result': path.relative_to(RUN).as_posix(),
                'last_transition': item['events'][-1]['to'] if item.get('events') else 'NORMAL',
                'carry_events': len(item.get('carry15_events', [])),
                'edge_events': len(item.get('edge15_events', [])),
                'budget_events': len(item.get('budget15_events', [])),
                'ik16_events': len(item.get('ik16_events', [])),
                'held16_events': len(item.get('held16_events', [])),
                'edge16_events': len(item.get('edge16_events', [])),
                'route17_events': len(item.get('route17_events', [])),
                'edge17_events': len(item.get('edge17_events', [])),
                'held17_events': len(item.get('held17_events', [])),
                'handoff18_events': len(item.get('handoff18_events', [])),
                'route18_events': len(item.get('route18_events', [])),
                'transition19_events': len(item.get('transition19_events', [])),
                'budget19_events': len(item.get('budget19_events', [])),
                'settling19_events': len(item.get('settling19_events', [])),
            })
    assert len(records) == completion['episodes']
    assert len(records) == EXPECTED_EXECUTIONS[family(name)]
    assert len(records) == analysis.get('evaluated_executions', len(records))
    for version, totals in analysis['variants'].items():
        selected = [row for row in records if row['version'] == version]
        assert len(selected) == totals['episodes']
        assert sum(row['success'] for row in selected) == totals['success']
    verification = {}
    for suffix in ['verification', 'physics']:
        path = RUN / 'analysis' / f'{name}_{suffix}.json'
        receipt = read(path) if path.is_file() else None
        verification[suffix] = receipt
        if path.is_file():
            sources.append(path)
        if receipt and receipt.get('passed') and suffix == 'verification':
            assert receipt['episodes'] == len(records)
    return {'name': name, 'analysis': analysis, 'records': records, 'verification': verification,
            'sources': sources, 'audits_passed': all(x and x.get('passed') for x in verification.values())}


def figure_settings():
    available = {font.name for font in font_manager.fontManager.ttflist}
    preferred = next((name for name in ['Microsoft YaHei', 'Noto Sans CJK SC', 'SimHei'] if name in available), None)
    assert preferred, 'A CJK font is required; do not export unreadable labels.'
    plt.rcParams.update({'font.family': preferred, 'font.size': 9, 'axes.labelsize': 9,
                         'axes.titlesize': 11, 'axes.titlepad': 13, 'xtick.labelsize': 8,
                         'ytick.labelsize': 9, 'pdf.fonttype': 42, 'svg.fonttype': 'none',
                         'axes.spines.top': False, 'axes.spines.right': False,
                         'figure.facecolor': 'white', 'savefig.dpi': 600})


def save_layout_receipt(figure, identifier):
    """Audit final physical axes bounds with the installed figure QA tool."""
    figure.canvas.draw()
    qa_root = Path(os.environ.get('FIGURE_QA_SCRIPTS',
        Path.home()/'.codex/research-skill-sources/nature-research/skills/nature-figure/scripts'))
    tool = qa_root/'audit_panel_alignment.py'
    assert tool.is_file(), 'Set FIGURE_QA_SCRIPTS to the installed nature-figure scripts directory.'
    spec = importlib.util.spec_from_file_location('figure_panel_alignment', tool)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    exemptions = ([{'panels': ['a', 'b'], 'checks': ['panel-width'],
                    'reason': 'Intentional 3.7:2.2 widths: count plot plus one-profile text column.'}]
                  if len(figure.axes) == 2 else [])
    path = FIGURES/f'{identifier}.alignment.json'
    receipt = module.require_matplotlib_panel_alignment(
        figure, json_out=path, overlay_svg=FIGURES/f'{identifier}.alignment.svg',
        tolerance_pt=1.5, panel_ids=['a', 'b'] if len(figure.axes)==2 else ['a'],
        exemptions=exemptions)
    assert receipt['summary']['fail'] == 0
    # Keep the full upstream audit plus stable fields used by project artifact QA.
    receipt.update(passed=True, tolerance_pt=1.5)
    path.write_text(json.dumps(receipt, indent=2, ensure_ascii=False), encoding='utf-8')
    return {'receipt': path.name, 'sha256': sha(path), 'tool_sha256': sha(tool),
            'scope': 'Rendered physical panel alignment; visual and PDF collision review remain separate.'}


def save_figure(figure, identifier, stage, caption, rows, sources, previous):
    hashes = {relative(path): sha(path) for path in sorted(set(sources) | {Path(__file__).resolve()})}
    dimensions = (np.asarray(figure.get_size_inches()) * 25.4).tolist()
    item = {'id': identifier, 'stage': stage, 'caption': caption, 'dpi': 600,
            'width_mm': dimensions[0], 'height_mm': dimensions[1], 'rows': len(rows),
            'no_smoothing': True, 'categorical_conditions_not_connected': True,
            'sources': hashes, 'independent_start_inference': False,
            'visual_contract': {'method': 'Categorical raw counts and observed target outcomes; no fitted curve.',
                                'paired_groups': ORDER,
                                'profile_scope': 'Eight standard starts plus a reused clearance configuration profile, counted separately.',
                                'missing_groups_AC_BC': True},
            'plotting_source_sha256': sha(Path(__file__))}
    paths = [FIGURES / f'{identifier}.{extension}' for extension in ['png', 'pdf', 'svg', 'csv']]
    if any(path.exists() for path in paths):
        assert all(path.is_file() for path in paths), ('Incomplete existing figure', identifier)
        old = previous.get(identifier)
        assert old and old['sources'] == hashes and old['rows'] == len(rows), ('Refusing to replace changed figure', identifier)
        assert all(sha(FIGURES / f'{identifier}.{extension}') == digest for extension, digest in old['outputs_sha256'].items())
        plt.close(figure)
        return old
    item['alignment_qa'] = save_layout_receipt(figure, identifier)
    for extension in ['png', 'pdf', 'svg']:
        figure.savefig(FIGURES / f'{identifier}.{extension}', dpi=600, facecolor='white')
    plt.close(figure)
    with (FIGURES / f'{identifier}.csv').open('x', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    item['outputs_sha256'] = {extension: sha(FIGURES / f'{identifier}.{extension}') for extension in ['png', 'pdf', 'svg', 'csv']}
    return item


def plot_stage(stage, previous):
    records = stage['records']
    versions = [version for version in ORDER if any(row['version'] == version for row in records)]
    standard = [row for row in records if row['comparison_profile'] == 'standard']
    profile = [row for row in records if row['comparison_profile'] != 'standard']
    denominators = {version: sum(row['version'] == version for row in standard) for version in versions}
    assert len(set(denominators.values())) == 1
    figure, (axis, profile_axis) = plt.subplots(1, 2, figsize=(7.2, 5.2), layout='constrained',
                                               gridspec_kw={'width_ratios': [3.7, 2.2]}, sharey=True)
    rows = []
    for index, version in enumerate(versions):
        selected = [row for row in standard if row['version'] == version]
        success = sum(row['success'] for row in selected)
        count = len(selected)
        axis.barh(index, success, height=.55, color=COLORS[version], zorder=2)
        axis.text(success + .12, index, f'{success} / {count}', va='center', fontsize=9)
        rows.append({'stage': stage['name'], 'version': version, 'comparison_profile': 'standard',
                     'success': success, 'executions': count, 'steps_if_single_profile': ''})
        subset = [row for row in profile if row['version'] == version]
        if subset:
            assert len(subset) == 1, 'Budget-profile panel expects one separately registered profile'
            item = subset[0]
            profile_axis.text(.04, index, f'{"成功" if item["success"] else "未完成"} · {item["steps"]} 步',
                              va='center', color='#176F58' if item['success'] else '#934429', fontsize=9)
            rows.append({'stage': stage['name'], 'version': version,
                         'comparison_profile': item['comparison_profile'], 'success': int(item['success']),
                         'executions': 1, 'steps_if_single_profile': item['steps']})
        else:
            profile_axis.text(.04, index, '本阶段未单列该 profile', va='center', fontsize=8, color='#64707C')
    count = next(iter(denominators.values()))
    axis.set(yticks=range(len(versions)), yticklabels=[LABELS[v] for v in versions],
             ylim=(len(versions)-.4, -.65), xlim=(0, max(count * 1.18, count + 1)),
             xlabel='成功执行数', title=f'标准条件 · 每组 {count} 次')
    axis.set_xticks(np.arange(0, count + 1, max(1, int(np.ceil(count / 4)))))
    axis.grid(axis='x', alpha=.18)
    axis.set_axisbelow(True)
    profile_axis.set_xlim(0, 1)
    profile_axis.axis('off')
    profile_axis.set_title('预算专用 profile · 单独列示', fontsize=10)
    figure.suptitle(f'v19 · {stage["name"]} · 组件对照', fontsize=11)
    figure.supxlabel('任务成功描述；旧预算组未启用现行持物保护，不能据此整体采用。', fontsize=8)
    caption = (f'{stage["name"]}：标准条件与 clearance-only 父配置的预算 profile 分开统计。'
               '右侧复用 demo6000005，不能当作新增独立起点。每组相同条件配对，条形仅作描述统计；'
               '不同修订不合并分母，不提供总体泛化区间。旧预算组未启用现行持物保护，'
               '任务成功数不代表满足当前保护要求，不能据此整体采用。')
    return save_figure(figure, 'V19_'+stage['name']+'_profiles', stage['name'], caption,
                       rows, stage['sources'], previous)


def plot_targets(stage, previous):
    rows = []
    figure, axis = plt.subplots(figsize=(7.2, 3.5), layout='constrained')
    for y, (label, condition, demo) in enumerate(TARGETS):
        for x, version in enumerate(ORDER):
            matches = [row for row in stage['records'] if row['version'] == version and row['condition'] == condition and row['demo'] == demo]
            assert len(matches) == 1
            row = matches[0]
            axis.add_patch(plt.Rectangle((x-.46, y-.34), .92, .68,
                                         facecolor='#DBF0E7' if row['success'] else '#F7E6DF', edgecolor='white'))
            axis.text(x, y, f'{"成功" if row["success"] else "未完成"}\n{row["steps"]} 步',
                      ha='center', va='center', color='#18352B' if row['success'] else '#673A29', fontsize=8)
            rows.append({key: row[key] for key in ['stage', 'version', 'condition', 'demo', 'comparison_profile', 'success', 'steps', 'result']})
    axis.set(xticks=range(len(ORDER)), xticklabels=[SHORT_LABELS[v] for v in ORDER],
             yticks=range(3), yticklabels=[target[0] for target in TARGETS],
             xlim=(-.55, len(ORDER)-.45), ylim=(2.5, -.55), title=f'三项预登记目标 · {stage["name"]}')
    axis.tick_params(axis='x', labelsize=8)
    axis.tick_params(length=0, pad=9)
    for spine in axis.spines.values():
        spine.set_visible(False)
    figure.supxlabel('A：过渡窗口；B：候选预算；C：终端收敛。A/B/C/AB/ABC均基于完整v18。\n'
                     '任务成功描述；旧预算组未启用现行持物保护，不能据此整体采用。', fontsize=8)
    caption = ('三项预登记目标的真实成功标签与终止步数。A为过渡窗口，B为候选预算，C为终端收敛；'
               'A/B/C/AB/ABC均叠加完整v18。两项任务案例加一项预算配置 profile，'
               '不是三个独立泛化实验；400步未完成不得以抓住、抬起或接近目标代替任务成功。'
               '旧预算组未启用现行持物保护，不能据成功标签整体采用。')
    return save_figure(figure, 'V19_'+stage['name']+'_targets', stage['name'], caption,
                       rows, stage['sources'], previous)


def gate_label(stage):
    passed = stage['analysis'].get('outcome_gate_passed', stage['analysis'].get('adoption_gate_passed'))
    if passed is False:
        return '结果门槛未通过'
    if passed is True and stage['audits_passed']:
        return '结果门槛与回放核验通过'
    if passed is True:
        return '结果门槛通过，回放核验未齐'
    return '描述结果，尚无采用结论'


def diagnosis_findings(latest_smoke):
    """Optional hand-reviewed findings linked to completed actual observations."""
    path = RUN/'analysis/report_findings.json'
    assert path.is_file(), 'Wait for the hand-reviewed findings before publishing the final report.'
    data = read(path)
    assert latest_smoke and data['stage'] == latest_smoke['name']
    findings = data['findings']
    for item in findings:
        assert all(key in item for key in ['title','finding','next_step','sources'])
        assert item['sources'] and all((RUN/source).is_file() for source in item['sources'])
        item['source_sha256'] = {source: sha(RUN/source) for source in item['sources']}
    return findings


def main():
    candidates = sorted([path for path in RUN.iterdir() if path.is_dir() and STAGE_PATTERN.fullmatch(path.name)],
                        key=lambda path: stage_key(path.name))
    stages = [load_stage(path) for path in candidates if (path/'completed.json').is_file()]
    if not stages:
        raise SystemExit('No completed, analyzed stage. No report or figure was generated.')
    assert all(stage['audits_passed'] for stage in stages), 'Wait for both decision and physical replay receipts before publishing final figures.'
    pending = [path.name for path in candidates if not (path/'completed.json').exists() and (path/'started.json').exists()]
    partial_episodes = 0
    for name in pending:
        for path in (RUN/name).glob('*/result.json'):
            saved = read(path)
            partial_episodes += len(saved.get('records', []))
    latest = stages[-1]
    smoke = [stage for stage in stages if family(stage['name']) == 'smoke']
    latest_smoke = smoke[-1] if smoke else None
    outcome = latest['analysis'].get('outcome_gate_passed', latest['analysis'].get('adoption_gate_passed'))
    adopted = bool(family(latest['name']) == 'confirmation' and latest['analysis'].get('adoption_gate_passed') and latest['audits_passed'])
    stopped = bool(latest_smoke and latest_smoke['analysis']['outcome_gate_passed'] is False
                   and all(family(stage['name']) == 'smoke' for stage in stages)
                   and all(family(name) == 'smoke' for name in pending))
    headline = ('小测试门槛未通过；保留候选和负结果，未进入大规模消融、开发或独立确认。' if stopped
                else f'{latest["name"]}：{gate_label(latest)}。版本采用须另有冻结后独立确认依据。')
    checks = []
    for path in sorted((RUN/'analysis').glob('*.json')):
        if (path.stem.startswith(('mechanisms', 'components', 'carry_path_offline'))
                or '_static' in path.stem):
            content = read(path)
            if 'passed' in content:
                checked_sources = checked_receipt_sources(content)
                checks.append({'path': path.relative_to(RUN).as_posix(), 'passed': bool(content['passed']),
                               'matches_current_source': bool(checked_sources) and all(
                                   (ROOT/key).is_file() and sha(ROOT/key)==digest for key,digest in checked_sources.items()),
                               'checked_source_count': len(checked_sources),
                               'scope': content.get('validation_scope', content.get('scope',
                                   '静态/机制诊断，具体检查范围与限制见原记录；不增加闭环评估样本')),
                               'new_evaluation_samples': 0,
                               'sha256': sha(path)})
    required_checks = {'mechanisms_b', 'components_a', 'transition_static_a',
                       'candidate_static_a', 'settling_static_a'}
    current_checks = {Path(check['path']).stem: check for check in checks}
    assert required_checks.issubset(current_checks), 'The five registered preflight receipts are required.'
    assert all(current_checks[name]['passed'] and current_checks[name]['matches_current_source']
               for name in required_checks), 'A registered preflight receipt is failed or stale.'
    counts = Counter()
    for stage in stages:
        counts[family(stage['name'])] += len(stage['records'])
    later = {}
    for key, planned in PLANNED.items():
        started = any(family(path.name) == key and (path/'started.json').exists() for path in candidates)
        later[key] = {'planned_executions': planned, 'completed_executions': counts[key],
                      'started': started, 'status': '已完成记录见阶段明细' if counts[key] else ('已启动但无完整结果' if started else '未运行')}
    diagnoses = diagnosis_findings(latest_smoke)
    summary = {
        'version': 'v19', 'status': 'smoke_gate_failed_not_adopted' if stopped else ('adopted_after_confirmation' if adopted else 'candidate_pending_required_gates'),
        'headline': headline, 'latest_stage': latest['name'],
        'latest_complete_stage': latest['name'], 'adopted': adopted,
        'completed_evaluation_executions': sum(len(stage['records']) for stage in stages),
        'partial_failed_stage_episodes': partial_episodes,
        'completed_stages': {stage['name']: len(stage['records']) for stage in stages},
        'pending_or_aborted_stages': pending, 'latest_complete_variants': latest['analysis']['variants'],
        'action_replay_controls': sum((stage['verification']['verification'] or {}).get('controls', 0)
                                     for stage in stages if (stage['verification']['verification'] or {}).get('passed')),
        'physical_replay_episodes': sum((stage['verification']['physics'] or {}).get('episodes', 0)
                                      for stage in stages if (stage['verification']['physics'] or {}).get('passed')),
        'physical_replay_steps': sum((stage['verification']['physics'] or {}).get('steps', 0)
                                   for stage in stages if (stage['verification']['physics'] or {}).get('passed')),
        'all_completed_stage_audits_passed': all(stage['audits_passed'] for stage in stages),
        'stage_gates': {stage['name']: gate_label(stage) for stage in stages},
        'later_stages': later, 'new_training_runs': 0, 'new_weights': 0,
        'registered_executions_per_complete_stage': EXPECTED_EXECUTIONS,
        'variant_order': ORDER,
        'component_design': {'parent': 'Full actual v18', 'A': 'transition_window',
                             'B': 'candidate_budget', 'C': 'terminal_settling',
                             'evaluated_new_combinations': ['A','B','C','AB','ABC'],
                             'not_evaluated': ['AC','BC']},
        'smoke_profiles_per_version': 9, 'smoke_unique_start_identities_per_version': 8,
        'mechanism_and_static_receipts': checks,
        'pre_experiment_static_risk': {'description': STATIC_ROUTE_RISK,
                                       'source': 'analysis/candidate_static_a.json',
                                       'new_evaluation_samples': 0},
        'diagnostic_findings': diagnoses,
        'sample_scope': 'Nine registered smoke conditions comprise eight standard conditions plus a clearance-only parent configuration profile reusing demo6000005. Executions and profiles are not independent starts.',
        'limitations': ['Known diagnostic profiles cannot establish generalization.',
                        'Local hand/carried-object geometry and waypoint IK do not prove full-arm physical safety.',
                        'Planning receipts, mechanism events and stable grasps are not complete-task successes.',
                        'Shared recovery gains are not evidence of a world-model-specific advantage.',
                        'Action and physical replays do not add evaluation samples.'],
    }
    FIGURES.mkdir(exist_ok=True)
    catalog_path = FIGURES / 'CATALOG.json'
    previous = {item['id']: item for item in read(catalog_path)} if catalog_path.is_file() else {}
    figure_settings()
    catalog = previous.copy()
    for stage in stages:
        if family(stage['name']) in ['smoke', 'pilot', 'dev']:
            item = plot_stage(stage, previous)
            catalog[item['id']] = item
    if latest_smoke:
        item = plot_targets(latest_smoke, previous)
        catalog[item['id']] = item
    catalog_path.write_text(json.dumps(list(catalog.values()), indent=2, ensure_ascii=False), encoding='utf-8')
    summary['figures'] = list(catalog)
    (RUN/'SUMMARY.json').write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding='utf-8')
    report = ['# v19 实验与交付报告', '', '**'+headline+'**', '',
              '本轮在完整v18上检查A：有界过渡窗口、B：可选候选预算和C：持物终端收敛。'
              '八组为本轮实际重跑的v17、完整v18、v15仅预算，以及完整v18分别加A、B、C、AB和ABC（完整v19）。'
              'A/B/C/AB均保留完整v18和所有历史模块，不能称为从v17单独新增一项。没有AC/BC两组，不声称完整三因子交互估计。'
              '原预算组同样实际重跑，但未启用后来加入的持物保护，仅作成功数约束参考，不能整体回退采用。'
              '旧版本、权重与原始结果保留；本轮不训练、不写论文。', '',
              '**执行前已发现的静态风险：** '+STATIC_ROUTE_RISK+' '
              '[离线原始记录](analysis/candidate_static_a.json)。', '',
              '## 约束与信息范围', '',
              '400 控制步、20 Hz、D2 FIFO、最多两次抓取，规划和等待均计入总步数。'
              '沿用9 mm/0.08 rad到位、5帧稳定、0.04 rad局部IK关节余量、1 mm手/箱路径、3 mm规划手/物体、1 mm执行手/物体及原开度/位姿保护。'
              '闭合与释放时长不缩短。控制只使用当前观测、历史和当前关节，不使用接触、奖励、成功标签或未来状态。', '',
              '## 已完成执行与门槛', '',
              '| 阶段 | '+' | '.join(LABELS[v] for v in ORDER)+' | 结果及核验 |',
              '|---|'+'---:|'*len(ORDER)+'---|']
    for stage in stages:
        values = [f'{stage["analysis"]["variants"][v]["success"]}/{stage["analysis"]["variants"][v]["episodes"]}'
                  if v in stage['analysis']['variants'] else '本阶段未单跑' for v in ORDER]
        report.append('| '+stage['name']+' | '+' | '.join(values)+' | '+gate_label(stage)+' |')
    report += ['', f'完整阶段累计 **{summary["completed_evaluation_executions"]} 次闭环执行**。'
               '不同修订与变体共享诊断条件；不得将这些执行数解释为独立起点数或合并成总体成功率。', '',
               '**小测试的9个条件不等于9个独立起点。** 其中8个为原标准条件，另1个是复用 demo6000005 的 clearance-only 父配置 profile。'
               '该专用 profile 在八组中按登记的继承配置配对，用于检查预算退步；图表将它单列。'
               '单轮小测试72次、后续消融752次、开发v17/v18/v19各240次合计720次、独立确认1440次；只有实际完成并核验的记录才计入成果。', '',
               '| 后续阶段 | 预定本轮执行数 | 完整执行数 | 状态 |', '|---|---:|---:|---|']
    for key, data in later.items():
        report.append(f'| {FAMILY_LABELS[key]} | {data["planned_executions"]} | {data["completed_executions"]} | {data["status"]} |')
    if stopped:
        report += ['', '**小测试失败后，752次消融、720次开发对照（v17/v18/v19各240）及1440次独立确认均未运行。** '
                   '计划文件或运行入口的存在不代表实验已执行，也没有独立确认支持采用v19。']
    if pending:
        report += ['', '以下已启动阶段没有完整结果，未计入完整阶段汇总：'+', '.join(pending)+'。']
    target_html = []
    if latest_smoke:
        report += ['', '## 最新小测试：三项目标逐项核对', '', '| 目标 / profile | '+' | '.join(LABELS[v] for v in ORDER)+' |',
                   '|---|'+'---|'*len(ORDER)]
        for label, condition, demo in TARGETS:
            cells = []
            html_cells = []
            for version in ORDER:
                row = next(row for row in latest_smoke['records'] if row['version'] == version and row['condition'] == condition and row['demo'] == demo)
                text = f'{"成功" if row["success"] else "未完成"}，{row["steps"]}步'
                cells.append(f'[{text}]({row["result"]})')
                html_cells.append(f'<td><a href="{esc(row["result"])}">{esc(text)}</a></td>')
            report.append('| '+label+' / '+demo+' | '+' | '.join(cells)+' |')
            target_html.append(f'<tr><th>{esc(label)}<small>{esc(demo)}</small></th>{"".join(html_cells)}</tr>')
        combined = latest_smoke['analysis']['variants']['v19']
        report += ['', '原v14失败目标的完成数：'+str(len(combined.get('target_rescues', [])))+' / '+str(len(TARGETS))+'。'
                   '预算profile已在v15和预算候选中成功，不能把重复完成说成相对这些版本的新救回。'
                   '只有整回合成功才计作完成，抓住、抬起、路径证书通过或局部误差变小都不能替代这个判据。']
        report.append('')
        for reference in ['v17', 'v18', 'budget', 'v16', 'v15', 'v14', 'v13', 'v6']:
            regressions = combined.get('regressed_vs_'+reference, [])
            report.append(f'- 相对 {reference} 的已配对成功退步：{len(regressions)}；配对覆盖 {combined.get("paired_reference_"+reference, 0)} 个条件。'
                          + (' 条件：'+'；'.join('/'.join(item) for item in regressions)+'。' if regressions else ''))
    if diagnoses:
        report += ['', '## 具体失败原因与下一步', '']
        for item in diagnoses:
            report += ['### '+item['title'], '', item['finding'], '', '**下一步方案：** '+item['next_step'], '',
                       '依据：'+' / '.join(f'[{Path(path).name}]({path})' for path in item['sources']), '']
    report += ['', '## 核验与证据边界', '',
               f'- 保存输入动作/FIFO/噪声核验：已通过记录合计 {summary["action_replay_controls"]:,} 控制步。',
               f'- 物理回放：已通过记录合计 {summary["physical_replay_episodes"]} 回合、{summary["physical_replay_steps"]:,} 步；不增加统计样本。',
               '- 每一轮源代码快照和结果保留；本报告校验快照哈希并从原始result重新核对成功数与分析汇总。',
               '- 关闭开关一致性、静态几何/IK、完整决策回放、物理回放是不同验证范围，不能相互替代。']
    for check in checks:
        version_scope='源哈希与当前版本一致' if check['matches_current_source'] else '历史诊断，不能作为当前源码的通过凭证'
        report.append(f'- [{Path(check["path"]).name}]({check["path"]})：{"通过" if check["passed"] else "未通过"}；{version_scope}；{check["scope"]}')
    report += ['', '图表为真实数据的分类计数或目标矩阵，输出600 dpi PNG及矢量PDF/SVG，附CSV和来源SHA-256。'
               '没有平滑、没有把任意案例排序连成折线，也没有给已挑选小测试附加泛化置信区间。'
               '图片实际外观、PDF字体、前端显示、链接与Git同步须由交付验证另行确认；生成文件本身不等于这些检查已经通过。', '',
               '## 整体评估', '',
               '本轮可以形成可追溯的实现、组件对照与失败分析材料，能够补充本科毕业设计。'
               '是否达到学校或导师的正式毕业标准，仍需按实际要求审定。历史项目证据没有被本轮替换；'
               '若本轮门槛未过，只能把v19作为探索和负结果，不能作为已确认的新增性能成果。', '',
               '仍需区分局部规划可行与实际执行完成、共享恢复贡献与世界模型独有贡献，以及已知诊断条件和独立确认。'
               '不应宣称项目完美、总体优于强基线或已获得完整机械臂安全保证。', '',
               '## 复核入口', '', '- [执行前协议](protocols/PLAN.md)', '- [机器可读汇总](SUMMARY.json)',
               '- [前端证据页](index.html)', '- [图表来源目录](figures/CATALOG.json)',
               '- [v18原报告](../improvement_v18_20261019_01/REPORT.md)',
               '- [v14既有历史演示](../improvement_v14_20261016_01/index.html#demo)', '',
               '本轮页面没有新增或冒用机器人视频；上面的演示链接明确指向v14历史记录。']
    for stage in stages:
        report.append(f'- [{stage["name"]}原始分析](analysis/{stage["name"]}.json) / [作业条件]({stage["name"]}/jobs.json)')
    report += ['', '每份机制/静态检查仅对应其记录的源哈希；以实际阶段快照和逐步核验确认受测源码，不把早期检查的通过自动转移到后续修订。']
    (RUN/'REPORT.md').write_text('\n'.join(report)+'\n', encoding='utf-8')
    readme = [
        '# v19：过渡窗口、候选预算与终端收敛', '', '**'+headline+'**', '',
        '本目录保存独立的v19实现、固定协议、真实执行、核验与图表。父版本和历史权重/结果保留；本轮不训练、不写论文。', '',
        '## 查看前端', '', '在项目根目录的 PowerShell / PyCharm Terminal 执行：', '', '```powershell',
        "Set-Location 'C:\\Users\\Livio\\Desktop\\robot_can'",
        "& '.\\.venv\\Scripts\\python.exe' -m http.server 8766 --bind 127.0.0.1", '```', '',
        '保持该终端运行，浏览器打开完整页面地址：', '',
        '[http://127.0.0.1:8766/reproduction/improvement_v19_20261019_01/index.html](http://127.0.0.1:8766/reproduction/improvement_v19_20261019_01/index.html)', '',
        '如果8766已经由同一项目根目录提供服务，直接打开上述地址。根地址显示的是目录列表。', '',
        '## 结果与证据', '',
        f'- 已完成评估：{summary["completed_evaluation_executions"]}次；采用状态：{"已通过冻结后独立确认" if adopted else "未采用"}。',
        '- [完整报告](REPORT.md) / [机器可读汇总](SUMMARY.json) / [执行前协议](protocols/PLAN.md)。',
        '- [图表目录及来源](figures/CATALOG.json)：600 dpi PNG、矢量PDF/SVG和原始绘图CSV。',
        '- 每组9个小测试profile包括8个标准起点和1个复用6000005的配置；八组执行不能相加当作独立样本。',
        '- A/B/C/AB/ABC全部继承完整v18。旧v15预算组保护不同，仅作成功数参考。', '',
        '| 后续阶段 | 预定执行数 | 当前状态 |', '|---|---:|---|',
        *[f'| {FAMILY_LABELS[key]} | {value["planned_executions"]} | {value["status"]} |' for key,value in later.items()], '',
        '保存输入回放、物理回放和静态检查均不是新增统计样本。论文使用本目录数据时，应保留阶段、版本、分母和保护差异说明。', '',
        '## 重新生成交付文件', '',
        '仅在对应完整结果、动作/物理核验、五项有效预检以及人工核对的report_findings都已存在时运行：', '',
        '```powershell', "& '.\\.venv\\Scripts\\python.exe' -B -X utf8 'reproduction/improvement_v19_20261019_01/build_report.py'", '```', '',
        '该命令只读取保存结果，不启动实验。已有图表会验证来源和输出哈希；若变化则拒绝覆盖。首次导出图表需要本机nature-figure的Python布局核验工具，可通过FIGURE_QA_SCRIPTS指定其scripts目录。',
    ]
    (RUN/'README.md').write_text('\n'.join(readme)+'\n', encoding='utf-8')

    stage_rows = []
    for stage in stages:
        metrics = ' · '.join(f'{LABELS.get(v, v)} {data["success"]}/{data["episodes"]}' for v, data in stage['analysis']['variants'].items())
        links = [f'<a href="analysis/{stage["name"]}.json">统计</a>', f'<a href="{stage["name"]}/jobs.json">条件</a>']
        for suffix, label in [('verification', '动作核验'), ('physics', '物理回放')]:
            if (RUN/'analysis'/f'{stage["name"]}_{suffix}.json').is_file():
                links.append(f'<a href="analysis/{stage["name"]}_{suffix}.json">{label}</a>')
        stage_rows.append(f'<tr><th>{esc(stage["name"])}</th><td>{esc(metrics)}</td><td>{esc(gate_label(stage))}</td><td>{" · ".join(links)}</td></tr>')
    cards = []
    for version in ORDER:
        selected = [row for row in latest['records'] if row['version'] == version]
        if not selected:
            continue
        standard = [row for row in selected if row['comparison_profile'] == 'standard']
        profile = [row for row in selected if row['comparison_profile'] != 'standard']
        budget_text = f'{sum(row["success"] for row in profile)}/{len(profile)}' if profile else '本阶段未单列'
        cards.append(f'<article class="metric"><span>{esc(LABELS[version])}</span><strong>{sum(row["success"] for row in standard)}<i> / {len(standard)}</i></strong><p>标准条件</p><div>预算专用 profile <b>{budget_text}</b></div></article>')
    figures = []
    for item in catalog.values():
        name = item['id']
        figures.append(f'<figure><img loading="lazy" src="figures/{esc(name)}.svg" alt="{esc(item["caption"])}"><figcaption>{esc(item["caption"])}<p><a href="figures/{name}.png">600 dpi PNG</a><a href="figures/{name}.pdf">矢量 PDF</a><a href="figures/{name}.svg">SVG</a><a href="figures/{name}.csv">数据 CSV</a></p></figcaption></figure>')
    future = ''.join(f'<article><span>{FAMILY_LABELS[key]}</span><h3>{data["status"]}</h3><p>预定 {data["planned_executions"]} 次；完整记录 {data["completed_executions"]} 次。</p></article>' for key, data in later.items())
    targets = ('<section><span class="eyebrow">REGISTERED TARGETS</span><h2>整回合是否完成，逐项查看。</h2><p>已知诊断案例，不能作为独立泛化结论。预算profile复用旧6000005；八组按登记条件配对，A/B/C/AB分别改变完整v18上的对应开关，完整v19为ABC。旧预算组未启用现行持物保护，只能参考。</p><div class="table-wrap"><table><thead><tr><th>目标</th>'
               + ''.join('<th>'+esc(LABELS[v])+'</th>' for v in ORDER)
               + '</tr></thead><tbody>'+''.join(target_html)+'</tbody></table></div></section>') if target_html else ''
    diagnosis_html = '<section><span class="eyebrow">DIAGNOSIS &amp; NEXT STEPS</span><h2>哪里没有完成，下一步改哪里。</h2>' if diagnoses else ''
    for item in diagnoses:
        diagnosis_html += '<article style="margin-top:18px"><h3>'+esc(item['title'])+'</h3><p>'+esc(item['finding'])+'</p><p><strong>下一步：</strong>'+esc(item['next_step'])+'</p><p>'+' · '.join(f'<a href="{esc(path)}">{esc(Path(path).name)}</a>' for path in item['sources'])+'</p></article>'
    if diagnoses:
        diagnosis_html += '</section>'
    style = '''
*{box-sizing:border-box}html{scroll-behavior:smooth;scroll-padding-top:90px}body{margin:0;background:radial-gradient(ellipse at 90% 0,#152932 0,transparent 35%),#080b10;color:#e8edf2;font:15px/1.75 -apple-system,BlinkMacSystemFont,"Segoe UI","Microsoft YaHei",sans-serif}a{color:#a5dfce;text-decoration:none}a:hover{color:white}a:focus-visible{outline:2px solid #bcebdd;outline-offset:4px}nav{position:sticky;top:0;z-index:5;display:flex;justify-content:space-between;gap:24px;padding:16px max(24px,calc((100vw - 1220px)/2));border-bottom:1px solid #29343e;background:#080c12e8;backdrop-filter:blur(18px)}nav strong{font-size:12px;letter-spacing:2px}nav div{display:flex;gap:24px;font-size:13px}main{max-width:1220px;margin:auto;padding:0 28px 60px}header{display:grid;grid-template-columns:1fr 260px;gap:70px;align-items:center;padding:85px 0 55px}.eyebrow{font-size:11px;letter-spacing:2px;color:#8fa4b2}h1{font-size:clamp(34px,4.5vw,62px);line-height:1.2;letter-spacing:-2px;font-weight:550;margin:22px 0}h2{font-size:30px;line-height:1.35;font-weight:500;letter-spacing:-.6px}h3{font-size:20px;font-weight:500;margin:10px 0}p{color:#aab7c4;margin:14px 0}header p{max-width:790px}.status{padding:18px 0;border-top:1px solid #36434a;color:#f0d5b8;font-size:16px}.button{display:inline-block;padding:10px 17px;margin:10px 12px 0 0;border:1px solid #47605d;border-radius:10px}.constraint{padding:26px;border:1px solid #35464d;border-radius:24px;background:linear-gradient(140deg,#17242c,#0e151d)}.constraint strong{font-size:78px;font-weight:450;letter-spacing:-5px;line-height:1.2}.constraint div{display:flex;justify-content:space-between;padding:12px 0;border-top:1px solid #34434b;font-size:12px}.cards{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:13px}article{border:1px solid #2b3743;border-radius:17px;padding:21px;background:#101720}article span{font-size:12px;color:#aab8c6}.metric strong{display:block;font-size:38px;font-weight:500;margin:13px 0 0}.metric i{font-style:normal;font-size:21px;color:#94a4b4}.metric p{margin:0 0 20px;font-size:12px}.metric div{padding-top:15px;border-top:1px solid #2b3c45;font-size:11px;color:#9dabb9}.metric b{float:right;color:#d3e5df;font-weight:500}section{margin-top:66px}.note{padding:23px 27px;border-left:3px solid #79b9a6;background:#111d24;border-radius:0 16px 16px 0;margin-top:28px}.note p:last-child{margin-bottom:0}.future{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px}.table-wrap{overflow-x:auto;border:1px solid #2b3844;border-radius:16px}table{border-collapse:collapse;width:100%;font-size:13px}th,td{text-align:left;border-bottom:1px solid #27343d;padding:16px;vertical-align:top}thead{background:#14202b}th{font-weight:500}td{color:#acbac7}small{display:block;color:#7e96a6;font-size:10px;margin-top:6px}figure{background:white;border-radius:16px;overflow:hidden;margin:25px 0;padding:22px}figure img{width:100%;display:block}figcaption{font-size:13px;color:#44515e;padding:15px 9px 0}figcaption a{color:#146f78;margin-right:20px}figcaption p{margin-bottom:0}footer{margin-top:65px;padding-top:25px;border-top:1px solid #2e3c45;display:flex;justify-content:space-between;gap:20px;font-size:12px;color:#8b9cab}.history-link{border:1px dashed #3b514e;border-radius:16px;padding:23px}.history-link strong{font-weight:500}.history-link p{font-size:13px;margin-bottom:0}@media(max-width:1000px){.cards{grid-template-columns:repeat(2,1fr)}header{gap:30px;grid-template-columns:1fr 210px}.constraint strong{font-size:64px}}@media(max-width:680px){main{padding:0 18px 40px}nav{padding:14px 18px}nav div{gap:14px}nav strong{display:none}header{grid-template-columns:1fr;padding:50px 0 30px}.constraint{display:none}.cards{grid-template-columns:repeat(2,1fr)}.future{grid-template-columns:1fr}h1{letter-spacing:-1px}h2{font-size:25px}th,td{padding:12px;min-width:110px}figure{padding:10px}section{margin-top:45px}footer{flex-direction:column}}@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}}
'''
    page = f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="icon" href="data:,"><title>CAN LAB · v19 实验与证据</title><style>{style}</style></head><body>
<nav><strong>CAN LAB / RECOVERY 19</strong><div><a href="../improvement_v18_20261019_01/index.html">v18</a><a href="#experiments">执行记录</a><a href="#evidence">图表与证据</a></div></nav><main>
<header><div><span class="eyebrow">BOUNDED SEARCH · GUARDED CONVERGENCE</span><h1>把时间留给执行，<br>用整回合验证。</h1><p>分别验证有界过渡窗口、候选预算与持物终端收敛。八组同条件实际运行；v17、完整v18和原预算组均在本轮重跑，A/B/C/AB与完整ABC全部加在完整v18之上。原v15预算组未启用现行持物保护，仅作成功数参考，不能据此整体采用。</p><p class="status">{esc(headline)}</p><a class="button" href="REPORT.md">完整评估报告 ↗</a><a class="button" href="protocols/PLAN.md">执行前协议 ↗</a></div><aside class="constraint"><strong>400</strong><p>固定控制步预算</p><div><span>执行延迟</span><b>D2 FIFO</b></div><div><span>控制频率</span><b>20 Hz</b></div><div><span>抓取尝试</span><b>≤ 2</b></div><div><span>保护阈值</span><b>保持原值</b></div></aside></header>
<p>最新完整阶段：{esc(latest['name'])} · 下列主数字仅统计标准条件，预算专用profile另列。</p><div class="cards">{''.join(cards)}</div>
<section class="note"><strong>执行数与独立样本必须分开。</strong><p>完整阶段累计 {summary['completed_evaluation_executions']} 次评估执行。同一条件在不同版本和修订中重复，9个小测试条件包括8个标准条件与1个复用起点的配置profile，不能写成9个独立起点。</p><p>规划证书、保存输入回放、物理回放和完整任务成功是不同证据。旧权重冻结；本轮不做泛化训练，也不写论文。</p><p><strong>执行前静态风险：</strong>{esc(STATIC_ROUTE_RISK)} <a href="analysis/candidate_static_a.json">查看离线记录</a>。</p></section>
{targets}{diagnosis_html}<section><span class="eyebrow">STAGE GATES</span><h2>后续实验，按门槛推进。</h2><div class="future">{future}</div><p>小测试72次；消融752次；开发共720次，分别为v17、v18和v19各240次；独立确认1440次，须先冻结，再使用全新起点。未运行的数据不会填成结果。</p></section>
<section id="experiments"><span class="eyebrow">TRACEABLE RESULTS</span><h2>每轮修订，保留完整记录。</h2><div class="table-wrap"><table><thead><tr><th>阶段</th><th>成功数 / 执行数</th><th>门槛状态</th><th>原始依据</th></tr></thead><tbody>{''.join(stage_rows)}</tbody></table></div><p>已通过的动作核验共 {summary['action_replay_controls']:,} 控制步；物理回放 {summary['physical_replay_episodes']} 回合、{summary['physical_replay_steps']:,} 步。回放不增加成功率样本。</p></section>
<section id="evidence"><span class="eyebrow">FIGURES &amp; SOURCE DATA</span><h2>分类对照，直接呈现。</h2><p>不把任意条件顺序连成趋势线，不对已知小测试附加泛化区间。每图提供600 dpi位图、矢量文件和绘图数据，来源哈希在<a href="figures/CATALOG.json">图表目录</a>中。</p>{''.join(figures)}</section>
<section class="history-link"><strong>历史机器人演示 · 明确保留版本</strong><p>本页没有新增v19演示视频。<a href="../improvement_v14_20261016_01/index.html#demo">查看v14原始对比演示 ↗</a>，其中动作与结果仍属于历史v14实验，不能视为本轮成果。</p></section>
<footer><span>400 steps · D2 FIFO · fixed weights</span><span><a href="SUMMARY.json">机器可读汇总</a> · <a href="../improvement_v18_20261019_01/REPORT.md">父版本报告</a></span></footer></main></body></html>'''
    (RUN/'index.html').write_text(page, encoding='utf-8')
    print(json.dumps({'status': summary['status'], 'completed_executions': summary['completed_evaluation_executions'],
                      'stages': list(summary['completed_stages']), 'figures': len(catalog)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
