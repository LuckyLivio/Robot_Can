"""Read-only analysis of evaluate_delay.py diagnostic traces (schema version 1).

Writes a fresh analysis directory. Counterfactual outcomes are not inferred from
two trajectories after they have diverged. Prediction errors use only the FIFO
prefix whose actual executed actions are checked against the imagined actions.
"""
import argparse
import csv
import json
import math
import statistics
from pathlib import Path


def max_difference(a, b):
    if len(a) != len(b):
        raise ValueError("Cannot compare vectors with different lengths")
    return max((abs(float(x) - float(y)) for x, y in zip(a, b)), default=0.0)


def distance(a, b):
    return math.sqrt(sum((float(x) - float(y)) ** 2 for x, y in zip(a, b)))


def describe(values):
    values = sorted(float(v) for v in values)
    if not values:
        return {"n": 0, "mean": None, "median": None, "p95": None, "max": None}
    return {"n": len(values), "mean": statistics.mean(values),
            "median": statistics.median(values),
            "p95": values[max(0, math.ceil(len(values) * .95) - 1)],
            "max": values[-1]}


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def finite_numbers(value):
    if isinstance(value, dict):
        return all(finite_numbers(v) for v in value.values())
    if isinstance(value, list):
        return all(finite_numbers(v) for v in value)
    return not isinstance(value, float) or math.isfinite(value)


def read_runs(input_dir):
    runs = []
    # Nested validation / ablation folders are separate runs, not extra inputs.
    for path in sorted(input_dir.glob("*.json")):
        document = read_json(path)
        if not isinstance(document, dict) or document.get("trace_schema_version") != 1:
            continue
        if not document.get("trace_files"):
            continue
        if document.get("status") != "complete":
            raise ValueError(f"Incomplete diagnostic result: {path}")
        records = document.get("records", [])
        if not records:
            raise ValueError(f"No episode records: {path}")
        if len({r["demo"] for r in records}) != len(records):
            raise ValueError(f"Duplicate episode names: {path}")
        expected_rate = sum(bool(r["success"]) for r in records) / len(records)
        if abs(float(document["success_rate"]) - expected_rate) > 1e-8:
            raise ValueError(f"Success-rate mismatch: {path}")
        episodes = {}
        for result in records:
            name = result["demo"]
            if name not in document["trace_files"]:
                raise ValueError(f"Missing trace mapping for {name}: {path}")
            trace_path = (path.parent / document["trace_files"][name]).resolve()
            if not trace_path.is_relative_to(input_dir):
                raise ValueError(f"Trace escapes input directory: {trace_path}")
            rows = [json.loads(line) for line in trace_path.read_text(encoding="utf-8").splitlines() if line.strip()]
            if len(rows) != int(result["steps"]):
                raise ValueError(f"Trace length does not match result: {trace_path}")
            for index, row in enumerate(rows):
                if row["demo"] != name or row["step"] != index + 1:
                    raise ValueError(f"Non-contiguous steps or wrong demo: {trace_path}")
                if not finite_numbers(row):
                    raise ValueError(f"Non-finite trace value: {trace_path}, step {index + 1}")
                if len(row["state_before"]) != 23 or len(row["state_after"]) != 23:
                    raise ValueError(f"Expected 23-dimensional observation: {trace_path}")
                if index and max_difference(rows[index - 1]["state_after"], row["state_before"]) > 1e-6:
                    raise ValueError(f"Discontinuous observations: {trace_path}, step {index + 1}")
                if row["success_after"] and index != len(rows) - 1:
                    raise ValueError(f"Trace continued after success: {trace_path}")
                pending = row["queue_before"]
                expected_action = pending[0] if pending else row["submitted_action"]
                if max_difference(expected_action, row["executed_action_before_noise"]) > 1e-7:
                    raise ValueError(f"FIFO execution mismatch: {trace_path}, step {index + 1}")
                if document["args"].get("noise", 0) == 0:
                    clipped = [min(1.0, max(-1.0, v)) for v in expected_action]
                    if max_difference(clipped, row["executed_action"]) > 1e-7:
                        raise ValueError(f"Clipped execution mismatch: {trace_path}, step {index + 1}")
                if row.get("costs") is not None:
                    costs = row["costs"]
                    raw, selected, fallback = row["raw_selected"], row["selected"], row["fallback_index"]
                    raw_advantage = costs[fallback] - costs[raw]
                    if raw != min(range(len(costs)), key=costs.__getitem__):
                        raise ValueError(f"Raw choice disagrees with costs: {trace_path}, step {index + 1}")
                    # The evaluator subtracts float32 costs. Use its recorded
                    # advantage at threshold boundaries after checking it below.
                    expected_selected = fallback if raw != fallback and row["raw_advantage"] < document["args"].get("gate_margin", 0) else raw
                    if selected != expected_selected or row["overrode_fallback"] != (selected != fallback):
                        raise ValueError(f"Gate choice mismatch: {trace_path}, step {index + 1}")
                    if row["gate_blocked"] != (raw != fallback and selected == fallback):
                        raise ValueError(f"Gate blocked flag mismatch: {trace_path}, step {index + 1}")
                    if abs(row["raw_advantage"] - raw_advantage) > 2e-6 or abs(row["selected_advantage"] - (costs[fallback] - costs[selected])) > 2e-6:
                        raise ValueError(f"Recorded advantage mismatch: {trace_path}, step {index + 1}")
            if not rows or bool(rows[-1]["success_after"]) != bool(result["success"]):
                raise ValueError(f"Final success flag does not match result: {trace_path}")
            episodes[name] = {"result": result, "rows": rows, "trace": str(trace_path)}
        runs.append({"id": str(path.relative_to(input_dir)), "path": str(path),
                     "args": document["args"], "provenance": document.get("provenance"),
                     "episodes": episodes})
    if not runs:
        raise ValueError(f"No complete schema-version-1 diagnostic results in {input_dir}")
    return runs


def score_parts(row, candidate, risk_weight):
    if row.get("predicted_progress") is None:
        return None
    progress = row["predicted_progress"][candidate]
    risk = row["predicted_risk"][candidate]
    benefit = progress[-1] + .5 * statistics.mean(progress)
    penalty = risk_weight * max(risk)
    return {"progress_component": benefit, "risk_penalty": penalty,
            "learned_score": benefit - penalty, "terminal_progress": progress[-1],
            "max_risk": max(risk)}


def summarize_steps(run, name, episode):
    args = run["args"]
    risk_weight = args.get("risk_weight", .5)
    summaries = []
    score_residuals = []
    for row in episode["rows"]:
        flat_queue = [v for action in row["queue_before"] for v in action]
        selected = row["selected"]
        fallback = row.get("fallback_index")
        selected_parts = score_parts(row, selected, risk_weight)
        fallback_parts = score_parts(row, fallback, risk_weight) if fallback is not None else None
        summary = {"run": run["id"], "method": args["method"], "demo": name,
                   "step": row["step"], "selected": selected,
                   "raw_selected": row.get("raw_selected"), "fallback_index": fallback,
                   "overrode_fallback": row.get("overrode_fallback"),
                   "gate_blocked": row.get("gate_blocked"),
                   "raw_advantage": row.get("raw_advantage"),
                   "selected_advantage": row.get("selected_advantage"),
                   "queue_nonzero": any(abs(v) > 1e-8 for v in flat_queue),
                   "queue_max_abs": max((abs(v) for v in flat_queue), default=0),
                   "queue_translation_max_norm": max((distance(a[:3], [0, 0, 0]) for a in row["queue_before"]), default=0),
                   "grasp_before": row["stages_before"][1] > .3,
                   "grasp_after": row["stages_after"][1] > .3,
                   "progress_after": 1.0 if row["success_after"] else max(row["stages_after"]),
                   "success_after": row["success_after"],
                   "object_x_after": row["state_after"][16],
                   "object_y_after": row["state_after"][17],
                   "object_z_after": row["state_after"][18],
                   "eef_object_distance_m": distance(row["state_after"][:3], row["state_after"][16:19]),
                   "object_target_distance_m": distance(row["state_after"][16:19], row["target_position"]),
                   "progress_component_delta": None, "risk_penalty_delta": None,
                   "learned_score_delta": None}
        if selected_parts is not None and fallback_parts is not None:
            summary["progress_component_delta"] = selected_parts["progress_component"] - fallback_parts["progress_component"]
            summary["risk_penalty_delta"] = selected_parts["risk_penalty"] - fallback_parts["risk_penalty"]
            summary["learned_score_delta"] = selected_parts["learned_score"] - fallback_parts["learned_score"]
            for k, stored_score in enumerate(row["learned_scores"]):
                score_residuals.append(abs(score_parts(row, k, risk_weight)["learned_score"] - stored_score))
        summaries.append(summary)
    if score_residuals and max(score_residuals) > 2e-6:
        raise ValueError(f"Readout decomposition disagrees with stored scores: {run['id']} {name}")
    return summaries, max(score_residuals, default=0)


def prediction_errors(run, rows):
    delay = int(run["args"].get("delay", 0))
    if run["args"].get("noise", 0) != 0:
        return {"enabled": False, "reason": "Noise is nonzero; deterministic FIFO-prefix analysis skipped."}
    if not any(row.get("predicted_states") is not None for row in rows):
        return {"enabled": False, "reason": "No predicted physical states in this run."}
    horizons = {}
    for horizon in range(1, min(delay, int(run["args"].get("horizon", 8))) + 1):
        metrics = {"eef_position_error_mm": [], "object_position_error_mm": [],
                   "progress_absolute_error": [], "risk_absolute_error": []}
        candidates = matched = mismatched = 0
        for index, row in enumerate(rows):
            if index + horizon > len(rows) or row.get("predicted_states") is None:
                continue
            candidates += 1
            selected = row["selected"]
            actions = row["model_sequences"][selected][:horizon]
            actual_rows = rows[index:index + horizon]
            if len(actions) != horizon or any(max_difference(action, actual["executed_action"]) > 1e-7 for action, actual in zip(actions, actual_rows)):
                mismatched += 1
                continue
            matched += 1
            future = row["predicted_states"][selected][horizon - 1]
            actual_row = actual_rows[-1]
            actual = actual_row["state_after"]
            metrics["eef_position_error_mm"].append(distance(future[:3], actual[:3]) * 1000)
            metrics["object_position_error_mm"].append(distance(future[16:19], actual[16:19]) * 1000)
            progress = 1.0 if actual_row["success_after"] else max(actual_row["stages_after"])
            lost = bool(row["stages_before"][1] > .3 and actual_row["stages_after"][1] < .3 and not actual_row["success_after"])
            metrics["progress_absolute_error"].append(abs(row["predicted_progress"][selected][horizon - 1] - progress))
            metrics["risk_absolute_error"].append(abs(row["predicted_risk"][selected][horizon - 1] - float(lost)))
        horizons[str(horizon)] = {"candidate_windows": candidates, "matched_windows": matched,
                                  "excluded_action_mismatch": mismatched,
                                  **{key: describe(value) for key, value in metrics.items()}}
    return {"enabled": True, "horizons": horizons,
            "interpretation": "Only identical realized FIFO-prefix actions are compared. Errors beyond the delay are not estimated."}


def risk_distinguishability(run, rows, overrides):
    """A shared FIFO risk peak cancels in pairwise candidate score differences.

    A prefix tie counts as a prefix peak: prefix_max >= overall_max. Candidate
    risk-max equality is checked separately with a 1e-10 absolute tolerance.
    This is descriptive and does not establish the cause of an episode failure.
    """
    delay = int(run["args"].get("delay", 0))
    evaluated = equal_maxima = prefix_peaks = both = 0
    minimum, maximum = None, None
    risk_weight = run["args"].get("risk_weight", .5)
    absolute_deltas = []
    for row in rows:
        risks = row.get("predicted_risk")
        if risks is None:
            continue
        evaluated += 1
        candidate_maxima = [max(risk) for risk in risks]
        flat_risks = [value for risk in risks for value in risk]
        minimum = min(flat_risks) if minimum is None else min(minimum, min(flat_risks))
        maximum = max(flat_risks) if maximum is None else max(maximum, max(flat_risks))
        equal = max(candidate_maxima) - min(candidate_maxima) <= 1e-10
        prefix = delay > 0 and all(max(risk[:delay]) >= max(risk) for risk in risks)
        equal_maxima += equal
        prefix_peaks += prefix
        both += equal and prefix
        if row.get("overrode_fallback"):
            selected_risk = candidate_maxima[row["selected"]]
            fallback_risk = candidate_maxima[row["fallback_index"]]
            absolute_deltas.append(abs(risk_weight * (selected_risk - fallback_risk)))
    if not evaluated:
        return {"available": False}
    if len(absolute_deltas) != len(overrides):
        raise ValueError("Risk contribution count does not match override count")
    return {"available": True, "evaluated_steps": evaluated,
            "risk_weight": risk_weight, "predicted_risk_min": minimum, "predicted_risk_max": maximum,
            "override_risk_penalty_absolute_delta": describe(absolute_deltas),
            "all_candidate_max_risks_equal_steps": equal_maxima,
            "all_candidate_max_risks_equal_fraction": equal_maxima / evaluated,
            "all_candidate_risk_peaks_in_fifo_prefix_steps": prefix_peaks,
            "all_candidate_risk_peaks_in_fifo_prefix_fraction": prefix_peaks / evaluated,
            "shared_fifo_peak_and_equal_candidate_maxima_steps": both,
            "shared_fifo_peak_and_equal_candidate_maxima_fraction": both / evaluated,
            "candidate_max_equality_tolerance": 1e-10,
            "prefix_peak_rule": "For every candidate, max(risk[:delay]) >= max(risk); ties count as prefix peaks.",
            "interpretation": "Risk need not be zero. Equal maxima give equal risk penalties and do not distinguish candidates at those steps. These episode-level observations do not establish a failure cause."}


def summarize_episode(run, name, episode):
    rows = episode["rows"]
    step_rows, score_residual = summarize_steps(run, name, episode)
    overrides = [row for row in step_rows if row["overrode_fallback"]]
    grasp_onsets, grasp_losses = [], []
    held_before = rows[0]["stages_before"][1] > .3
    for row in rows:
        held_after = row["stages_after"][1] > .3
        if held_after and not held_before:
            grasp_onsets.append(row["step"])
        if held_before and not held_after and not row["success_after"]:
            grasp_losses.append(row["step"])
        held_before = held_after
    selected_counts = {}
    for row in rows:
        key = str(row["selected"])
        selected_counts[key] = selected_counts.get(key, 0) + 1
    final = rows[-1]
    final_object = final["state_after"][16:19]
    result = {"run": run["id"], "method": run["args"]["method"], "demo": name,
              "success": bool(episode["result"]["success"]), "steps": len(rows),
              "selected_counts": selected_counts, "override_count": len(overrides),
              "override_fraction": len(overrides) / len(rows),
              "gate_blocked_count": sum(bool(row["gate_blocked"]) for row in step_rows),
              "first_override_step": overrides[0]["step"] if overrides else None,
              "overrides": [{key: row[key] for key in ("step", "selected", "raw_selected", "fallback_index", "raw_advantage", "selected_advantage", "progress_component_delta", "risk_penalty_delta", "learned_score_delta", "queue_max_abs", "queue_translation_max_norm", "grasp_before")} for row in overrides],
              "override_advantage": describe(row["selected_advantage"] for row in overrides),
              "override_progress_component_delta": describe(row["progress_component_delta"] for row in overrides),
              "override_risk_penalty_delta": describe(row["risk_penalty_delta"] for row in overrides),
              "queue_nonzero_steps": sum(row["queue_nonzero"] for row in step_rows),
              "queue_nonzero_fraction": sum(row["queue_nonzero"] for row in step_rows) / len(rows),
              "queue_translation_max_norm": describe(row["queue_translation_max_norm"] for row in step_rows),
              "initial_grasp_proxy": rows[0]["stages_before"][1] > .3,
              "grasp_onset_steps": grasp_onsets, "grasp_loss_steps": grasp_losses,
              "final_object_position_m": final_object,
              "final_eef_position_m": final["state_after"][:3],
              "target_position_m": final["target_position"],
              "final_object_target_distance_m": distance(final_object, final["target_position"]),
              "final_object_target_xy_distance_m": distance(final_object[:2], final["target_position"][:2]),
              "score_decomposition_max_residual": score_residual,
              "risk_distinguishability": risk_distinguishability(run, rows, overrides),
              "prefix_prediction_errors": prediction_errors(run, rows)}
    return result, step_rows


def first_difference(a_rows, b_rows, field, tolerance=1e-6):
    for a, b in zip(a_rows, b_rows):
        error = max_difference(a[field], b[field])
        if error > tolerance:
            return {"step": a["step"], "max_abs_difference": error}
    return None


def compare_runs(runs):
    comparisons = []
    for wm in (r for r in runs if r["args"]["method"] == "wm"):
        args = wm["args"]
        fallback = 0 if args.get("fallback", "base") == "base" else args.get("fallback_index")
        if fallback is None:
            fallback = args.get("delay", 2)
        for baseline in (r for r in runs if r["args"]["method"] == "bc_shift"):
            baseline_shift = baseline["args"].get("shift_index")
            if baseline_shift is None:
                baseline_shift = baseline["args"].get("delay", 2)
            keys = ("policy", "policy_checkpoint", "split", "steps", "delay", "horizon", "noise")
            if baseline_shift != fallback or any(args.get(key) != baseline["args"].get(key) for key in keys):
                continue
            for name in sorted(set(wm["episodes"]) & set(baseline["episodes"])):
                a, b = wm["episodes"][name], baseline["episodes"][name]
                initial_error = max_difference(a["rows"][0]["state_before"], b["rows"][0]["state_before"])
                if initial_error > 1e-6:
                    raise ValueError(f"Paired run initial observations differ: {name}, {initial_error}")
                comparisons.append({"demo": name, "wm_run": wm["id"], "baseline_run": baseline["id"],
                                    "fallback_index": fallback, "initial_state_max_error": initial_error,
                                    "wm_success": bool(a["result"]["success"]), "baseline_success": bool(b["result"]["success"]),
                                    "wm_steps": len(a["rows"]), "baseline_steps": len(b["rows"]),
                                    "first_submitted_action_difference": first_difference(a["rows"], b["rows"], "submitted_action"),
                                    "first_executed_action_difference": first_difference(a["rows"], b["rows"], "executed_action"),
                                    "first_state_after_difference": first_difference(a["rows"], b["rows"], "state_after"),
                                    "interpretation": "Only the shared prefix has the same observed starting state. Later step-aligned differences are descriptive, not counterfactual causal estimates."})
    return comparisons


def number(value, digits=4):
    return "无" if value is None else f"{value:.{digits}f}"


def step_of(event):
    return "未观察到" if event is None else str(event["step"])


def diagnosis_text(analysis):
    lines = ["延迟控制诊断（仅读取保存的轨迹）", "", "统计口径：step 从 1 开始；predicted_states[k][j] 是当前观察起第 j+1 个物理步后的预测；第 step 步提交的命令首次在 step+delay 步执行。所有位置误差均明确标出单位。"]
    for pair in analysis["paired_comparisons"]:
        lines.extend(["", f"配对回合 {pair['demo']}：WM {'成功' if pair['wm_success'] else '失败'}（{pair['wm_steps']} 步），k={pair['fallback_index']} {'成功' if pair['baseline_success'] else '失败'}（{pair['baseline_steps']} 步）。",
                      f"首次提交动作差异：第 {step_of(pair['first_submitted_action_difference'])} 步；首次实际执行动作差异：第 {step_of(pair['first_executed_action_difference'])} 步；首次后状态差异：第 {step_of(pair['first_state_after_difference'])} 步。"])
    for episode in analysis["episodes"]:
        lines.extend(["", f"{episode['demo']} / {episode['method']} / {episode['run']}",
                      f"选择次数：{json.dumps(episode['selected_counts'], ensure_ascii=False)}；覆盖默认策略 {episode['override_count']}/{episode['steps']} 次；门控拦截 {episode['gate_blocked_count']} 次。",
                      f"队列非零 {episode['queue_nonzero_steps']}/{episode['steps']} 步；抓取代理开始步：{episode['grasp_onset_steps']}；抓取代理丢失步：{episode['grasp_loss_steps']}。",
                      f"最终物体位置（米）：{episode['final_object_position_m']}；距目标水平距离 {episode['final_object_target_xy_distance_m'] * 1000:.2f} 毫米。"])
        if episode["overrides"]:
            first = episode["overrides"][0]
            lines.append(f"首次覆盖在第 {first['step']} 步选择 k={first['selected']}，预测成本优势 {number(first['selected_advantage'])}；进度贡献变化 {number(first['progress_component_delta'])}，风险惩罚变化 {number(first['risk_penalty_delta'])}。进度贡献减去风险惩罚等于学习分数。")
            lines.append(f"全部覆盖的平均预测优势 {number(episode['override_advantage']['mean'])}；平均进度贡献变化 {number(episode['override_progress_component_delta']['mean'])}；平均风险惩罚变化 {number(episode['override_risk_penalty_delta']['mean'])}。")
        risk = episode["risk_distinguishability"]
        if risk["available"]:
            delta = risk["override_risk_penalty_absolute_delta"]
            if delta["n"]:
                lines.append(f"覆盖时风险惩罚差的绝对值：均值 {delta['mean']:.6g}，最大值 {delta['max']:.6g}；所有候选、所有预测步的风险输出范围 [{risk['predicted_risk_min']:.6g}, {risk['predicted_risk_max']:.6g}]，风险并非恒为零。")
            lines.append(f"所有候选的风险峰值均在共同 FIFO 前缀出现，且候选最大风险相同：{risk['shared_fifo_peak_and_equal_candidate_maxima_steps']}/{risk['evaluated_steps']} 步；这些步的共同风险惩罚不区分候选。分别核对：前缀峰值条件满足 {risk['all_candidate_risk_peaks_in_fifo_prefix_steps']} 步，候选最大风险相同 {risk['all_candidate_max_risks_equal_steps']} 步。")
            lines.append("峰值统计口径：每个候选均满足 prefix_max >= overall_max（并列峰值计入）；另逐步核对所有候选最大风险的绝对差不超过 1e-10。")
        errors = episode["prefix_prediction_errors"]
        if errors["enabled"]:
            for horizon, metric in errors["horizons"].items():
                lines.append(f"向前 {horizon} 步同动作窗口 {metric['matched_windows']} 个（排除动作不一致 {metric['excluded_action_mismatch']} 个）：末端位置误差均值 {number(metric['eef_position_error_mm']['mean'], 2)} 毫米，物体位置误差均值 {number(metric['object_position_error_mm']['mean'], 2)} 毫米，进度绝对误差均值 {number(metric['progress_absolute_error']['mean'])}。")
    lines.extend(["", "解释边界：", "1. 覆盖发生后两条闭环轨迹会分叉。后续同一步的状态、成功率或评分差异不能视为同状态下的候选动作因果效果。",
                  "2. 仅在无噪声且实际执行动作逐项吻合时，比较延迟队列覆盖范围内的预测与真实后状态。不把重复同一候选动作的长预测当作闭环未来的真实轨迹。",
                  "3. 抓取使用 staged_rewards()[1] > 0.3 的代理；代理下降并不自动等于物理掉落或已定位根因。",
                  "4. 非零队列覆盖率描述部署输入。训练零队列与部署真实队列的差异是待验证机制，单靠本报告不能确认它导致失败。",
                  "5. 这里只诊断所读取的回合，不估计总体成功率，也不据此调节封存测试集上的参数。",
                  "6. 世界模型分数不是置信度；进度与风险贡献的大小不能直接解释为校准概率。",
                  "7. 本次共同风险峰值和风险贡献统计只描述所选诊断回合；风险不区分候选并不是这些回合失败根因的证明。", ""])
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, required=True,
                        help="Read result JSON files directly in this directory, non-recursively; skip results without trace files.")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    input_dir = args.input_dir.resolve()
    output_dir = args.output_dir.resolve()
    if not input_dir.is_dir():
        raise NotADirectoryError(input_dir)
    if output_dir.exists():
        raise FileExistsError(f"Refusing to overwrite analysis directory: {output_dir}")
    runs = read_runs(input_dir)
    episodes, steps = [], []
    for run in runs:
        for name, episode in run["episodes"].items():
            summary, step_rows = summarize_episode(run, name, episode)
            episodes.append(summary)
            steps.extend(step_rows)
    analysis = {"analysis_schema_version": 1, "input_dir": str(input_dir),
                "inputs": [{key: run[key] for key in ("id", "path", "args", "provenance")} for run in runs],
                "episodes": episodes, "paired_comparisons": compare_runs(runs),
                "validation": {"complete_results": len(runs), "episodes": len(episodes), "trace_steps": len(steps),
                               "step_continuity": True, "episode_results_match_traces": True,
                               "fifo_execution_checked": True, "gate_decisions_checked": True,
                               "score_decomposition_checked": True}}
    # Finish all parsing and validation before creating any output.
    encoded = json.dumps(analysis, ensure_ascii=False, indent=2, allow_nan=False)
    text = diagnosis_text(analysis)
    output_dir.mkdir(parents=True, exist_ok=False)
    (output_dir / "analysis.json").write_text(encoded, encoding="utf-8")
    with (output_dir / "step_summary.csv").open("x", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(steps[0]))
        writer.writeheader()
        writer.writerows(steps)
    (output_dir / "diagnosis.txt").write_text(text, encoding="utf-8")
    print(json.dumps({"output_dir": str(output_dir), **analysis["validation"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
