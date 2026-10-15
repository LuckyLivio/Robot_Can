"""Rebuild thesis tables from existing files only; standard library; no ML or simulator imports.

Sources: ../04_snapshot when complete; original checkout is a development fallback.
Writes only into this 02_tables directory. No result, model or dataset is changed.
"""
from pathlib import Path
from collections import Counter, defaultdict
import csv
import hashlib
import json
import math
import statistics

OUT = Path(__file__).resolve().parent
PACK = OUT.parent
REPO = PACK.parent
TABLES = []
PROVENANCE = []
CHECKS = []


def source(rel):
    for base in (PACK / "04_snapshot", REPO):
        path = base / rel
        if path.is_file():
            return path
    raise FileNotFoundError(f"Missing source in snapshot and checkout: {rel}")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def jload(rel):
    return json.loads(source(rel).read_text(encoding="utf-8-sig"))


def cload(rel):
    with source(rel).open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def val(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")) if isinstance(value, (list, dict)) else value


def write_csv(path, rows):
    fields = list(dict.fromkeys(k for row in rows for k in row))
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows({k: val(v) for k, v in row.items()} for row in rows)


def display(value):
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(val(value) if value is not None else "").replace("|", "\\|").replace("\n", " ")


def table(name, title, rows, sources, *, cohort, independent_n, seeds, scope, note):
    """Metadata is added without changing original numeric fields."""
    sources = list(dict.fromkeys(sources))
    cooked = []
    for raw in rows:
        row = dict(raw)
        row.setdefault("dataset", cohort)
        row.setdefault("cohort", cohort)
        row.setdefault("condition", "clean" if str(row.get("noise", "")) in ("0", "0.0") else
                       "noise005" if str(row.get("noise", "")) in ("0.05",) else "see_row_or_catalog")
        row.setdefault("independent_N", independent_n(row) if callable(independent_n) else independent_n)
        row.setdefault("seed_count", seeds(row) if callable(seeds) else seeds)
        row.setdefault("source_repo_path", row.get("source", ";".join(sources)))
        row.setdefault("evidence_scope", scope)
        cooked.append(row)
    write_csv(OUT / f"{name}.csv", cooked)
    fields = list(cooked[0]) if cooked else []
    # Full CSV remains canonical. These short views are intended for immediate reading.
    show = [f for f in fields if f not in ("dataset", "cohort", "source_repo_path", "evidence_scope")]
    if len(cooked) <= 90 and len(show) <= 20:
        lines = [f"# {title}", "", note, "", f"完整数值：`{name}.csv`。Markdown 仅显示约 6 位有效数字。", "",
                 "| " + " | ".join(show) + " |", "| " + " | ".join("---" for _ in show) + " |"]
        lines += ["| " + " | ".join(display(row.get(f, "")) for f in show) + " |" for row in cooked]
        (OUT / f"{name}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    TABLES.append({"table": f"{name}.csv", "title": title, "rows": len(cooked), "cohort": cohort,
                   "independent_N": "row-specific" if callable(independent_n) else independent_n,
                   "seed_count": "row-specific" if callable(seeds) else seeds, "scope": scope, "note": note,
                   "sources": sources})
    for rel in sources:
        p = source(rel)
        PROVENANCE.append({"derived_table": f"{name}.csv", "source_repo_path": rel,
                           "source_sha256": sha(p), "source_bytes": p.stat().st_size,
                           "source_resolved_from": "04_snapshot" if PACK / "04_snapshot" in p.parents else "original_checkout",
                           "derived_sha256": sha(OUT / f"{name}.csv")})
    return cooked


def check(label, condition, detail):
    CHECKS.append({"check": label, "passed": bool(condition), "detail": detail})
    if not condition:
        raise AssertionError(f"{label}: {detail}")


def success(value):
    return str(value).lower() in ("true", "1")


def is_close(left, right):
    return math.isclose(float(left), float(right), abs_tol=1e-8)


CONF = "reproduction/confirmation_20261012_01/analysis/"
DEV = "reproduction/multiseed_20261012_01/analysis/"
EXT = "reproduction/extensions_20261012_01/"
V5 = "reproduction/recovery_v5_20261012_01/"
DEEP = "reproduction/figures_deepcheck_20261014_01/"
CROSS = "paired crossed bootstrap of starts and training seeds; existing 20,000 draws; pointwise 95% CI"
FIXED = "existing paired-start bootstrap; 3 fixed Full seeds averaged within start; pointwise 95% CI; no retraining uncertainty"
WM_NOTE = "独立确认：60 个全新起点，clean/noise 重用同一批起点；BC 固定权重，Full/Plain 各 3 个训练种子。联合结果等权平均两条件，仍只有 60 个独立起点。区间沿用原有配对交叉 bootstrap。"
DEV_NOTE = "反复查看的 30 个开发起点；用于模型/参数选择和消融，不能作为独立泛化确认。各方法的训练种子数见行字段；BC 的 0 表示固定策略且无世界模型训练种子。"
EXT_NOTE = "补充开发诊断：复用 30 个已知起点。H/K 的结果依赖既有 D=2、门控和 k=2 回退；H=1、K=1、持续性基线始终回退。K=8 超出训练时 K=0..3 候选支持。oracle 只对既定候选用真值排序，不是全局最优控制器。"
V5_NOTE = "v5 独立确认的 60 个新起点，与 WM 主确认的 60 个起点不是同一批。每版本 480 次执行是 BC 2 条件 + Full 3 种子×2条件；仍只有 60 个独立起点。overall_execution_mix 为预定 8 次执行等权（BC 占1/4、Full占3/4），不能解释成模型等权平均。"


def csv_table(name, title, rel, **kwargs):
    return table(name, title, cload(rel), [rel], **kwargs)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    conf = jload(CONF + "analysis.json")
    dev = jload(DEV + "analysis.json")
    ce = cload(CONF + "episodes.csv")
    de = cload(DEV + "episodes.csv")
    check("WM confirmation episode/parent count", len(ce) == conf["validation"]["episode_records"] and len({r["demo"] for r in ce}) == conf["validation"]["independent_initial_states"], "CSV and analysis.json agree")
    check("Development episode/parent count", len(de) == dev["verification"]["episode_records"] and len({r["demo"] for r in de}) == len(dev["dev_parent_order"]), "CSV and analysis.json agree")
    for rel, episodes in [(CONF + "per_seed.csv", ce), (DEV + "per_seed.csv", de)]:
        for row in cload(rel):
            target = [e for e in episodes if e["method"] == row["method"] and e["seed"] == row["seed"] and
                      e.get("condition", e.get("noise")) == row.get("condition", row.get("noise"))]
            check(f"per-seed counts {rel}:{row['method']}:{row['seed']}:{row.get('condition', row.get('noise'))}",
                  len(target) == int(row["episodes"]) and sum(success(e["success"]) for e in target) == int(row["success"]), "Derived counts match episode records")
    for row in conf["summary"]:
        selected = [e for e in ce if e["method"] == row["method"] and (row["condition"] == "joint_equal_weight" or e["condition"] == row["condition"])]
        check(f"WM summary {row['method']} {row['condition']}", is_close(100 * sum(success(e['success']) for e in selected) / len(selected), row["mean_success_percent"]), "Summary rate matches episode records")
    for row in cload(CONF+'summary.csv'):
        reference=next(r for r in conf['summary'] if r['method']==row['method'] and r['condition']==row['condition'])
        check(f"WM summary CSV/JSON {row['method']} {row['condition']}",is_close(row['mean_success_percent'],reference['mean_success_percent']),'Flat table agrees with JSON analysis')
    for row in cload(DEV+'summary.csv'):
        selected=[e for e in de if e['method']==row['method'] and e['noise']==row['noise']]
        check(f"Development summary {row['method']} {row['noise']}",is_close(100*sum(success(e['success']) for e in selected)/len(selected),row['mean_success_percent']),'Summary rate matches all existing episode records')

    confmeta = dict(cohort="wm_confirmation_60_new_starts", independent_n=60,
                    seeds=lambda r: r.get("world_model_training_seeds", 0 if r.get("method") == "bc_k2" else 3), scope="independent_confirmation", note=WM_NOTE)
    csv_table("T01_wm_confirmation_summary", "世界模型独立确认主表", CONF + "summary.csv", **confmeta)
    csv_table("T02_wm_confirmation_paired", "世界模型独立确认配对差值", CONF + "paired_comparisons.csv", **{**confmeta,"seeds":3})
    csv_table("T03_wm_confirmation_per_seed", "世界模型独立确认逐种子结果与截断步数", CONF + "per_seed.csv", **{**confmeta,"seeds":lambda r:0 if r['method']=='bc_k2' else 1})
    csv_table("T04_wm_confirmation_paired_per_seed", "世界模型独立确认逐种子不一致起点", CONF + "paired_per_seed.csv", **{**confmeta,"seeds":1})
    dmeta = dict(cohort="development_30_reused_starts", independent_n=30,
                 seeds=lambda r: r.get("train_seeds", 0 if str(r.get("method", "")).startswith("bc_") else 3), scope="development_selection", note=DEV_NOTE)
    csv_table("T05_development_all_ablation", "全部开发集方法与公平消融", DEV + "summary.csv", **dmeta)
    csv_table("T06_development_paired", "开发集全部配对比较", DEV + "paired_comparisons.csv", **{**dmeta,"seeds":3})
    csv_table("T07_development_per_seed", "开发集逐种子结果与控制代价", DEV + "per_seed.csv", **{**dmeta,"seeds":lambda r:0 if str(r.get('method','')).startswith('bc_') else 1})
    csv_table("T08_training_budget_model_metadata", "模型参数、训练预算和选择 checkpoint", DEV + "model_metadata.csv", cohort="branch_training_and_selection", independent_n="train_parent20_dev_parent8", seeds=1, scope="training_metadata", note="参数/预算表不是策略成功率。base 与额外 head 阶段分别列出；有效可训练参数不一定等于总参数。Full/Plain/Direct/Prediction-only 及校准/控制臂请勿混称一个模型。")
    statrows = [{"split": split, **row, "independent_N": 20 if split == "train" else 8} for split, row in dev["data_statistics"].items()]
    table("T09_branch_dataset_statistics", "分支训练开发数据与有效排序对", statrows, [DEV + "analysis.json"], cohort="fixed_branch_dataset", independent_n=lambda r:r['independent_N'], seeds=0, scope="dataset_description", note="160/64 是候选分支组数，同一父回合可贡献多个相关组；独立父回合仅 train=20、dev=8。非平凡排序对按真值分差阈值筛选。")
    csv_table("T10_head_calibration_offline", "评分头校准离线指标", DEV + "head_calibration_offline.csv", cohort="branch_dev_8_parents_64_groups", independent_n=8, seeds=1, scope="development_mechanism_diagnosis", note="评分头校准/继续训练控制臂在已用于选择的开发标签上评估，不构成新测试集效果。MAE/Brier/regret 的单位和输入对象不同。")
    csv_table("T11_development_controller_usage", "开发集候选覆盖与回退比例", DEV + "controller_usage.csv", **dmeta)

    extrows = jload(EXT + "analysis/summary.json")
    for row in extrows:
        rate = 100 * sum(row["success_counts"]) / (len(row["success_counts"]) * row["episodes_per_policy"])
        check(f"Extensions counts {row['variant']} {row['noise']}", is_close(rate, row['mean_success_percent']), "All success counts agree with reported rate")
    table("T12_supplementary_H_K_persistence_oracle", "H、K、持续性和真值候选排序补充诊断", extrows, [EXT + "analysis/summary.json"], cohort="development_30_reused_starts", independent_n=30, seeds=lambda r:r['trained_seeds'], scope="development_supplementary_diagnosis", note=EXT_NOTE)
    extseeds={r['variant']:r['trained_seeds'] for r in extrows}
    csv_table("T13_supplementary_paired", "补充诊断配对差值", EXT + "analysis/paired_comparisons.csv", cohort="development_30_reused_starts", independent_n=30, seeds=lambda r:max(extseeds[r['left']],extseeds[r['right']]), scope="development_supplementary_diagnosis", note=EXT_NOTE)
    off = jload(EXT + "offline_metrics.json")
    offmeta = dict(cohort="branch_dev_8_parents_64_groups", independent_n=off['independent_parents'], seeds=1, scope="development_offline_diagnosis", note="现有分支开发集已用于 checkpoint 选择；64 个相关分支组来自 8 个父回合。归一化状态 MSE、位置 RMSE、评分 regret 分别反映不同性质；不可把它们混画成同单位损失。")
    prediction = [{k:v for k,v in row.items() if not isinstance(v,(dict,list))} for row in off['rows']]
    table("T14_offline_prediction_metrics", "离线预测：Full、Plain 与持续性", prediction, [EXT + "offline_metrics.json"], **offmeta)
    horizons = [{"method":r['method'],"seed":r['seed'],"horizon_step":i,"normalized_state_mse":v} for r in off['rows'] for i,v in enumerate(r['normalized_mse_per_horizon'],1)]
    table("T15_prediction_error_by_horizon", "逐预测时域状态误差", horizons, [EXT + "offline_metrics.json"], **offmeta)
    scorer = [{"method":r['method'],"seed":r['seed'],"scorer_input":kind,**r[kind]} for r in off['rows'] for kind in ('forecast_score','same_head_on_true_states')]
    table("T16_offline_scoring_and_ranking", "预测状态评分与真值状态评分", scorer, [EXT + "offline_metrics.json"], **offmeta)
    table("T17_oracle_offline_reference", "真值候选评分离线参考", [off['oracle']], [EXT + "offline_metrics.json"], **{**offmeta,"seeds":0,"note":offmeta['note'] + " oracle 的 raw regret 为候选内参考零；门控仍可能回退而带来非零 gated regret。"})

    for stage, startid, prefix in [('confirmation',60,'T18'),('dev_a',30,'T23')]:
        rel=V5 + f"analysis_{stage}/summary.json"
        summary=jload(rel)
        erel=V5 + f"analysis_{stage}/episodes.csv"
        episodes=cload(erel)
        check(f"v5 {stage} unique starts", len({e['demo'] for e in episodes}) == summary['unique_starts'], "Episode CSV unique parents match declared N")
        for version,total in summary['totals'].items():
            records=[e for e in episodes if e['version']==version]
            check(f"v5 {stage} {version} totals", len(records)==total['episodes'] and sum(success(e['success']) for e in records)==total['successes'], "Counts checked against existing episode CSV")
        cohort=f"recovery_v5_{stage}_{startid}_starts"
        scope='independent_confirmation' if stage=='confirmation' else 'development_selection'
        note=V5_NOTE if stage=='confirmation' else "v5 开发比较：30 个复用起点。表含 5 版本共 1,200 条已存在记录，其中 v2/v4 共 480 条为沿用；本阶段只新执行 T/S/v5 720 回合。不是 1,200 个独立样本。区间按起点重采样，3 个固定 Full 种子在起点内平均。"
        mainrows=[]
        for version in summary['totals']:
            for method in ('bc_k2','full'):
                for noise in (0.,.05):
                    jobs=[r for r in summary['jobs'] if r['version']==version and r['method']==method and float(r['noise'])==noise]
                    n=sum(r['episodes'] for r in jobs); s=sum(r['successes'] for r in jobs)
                    key=version + ('_bc' if method=='bc_k2' else '_full')
                    cond='clean' if noise==0 else 'noise005'
                    stat=summary['statistics'][cond][key]
                    check(f"v5 {stage} arm rate {version}/{method}/{cond}", is_close(s/n,stat['estimate']), "Raw job counts agree with statistical estimate")
                    mainrows.append({'version':version,'method':method,'noise':noise,'successes':s,'execution_count':n,'success_percent':100*s/n,'ci95_low_percent':100*stat['ci95'][0],'ci95_high_percent':100*stat['ci95'][1],'seed_count':0 if method=='bc_k2' else len(jobs),'ci_method':FIXED})
        tmeta=dict(cohort=cohort,independent_n=startid,seeds=lambda r:r.get('seed_count',3),scope=scope,note=note)
        table(prefix + '_recovery_main',f"v5 {stage} 分条件主表",mainrows,[rel],**tmeta)
        totals=[{'version':v,**r,'success_percent':100*r['successes']/r['episodes'],'distinct_rescued_N_vs_v2':len(r['distinct_rescued_starts_vs_v2']),'distinct_rescued_N_vs_v4':len(r['distinct_rescued_starts_vs_v4'])} for v,r in summary['totals'].items()]
        num='T20' if stage=='confirmation' else 'T24'
        table(num + '_recovery_execution_mix_totals',f"v5 {stage} 执行混合总表及净救回",totals,[rel],**{**tmeta,'seeds':3})
        stats=[{'condition':condition,'estimand':key,'estimate_percent_or_pp':100*r['estimate'],'ci95_low_percent_or_pp':100*r['ci95'][0],'ci95_high_percent_or_pp':100*r['ci95'][1],'unit':'percentage_points' if 'minus' in key or 'interaction' in key else 'percent','ci_method':FIXED} for condition,items in summary['statistics'].items() for key,r in items.items()]
        num='T21' if stage=='confirmation' else 'T25'
        table(num + '_recovery_statistical_comparisons',f"v5 {stage} 全部估计量及既有区间",stats,[rel],**{**tmeta,'seeds':lambda r:0 if ((('_bc' in r['estimand'] or r['estimand'].startswith('bc_')) and '_full' not in r['estimand']) or r['estimand'].startswith('bc_interaction')) else 3})
        if stage=='confirmation':
            table('T19_recovery_confirmation_jobs','v5 确认逐种子、条件与介入情况',summary['jobs'],[rel],**{**tmeta,'seeds':lambda r:0 if r['method']=='bc_k2' else 1})
            csv_table('T22_recovery_confirmation_paired','v5 确认逐种子配对救回与退步',V5+'analysis_confirmation/comparisons.csv',**{**tmeta,'seeds':lambda r:0 if r['method']=='bc_k2' else 1})

    geo=jload(V5+'analysis_geometry_confirmation/summary.json')
    grow=[{'version':version,'geometry_stratum':group,**r,'success_percent':100*r['successes']/r['episodes'],'independent_N':r['episodes']} for version,groups in geo['totals'].items() for group,r in groups.items()]
    geonote="手工指定几何压力测试：16 个起点，4 类各 4 个，5 版本共 80 次执行；第 80 步强制恢复，stationary-open 提案。分层描述性数据，无独立泛化显著性结论，不能并入自然策略确认集。"
    table('T26_geometry_stress_strata','几何压力分层与总表',grow,[V5+'analysis_geometry_confirmation/summary.json'],cohort='geometry_stress_16_manual_starts',independent_n=lambda r:r['independent_N'],seeds=0,scope='descriptive_geometry_stress',note=geonote)
    table('T27_geometry_stress_paired','几何压力配对变化',geo['comparisons'],[V5+'analysis_geometry_confirmation/summary.json'],cohort='geometry_stress_16_manual_starts',independent_n=16,seeds=0,scope='descriptive_geometry_stress',note=geonote)
    for version,groups in geo['totals'].items():
        records=[r for r in geo['episodes'] if r['version']==version]
        check(f"Geometry total {version}",len(records)==groups['all']['episodes'] and sum(r['success'] for r in records)==groups['all']['successes'],"Summary matches preserved per-episode records")

    frel='reproduction/consolidation_20261012_01/factorial_analysis.json'
    factorial=jload(frel)
    cells=[]; effects=[]
    for study in factorial:
        cohort=study['source'] + ':enabled=' + study['enabled_version']
        cells += [{'factorial_cohort':cohort,'enabled_version':study['enabled_version'],**r,'independent_N':study['unique_starts'],'seed_count':3 if r['method'].startswith('Full') else 0,'success_percent':100*r['rate'],'source_repo_path':frel+';'+study['source']} for r in study['cells']]
        effects += [{'factorial_cohort':cohort,'enabled_version':study['enabled_version'],'condition':condition,'estimand':key,'difference_pp':100*r['estimate'],'ci95_low_pp':100*r['ci95'][0],'ci95_high_pp':100*r['ci95'][1],'independent_N':study['unique_starts'],'source_repo_path':frel+';'+study['source']} for condition,items in study['effects'].items() for key,r in items.items()]
    fnote="对以前已观察的 v2/v3 确认结果进行事后 2×2 整理：相同起点内比较 WM 开关与恢复开关。三个小表中两个共享 v3 的同一批起点；不能相加当作 180 个独立起点，也不能与最新 v5 批次直接相减。既有 20,000 次配对起点 bootstrap，固定三种子平均、逐点区间。"
    table('T28_recovery_WM_factorial_cells','世界模型×共享恢复的既有同批 2×2 单元',cells,[frel],cohort='separate_historical_factorial_cohorts',independent_n=lambda r:r['independent_N'],seeds=lambda r:r['seed_count'],scope='posthoc_existing_results',note=fnote)
    table('T29_recovery_WM_factorial_effects','世界模型×恢复的主效应与交互',effects,[frel],cohort='separate_historical_factorial_cohorts',independent_n=lambda r:r['independent_N'],seeds=3,scope='posthoc_existing_results',note=fnote)

    diag=jload(DEEP+'diagnostics.json')
    for row in diag['paired_step_counts']:
        baseline={e['demo']:e for e in ce if e['method']=='bc_k2' and e['condition']==row['condition']}
        candidate={e['demo']:e for e in ce if e['method']=='full' and int(e['seed'])==row['seed'] and e['condition']==row['condition']}
        differences=[int(candidate[key]['steps'])-int(baseline[key]['steps']) for key in baseline if success(baseline[key]['success']) and success(candidate[key]['success'])]
        check(f"Common-success paired steps {row['seed']} {row['condition']}",len(differences)==row['paired_n'] and sum(d<0 for d in differences)==row['full_faster'] and sum(d==0 for d in differences)==row['equal_steps'] and sum(d>0 for d in differences)==row['full_slower'] and is_close(statistics.mean(differences),row['mean_difference']) and is_close(statistics.median(differences),row['median_difference']),'All signs, denominator and mean/median independently recomputed from preserved episodes')
    training=cload(DEEP+'checkpoint_metrics.csv')
    tnote="现有 36 个 checkpoint 的离线全量复算：3 种子×12 保存 step×train/dev=72 行；原深核查在 10 月14日已完成，此次只整理其 CSV/JSON，没有重新推理。横轴是 optimizer update step，非 epoch。train=160组/20父回合，dev=64组/8父回合；同一父回合、相邻 checkpoint 高度相关。"
    tmeta=dict(cohort='fixed_branch_train_dev_checkpoint_diagnostic',independent_n=lambda r:int(r.get('parents',8)),seeds=1,scope='existing_checkpoint_offline_diagnosis',note=tnote)
    table('T30_training_full_checkpoint_metrics','全量训练开发 checkpoint 曲线数据',training,[DEEP+'checkpoint_metrics.csv'],**tmeta)
    bykey={(int(r['seed']),int(r['step']),r['split']):r for r in training}
    gaps=[];endpoints=[]
    for seed,step in sorted({(int(r['seed']),int(r['step'])) for r in training}):
        tr=bykey[(seed,step,'train')]; dv=bykey[(seed,step,'dev')]
        gaps.append({'seed':seed,'step':step,'train_prediction_mse':float(tr['prediction_mse']),'dev_prediction_mse':float(dv['prediction_mse']),'prediction_mse_dev_minus_train':float(dv['prediction_mse'])-float(tr['prediction_mse']),'train_mean_regret':float(tr['mean_regret']),'dev_mean_regret':float(dv['mean_regret']),'train_object_error_mm':float(tr['object_error_mm']),'dev_object_error_mm':float(dv['object_error_mm']),'train_independent_parents':int(tr['parents']),'dev_independent_parents':int(dv['parents'])})
    table('T31_training_generalization_gap','逐种子逐 step 泛化差距',gaps,[DEEP+'checkpoint_metrics.csv'],**{**tmeta,'independent_n':8})
    for seed,split in sorted({(int(r['seed']),r['split']) for r in training}):
        seq=sorted([r for r in training if int(r['seed'])==seed and r['split']==split],key=lambda r:int(r['step']))
        first,last=seq[0],seq[-1]
        endpoints.append({'seed':seed,'split':split,'first_saved_step':int(first['step']),'last_saved_step':int(last['step']),'parents':int(first['parents']),'first_prediction_mse':float(first['prediction_mse']),'last_prediction_mse':float(last['prediction_mse']),'first_object_error_mm':float(first['object_error_mm']),'last_object_error_mm':float(last['object_error_mm']),'first_mean_regret':float(first['mean_regret']),'last_mean_regret':float(last['mean_regret'])})
    table('T32_training_endpoints','训练曲线首末保存点摘要',endpoints,[DEEP+'checkpoint_metrics.csv'],**tmeta)
    table('T33_common_success_paired_steps','共同成功起点的步数差',diag['paired_step_counts'],[DEEP+'diagnostics.json'],cohort='wm_confirmation_60_new_starts_common_success_subset',independent_n=lambda r:r['paired_n'],seeds=1,scope='conditional_paired_efficiency',note="仅纳入 BC 与对应 Full 种子都成功的起点。差值为 Full步骤−BC步骤：负数更快、正数更慢。每种子/条件实际配对 N 见 paired_n；这是条件效率，不能取代全体成功率或失败按400封顶的平均步数。")
    table('T34_seed_duplicate_success_diagnostic','同成功数、同起点和不同步数检查',diag['duplicate_checks'],[DEEP+'diagnostics.json'],cohort='wm_confirmation_60_new_starts',independent_n=60,seeds=3,scope='result_integrity_diagnosis',note="成功数相同并不证明输出复制；identical_success_sets 指二值成功起点集合相同，identical_step_vectors 是全步数向量是否相同。噪声下成功集合可不同。")
    table('T35_wm_confirmation_episode_records','WM 独立确认全部逐回合记录',ce,[CONF+'episodes.csv'],**{**confmeta,'seeds':lambda r:0 if r['method']=='bc_k2' else 1})

    failure_rel=V5+'posthoc_failure_review.json';failure=jload(failure_rel)
    failure_ids=failure['v5_failure_distinct_starts']
    failure_n=len(failure_ids) if isinstance(failure_ids,list) else failure_ids
    cats=[{'failure_category':k,'failure_execution_count':v,'total_failure_executions':failure['v5_failure_executions'],'total_failure_distinct_starts':failure_n,'failure_start_ids':failure_ids} for k,v in failure['v5_failure_categories'].items()]
    check('v5 failures execution and start counts',len(failure['v5_failures'])==failure['v5_failure_executions'] and len({r['demo'] for r in failure['v5_failures']})==failure_n,'Failure category/record denominators agree')
    failmeta=dict(cohort='recovery_v5_confirmation_failed_subset',independent_n=failure_n,seeds=3,scope='posthoc_observation_based_failure_review',note="现有观测日志的事后失败分类，不是碰撞因果或物理真值标签。v5 尚有失败执行和共同失败起点；不能写成恢复问题完全解决。")
    table('T36_v5_failure_categories','v5 剩余失败类别',cats,[failure_rel],**failmeta)
    records=[{k:v for k,v in r.items() if k not in ('events','phases','side_plans')} for r in failure['v5_failures']]
    table('T37_v5_failed_executions','v5 剩余失败逐回合索引',records,[failure_rel],**{**failmeta,'seeds':lambda r:0 if r['method']=='bc_k2' else 1})
    mechanisms_rel=V5+'mechanisms_confirmation.json';mechanisms=jload(mechanisms_rel)
    table('T38_v5_confirmation_mechanisms','v5 确认恢复机制事件覆盖', [{'version':v,**r} for v,r in mechanisms['summary'].items()], [mechanisms_rel],cohort='recovery_v5_confirmation_60_starts',independent_n=60,seeds=3,scope='posthoc_event_coverage',note="事件覆盖数按执行回合计，不是独立起点数。侧倒可行方案自然触发很稀少；不能把压力测试改善直接解释成自然分布上稳定的侧倒收益。")
    csv_table('T39_development_vs_confirmation_descriptive','开发与独立确认的描述性分布变化',CONF+'dev_vs_confirmation.csv',cohort='two_distinct_cohorts_not_paired',independent_n='dev30;confirmation60',seeds=lambda r:0 if r['method']=='bc_k2' else 3,scope='descriptive_cross_cohort_only',note="原表 descriptive_change_pp 是不同起点分布间的描述性差值，不是同批配对提升，也不是训练改进效果。论文中应分别列开发结果和确认结果。")
    worst=[]
    for row in diag['dev_group_details']:
        values=row['regret'];idx=max(range(len(values)),key=values.__getitem__)
        total=sum(values)
        worst.append({'seed':row['seed'],'step':row['step'],'groups':len(values),'worst_group_index':idx,'worst_regret':values[idx],'worst_share_of_total_regret':values[idx]/total if total else 0,'mean_regret':statistics.mean(values)})
    table('T40_development_regret_concentration','开发 regret 跳变集中度',worst,[DEEP+'diagnostics.json'],cohort='branch_dev_8_parents_64_groups',independent_n=8,seeds=1,scope='posthoc_curve_diagnosis',note="每 step 在 64 组中找 regret 最大组，给出其对总 regret 的占比。组索引是该诊断中的零基数组位置，不是新回合；多个相关组会使评分均值不稳定。")
    validation=[{'check':r['check'],'passed':r['passed'],'detail':r['detail']} for r in CHECKS]
    write_csv(OUT/'VALIDATION_CHECKS.csv',validation)
    write_csv(OUT/'PROVENANCE.csv',PROVENANCE)
    catalog={'tables':TABLES,'source_count':len({r['source_repo_path'] for r in PROVENANCE}),'checks':CHECKS,
             'scope':'Existing JSON/CSV only; no simulation, training, checkpoint inference, new bootstrap, or old script execution.',
             'source_priority':['../04_snapshot','original_checkout_fallback'],'new_experiments':0}
    (OUT/'table_catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    lines=['# 论文数据表目录与使用口径','',
           '全部数值从已存在的 JSON/CSV 导出，原始小数保留在 UTF-8 BOM CSV 中，便于 Excel/Word/脚本读取。此次只计算计数、单位转换、已有指标首末差等描述性整理；没有训练、仿真、checkpoint 推理或新增 bootstrap。','',
           '## 使用次序','',
           '正文主要结果优先 T01/T02（WM 独立确认）和 T18/T20/T21（共享恢复独立确认）；T05/T06 用于消融，T12–T17 用于机制诊断；T26–T29 与 T30–T40 用于局限性或附录。不同 cohort 不可直接计算因果提升。','',
           '## 必须保留的限制','',
           '- 60 个起点在多个种子和两个噪声条件下重复使用，不能把 180/360/480 次执行写成独立样本数。',
           '- WM 主确认的 Full 相对 BC 改善较小；Full 相对 Plain 的区间包含 0，排序模块的独立增益未得到清晰确认。',
           '- v5 原生确认中，同样有恢复的 BC 成功率高于 Full；不能用恢复总收益证明世界模型优于全部强基线。',
           '- v5 相对 v4 净救回只集中在少数起点；pointwise CI 不含多重比较校正、不能证明普适等效。',
           '- 满成功、零不一致或固定种子可能导致 bootstrap 区间退化为零宽；不能声称不存在不确定性。',
           '- 训练曲线复算显示 train/dev 差距，反复使用的 8 个分支开发父回合不足以证明广泛泛化。',
           '- 并行执行时记录的 decision_ms 受机器/负载影响，保留供追溯，不能作为严格延迟性能基准。','',
           f'本目录共 {len(TABLES)} 张数据表，引用 {catalog["source_count"]} 个源文件，自动检查 {len(CHECKS)} 项。逐表 SHA 见 PROVENANCE.csv。','']
    for item in TABLES:
        lines += [f'## {item["table"]} — {item["title"]}','',f'- 行数：{item["rows"]}；cohort：`{item["cohort"]}`；独立 N：{item["independent_N"]}；种子数：{item["seed_count"]}。',f'- 证据性质：`{item["scope"]}`。',f'- 用法与限制：{item["note"]}', '- 源文件：'+ '；'.join('`'+s+'`' for s in item['sources'])+'。','']
    (OUT/'TABLE_CATALOG.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    dictionary='''# 数据字典与统计口径

本字典适用于 T01–T40，未重命名的字段沿用各来源分析文件。所有 CSV 使用 UTF-8 BOM；空值表示未计算/不适用，不等于 0。数组、字典字段在 CSV 中保存 JSON 字符串。

| 字段/字段族 | 单位与定义 | 使用限制 |
| --- | --- | --- |
| dataset / cohort | 固定数据批次或证据集合标识 | 同名批次可配对；不同批次不得相减写成效果 |
| independent_N / independent_initial_states / distinct_parents / parents | 独立起点或分支父回合数 | 分支父回合≠分支组数；重复条件/种子不扩大 N |
| seed_count / train_seeds / world_model_training_seeds | 世界模型训练种子数；固定 BC 写 0；逐种子行通常写 1 | 0 并非没有策略或没有重复执行 |
| seed / seed_order | 17、23、41 等已冻结训练随机种子 | 不含任意重训分布的完整不确定性 |
| condition / noise | clean=0；noise005=0.05；joint_equal_weight=两条件等权 | 两条件复用起点，非新增独立实验 |
| source_repo_path / source | 原项目相对路径，可在 ../04_snapshot 镜像找到 | PROVENANCE.csv 记录源 SHA-256 |
| evidence_scope | independent_confirmation / development_selection / diagnosis / stress / posthoc 等 | 不可把开发或事后分析描述为预注册独立确认 |
| successes / success / success_counts / success_s17... | 成功执行计数或逐回合布尔值 | 三种子总成功数的分母通常为 3N，独立 N 仍为 N |
| execution_count / episodes / episodes_per_seed | 已有执行记录条数 | 同一起点可能有多个高度相关执行 |
| mean_success_percent / success_percent / rate | 百分比；rate 原字段通常为 0–1 | 看列名区分百分比与比例 |
| seed_sd_pp / seed_sample_sd_pp | 三个种子成功率的样本标准差，百分点 | 成功数相同可为 0，并非总体不确定性为 0 |
| ...difference_pp / ...delta... / ...minus... | 同批配对成功率差，百分点；left−right | 跨 cohort descriptive_change_pp 仅描述分布变化 |
| ...ci...low/high... / ci95_pp | 沿用来源的 95% bootstrap 区间 | WM 表为 starts×seeds 交叉重采样；v5 为起点重采样、固定三种子均值；均为逐点区间 |
| overall_execution_mix | v5 每起点 8 执行的等权混合 | BC 2/8、Full 6/8；不是两种方法各 1/2 |
| joint_equal_weight | WM 主确认 clean/noise 条件等权平均 | 不等同 v5 execution mix |
| wins / losses / rescues / regressions | 配对不一致执行数 | 同一起点可贡献多个条件/种子，另看 distinct/rescued IDs |
| mean_steps_failures_capped_400 / mean_steps_capped | 所有起点平均步数，失败以 400 封顶 | 同时受成功率与效率影响 |
| paired_n / mean_difference / median_difference | 双方均成功子集的 N、Full步数−BC步数 | 负值表示 Full 更快，只对该条件子集有效 |
| override_fraction / fraction_override | 门控所选动作不同于回退 k=2 的决策比例 | 不是成功率，也不等于模型预测准确率 |
| parallel...decision_ms / mean_decision_ms... | 旧运行记录的平均毫秒 | 并行负载，不能当严格推理延迟基准 |
| groups / branch_steps / nontrivial_pairs | 候选分支组、分支时刻、真值分差>.025的候选对 | 同父回合相关；有效排序对远少于全部可能对 |
| normalized_state_mse / prediction_mse | 按既有训练标准化的状态均方误差 | 无量纲，不是米；低于持久性不等于控制收益必然提升 |
| eef_position_rmse_m / object_position_rmse_m | 末端/物体位置误差，米 | 与 object_error_mm 的指标定义不同 |
| object_error_mm | 全量 checkpoint 诊断中的平均物体欧氏位置误差，毫米 | 不要与 m 单位 RMSE 混用；须看原诊断脚本定义 |
| normalized_mse_per_horizon / horizon_step | 每预测步的标准化状态 MSE | x 轴是预测步数而非训练 step |
| step / base_selected_step / head_selected_step | 优化更新次数 | 不是 epoch；不同阶段 step 不应直接拼接 |
| progress_bce / risk_bce / ranking_loss / total_loss | 各训练目标损失；total 含既有权重 | 各损失尺度不同，不应靠形状判断所有模块共同改善 |
| raw_regret / mean_regret | 候选真实最好分数减模型选中候选的真实分数 | 对固定候选集成立；非全局任务 regret |
| gated_regret | 经过风险/优势门控及 k=2 回退后的候选 regret | 即使 oracle raw=0，门控后也可非零 |
| pair_accuracy_ties_half | 非平凡候选对排序准确率，预测并列计半对 | 必须一起报告有效对数与 pair_tie_rate |
| risk / grasp-loss | 已有训练标注定义的失抓风险目标 | 不等于所有碰撞/失败原因的概率 |
| effective_trainable_parameters_this_phase | 该训练阶段实际可更新的参数数 | 不等于模型总参数、也不能跨阶段简单加总 |
| worst_share_of_total_regret | 最大 regret 组占全部 regret 之和比例 | 单组主导提示指标脆弱性，不代表数据造假 |
| observation_based_category | 依据旧轨迹观测的事后失败分类 | 不作为物理碰撞真值或严格因果诊断 |

原始 CSV 一致性复核：VALIDATION_CHECKS.csv。源/产物 SHA：PROVENANCE.csv。可迁移机器目录：table_catalog.json。脚本只用 Python 标准库，`python 02_tables/build_tables.py` 可从包根目录运行；优先读取 04_snapshot，若缺失才读取原 checkout，缺失两处会明确报错。
'''
    (OUT/'DATA_DICTIONARY.md').write_text(dictionary,encoding='utf-8')
    print(json.dumps({'passed':True,'tables':len(TABLES),'source_files':catalog['source_count'],'automatic_checks':len(CHECKS),'new_experiments':0,'new_checkpoint_inference':0,'outputs':str(OUT),'source_resolution_counts':dict(Counter(r['source_resolved_from'] for r in PROVENANCE))},ensure_ascii=False,indent=2))


if __name__ == '__main__':
    main()
