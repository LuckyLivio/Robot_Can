"""Resolve count flags against explicit diagnostic subsets; inventory all modules."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];RUN=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text(encoding='utf-8'))
flags=read(RUN/'audit_validation.json')['legacy_incomplete_or_partial_results'];qualified=[]
for row in flags:
    d=read(ROOT/row['path']);actual=[r['demo'] for r in d['records']]
    assert actual==d['resolved_demos'] and set(actual)==set(d['args']['demos'])
    qualified.append({'path':row['path'],'verdict':'intentional_explicit_diagnostic_subset_complete','episodes':len(actual),'resolved_demos':actual})
legacy=[]
for p in (ROOT/'queue_v2/results').rglob('result.json'):
    d=read(p);assert len(d['records'])==d['args']['episodes']
    legacy.append({'path':p.relative_to(ROOT).as_posix(),'episodes':len(d['records']),'success':sum(r['success'] for r in d['records']),'delay':d['args']['delay'],'method':d['args']['method']})
payload={'passed':True,'count_flag_note':'audit_validation count flags use requested episodes only; explicit --demos overrides that cap. They are not unfinished runs.',
         'all17_flags_resolved_as_intentional_subsets':qualified,'unresolved_flag_count':0,'queue_v2_legacy_closed_loop':legacy,
         'legacy_no_status_caveat':'130 result files lack the modern complete marker. Artifact presence is historical evidence, not proof that every old script has been re-executed under the present runtime.'}
(RUN/'inventory_qualifications.json').write_text(json.dumps(payload,indent=2,ensure_ascii=False),encoding='utf-8')
groups=[
('common.py world_model.py','当前主线公共实现','18份世界模型和BC前向测试、历史闭环哈希；本次smoke_env恢复检查'),
('bootstrap.py inspect_data.py','数据准备','原HDF5哈希、200轨迹、140/30/30划分；已有下载/检查清单；本次未重复下载'),
('download_wheel.py setup_windows.py','历史环境辅助','历史Windows DLL兼容记录；当前依赖检查和Panda仿真通过；本次未执行安装/补丁脚本'),
('smoke_env.py','恢复验证','本次实际执行，两个父轨迹、四个中途分支位置、顺逆序和XML重复检查通过'),
('train_policy.py evaluate_policy.py','BC训练/评估','历史BC日志/权重/评估存在；当前固定BC前向和确认输出已核对；本次未重训BC'),
('collect_branches.py collect_delay_branches.py','历史分支采集及标签工具','历史NPZ/JSON存在；现行采集使用collect_rollout_branches；旧数据不混入现行主表'),
('collect_rollout_branches.py','当前真实队列分支采集','160训练组/64开发组、20/8父轨迹、数据哈希与队首一致性通过'),
('train_world.py','通用世界模型训练入口','历史训练权重/日志存在；当前三种子主线通过multiseed/train_suite.py执行'),
('evaluate_delay.py','当前FIFO闭环核心','60开发任务和14确认任务全部完成；确认适配器核心锁定，演示18回放已验收'),
('analyze_delay_traces.py','轨迹诊断','decision_diagnostic/final_analysis/analysis.json与diagnosis.txt'),
('run_queue_coverage_probe.py analyze_queue_coverage.py','队列覆盖诊断','queuepair_20261012_01/analysis/analysis.json及诊断图'),
('diagnose_candidate_truth.py','同状态真实后果诊断','7起点、28候选、84续接；仅局部诊断，非全面oracle闭环'),
('calibrate_score_head.py analyze_head_calibration.py','评分头控制/校准','单种子探索及三种子匹配预算控制/校准；18份选点权重中包含6份评分头变体'),
('evaluate_candidate_rollout.py','候选续接探索','tailprobe_20261012_01保留结果；不纳入60新起点主确认'),
('evaluate_world_control.py evaluate_gated_mpc.py evaluate_state_mpc.py evaluate_task_mpc.py','早期MPC探索','models内control_、gated_、state_mpc_、taskmpc_结果存在；本次仅存量核对，未重新运行'),
('adaptive_model.py collect_response.py train_response.py fit_linear_response.py evaluate_adaptive.py','执行偏差适应探索','response数据/模型及evaluation内7份结果；独立历史分支，未纳入当前三种子主线'),
('train_wm_aug_policy.py','世界模型辅助BC探索','policy/wm_aug_low20权重、日志和eval_dev_0.0_policy.json存在；非当前主方法'),
('queue_v2.py','队列补偿探索','2个已训练模型；results子目录中5组D=4试验，每组12回合；非当前确认'),
('make_figures.py','历史绘图','硬编码旧结果；仅保留归档用途，当前图由两轮analysis脚本读取原始JSON生成')]
covered=[];rows=[]
for names,scope,evidence in groups:
    for name in names.split():assert (ROOT/name).is_file();covered.append(name)
    rows.append({'files':names.split(),'scope':scope,'evidence_and_limit':evidence})
assert len(covered)==len(set(covered)) and set(covered)=={p.name for p in ROOT.glob('*.py')}
(RUN/'module_inventory.json').write_text(json.dumps({'root_scripts':len(covered),'groups':rows},indent=2,ensure_ascii=False),encoding='utf-8')
print(json.dumps({'resolved_diagnostic_count_flags':len(qualified),'legacy_queue_v2_jobs':len(legacy),'root_scripts_classified':len(covered)}))
