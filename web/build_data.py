"""Build the CAN LAB viewer from frozen evidence without running a policy.

Uses only the Python standard library. Original result files and traces are
read-only. The browser receives full per-control records for the selected cases;
column packing and a shared action dictionary only reduce transfer size.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
STAGE = ROOT / "reproduction/graduation_repairs_20261022_01"
CONFIRMATION = STAGE / "confirmation"
INPUTS: dict[str, dict] = {}
FRAME_KEYS = [
    "step", "eef", "object", "phase", "nextPhase", "holding", "attempts",
    "selected", "scores", "submitted", "executed", "success", "compute_ms", "queue",
]


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def register(path: Path) -> None:
    key = rel(path)
    if key in INPUTS:
        return
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
            size += len(chunk)
    INPUTS[key] = {"sha256": digest.hexdigest(), "bytes": size}


def read_json(path: Path):
    register(path)
    return json.loads(path.read_text(encoding="utf-8-sig"))


def read_csv(path: Path):
    register(path)
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def quantize(value: float, digits: int = 6) -> float:
    """Truncate only the display copy; never change the original evidence."""
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("A selected display value is not finite")
    scale = 10 ** digits
    return math.trunc(value * scale) / scale


def vector(values, digits: int = 6):
    return [quantize(value, digits) for value in values]


def percentile(ordered: list[float], percent: float) -> float:
    """Linear interpolation, equivalent to NumPy's default percentile."""
    index = (len(ordered) - 1) * percent / 100
    lo = math.floor(index)
    hi = math.ceil(index)
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (index - lo)


def build_cells(rows):
    output = []
    for policy in ("bc", "full"):
        for controller in ("none", "v5", "queue_budget"):
            for noise in (0.0, 0.05):
                selected = [row for row in rows
                            if row["study_arm"] == "recovery_factorial"
                            and row["method"] == policy
                            and row["controller"] == controller
                            and float(row["noise"]) == noise]
                assert len(selected) == (1 if policy == "bc" else 3)
                records = []
                sources = [rel(STAGE / "analysis/confirmation/cells.csv")]
                for row in selected:
                    result_path = CONFIRMATION / row["job_id"] / "result.json"
                    result = read_json(result_path)
                    assert result["status"] == "complete"
                    assert len(result["records"]) == 60
                    assert sum(record["success"] for record in result["records"]) == int(row["successes"])
                    assert sum(record["stability"]["stable"] for record in result["records"]) == int(row["stable_successes"])
                    assert sum(record["steps"] for record in result["records"]) == int(row["compute_samples"])
                    records.extend(result["records"])
                    sources.append(rel(result_path))
                successes = sum(int(row["successes"]) for row in selected)
                total = sum(int(row["executions"]) for row in selected)
                stable = sum(int(row["stable_successes"]) for row in selected)
                controls = sum(int(row["compute_samples"]) for row in selected)
                output.append({
                    "policy": policy, "controller": controller, "noise": noise,
                    "successes": successes, "total": total, "stable": stable,
                    "total_controls": controls, "source": sources,
                    "independent_starts": 60,
                    "world_model_seeds": [17, 23, 41] if policy == "full" else [],
                    "success_rate": successes / total,
                    "stable_rate": stable / total,
                    "stable_rate_among_successes": stable / successes,
                    "mean_capped_steps": controls / total,
                    "job_ids": [row["job_id"] for row in selected],
                })
    return output


def build_effects(rows):
    floats = {"before_mean", "after_mean", "effect", "ci95_low", "ci95_high"}
    integers = {"independent_starts", "bootstrap_draws", "bootstrap_seed", "net_positive_starts", "net_negative_starts"}
    output = []
    for line, row in enumerate(rows, 2):
        effect = {}
        for key, value in row.items():
            if key in floats:
                effect[key] = float(value)
            elif key in integers:
                effect[key] = int(value)
            elif key == "noise" and value != "equal_noise_joint":
                effect[key] = float(value)
            else:
                effect[key] = value
        effect["source"] = rel(STAGE / "analysis/confirmation/paired_effects.csv")
        effect["source_row"] = line
        output.append(effect)
    return output


def build_timing():
    entries = []
    for policy in ("bc", "full"):
        by_noise = {0.0: [], 0.05: []}
        sources = {0.0: [], 0.05: []}
        for path in sorted(CONFIRMATION.glob(f"v5_{policy}_*/trace.jsonl")):
            job = read_json(path.parent / "result.json")["job"]
            noise = float(job["noise"])
            register(path)
            sources[noise].append(rel(path))
            with path.open(encoding="utf-8") as handle:
                by_noise[noise].extend(float(json.loads(line)["compute_ms"]) for line in handle)
        for noise in (0.0, 0.05, "joint"):
            values = by_noise[noise] if noise != "joint" else by_noise[0.0] + by_noise[0.05]
            paths = sources[noise] if noise != "joint" else sources[0.0] + sources[0.05]
            ordered = sorted(values)
            entries.append({
                "policy": policy, "controller": "v5", "noise": noise,
                "n": len(values), "p50_ms": percentile(ordered, 50),
                "p95_ms": percentile(ordered, 95), "p99_ms": percentile(ordered, 99),
                "max_ms": max(values), "over_50ms": sum(value > 50 for value in values),
                "source": paths,
            })
    return {
        "entries": entries,
        "unit": "milliseconds per benchmark control",
        "quantile_method": "Linear interpolation over all raw benchmark compute_ms values; no averaging of episode quantiles.",
        "scope": "观测打包、BC、可选世界模型与恢复控制计算；不含物理推进、日志、传感器或网络。并行负载会影响计时；不是端到端实时性验证。",
        "threshold_ms": 50,
        "control_hz": 20,
    }


def build_run(case_id, controller, noise, demo):
    suffix = "0" if noise == 0 else "0.05"
    job_id = f"{controller}_full_s17_{suffix}"
    result_path = CONFIRMATION / job_id / "result.json"
    result = read_json(result_path)
    record = next(record for record in result["records"] if record["demo"] == demo)
    trace_path = result_path.parent / "trace.jsonl"
    register(trace_path)
    frames = []
    with trace_path.open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            if row["demo"] != demo:
                continue
            diagnostic = row["recovery"]
            before = row["state_before"]
            assert len(before) == 23
            frames.append({
                "step": row["step"], "eef": vector(before[0:3]),
                "object": vector(before[16:19]),
                "phase": diagnostic.get("mode_before", diagnostic["mode"]),
                "nextPhase": diagnostic["mode"],
                "holding": bool(diagnostic.get("stable_hold", False)),
                "attempts": int(diagnostic.get("attempts", 0)),
                "selected": row["selected"], "scores": vector(row["scores"], 8),
                "submitted": vector(row["submitted_action"]),
                "executed": vector(row["executed_action"]),
                "success": row["success_after"],
                "compute_ms": quantize(row["compute_ms"], 5),
                "queue": [vector(action) for action in row["queue_before"]],
            })
    assert len(frames) == record["steps"] <= 400
    assert [frame["step"] for frame in frames] == list(range(1, len(frames) + 1))
    assert frames[-1]["success"] == record["success"]
    return {
        "id": f"{case_id}-{controller}",
        "label": "Full + 冻结 v5" if controller == "v5" else "Full · 无恢复",
        "job": job_id, "method": "full", "controller": controller,
        "seed": 17, "noise": noise, "demo": demo,
        "success": record["success"], "steps": record["steps"],
        "attempts": record["attempts"], "verified_regrasps": record["verified_regrasps"],
        "source": rel(trace_path), "result_source": rel(result_path),
        "result": record, "frames": frames,
    }


def build_cases():
    specifications = [
        ("recovery-noise", "恢复把停滞变成完成", "recovered", "demo_22000011", 0.05,
         "同一起点、同噪声、同一 Full seed17：v5 在一次恢复后于302步成功，无恢复在400步失败。此例为事后选取的机制展示。"),
        ("normal-clean", "正常策略直接完成", "success", "demo_22000051", 0.0,
         "Full seed17 的普通成功回合：v5没有发起恢复，85步完成。用于对照正常控制与恢复接管。"),
        ("failure-noise", "两次尝试后仍然失败", "failure", "demo_22000040", 0.05,
         "Full seed17 在两次恢复尝试后仍于400步失败；保留真实失败，不能把局部抓取或阶段推进当作任务成功。"),
    ]
    output = []
    for case_id, title, kind, demo, noise, description in specifications:
        runs = [build_run(case_id, controller, noise, demo) for controller in ("v5", "none")]
        if kind == "recovered":
            assert runs[0]["success"] and not runs[1]["success"] and runs[0]["attempts"] > 0
        elif kind == "success":
            assert runs[0]["success"] and runs[0]["attempts"] == 0
        else:
            assert not runs[0]["success"]
        output.append({"id": case_id, "title": title, "kind": kind,
                       "description": description, "demo": demo, "noise": noise,
                       "seed": 17, "runs": runs})
    return output


def pack_frames(data):
    actions = []
    action_ids = {}
    phases = []
    phase_ids = {}

    def action_id(action):
        key = tuple(action)
        if key not in action_ids:
            action_ids[key] = len(actions)
            actions.append(action)
        return action_ids[key]

    def phase_id(phase):
        if phase not in phase_ids:
            phase_ids[phase] = len(phases)
            phases.append(phase)
        return phase_ids[phase]

    for case in data["cases"]:
        for run in case["runs"]:
            packed = []
            for frame in run["frames"]:
                row = [frame[key] for key in FRAME_KEYS]
                row[3] = phase_id(row[3])
                row[4] = phase_id(row[4])
                row[9] = action_id(row[9])
                row[10] = action_id(row[10])
                row[13] = [action_id(action) for action in row[13]]
                packed.append(row)
            run["frames"] = packed
    return actions, phases


def main():
    summary_path = STAGE / "analysis/confirmation/summary.json"
    summary = read_json(summary_path)
    cells = build_cells(read_csv(STAGE / "analysis/confirmation/cells.csv"))
    effects = build_effects(read_csv(STAGE / "analysis/confirmation/paired_effects.csv"))
    register(STAGE / "METHODS.md")
    register(STAGE / "REPORT.md")
    assert summary["independent_starts"] == 60
    assert summary["executions"] == 1680
    data = {
        "meta": {
            "schema_version": 1, "evidence_date": "2026-10-22",
            "independent_starts": 60, "confirmation_executions": 1680,
            "registered_jobs": 28, "world_model_seeds": [17, 23, 41],
            "delay": 2, "horizon_steps": 400, "control_hz": 20,
            "observation_dimensions": 23, "candidate_count": 4,
            "prediction_horizon": 8, "attempt_limit": 2,
            "formal_controller": "v5", "default_system_policy": "full",
            "highest_formal_task_success_policy": "bc",
            "default_case": "recovery-noise",
            "main_factorial_executions": 960, "candidate_executions": 480,
            "observation_confirmation_executions": 240,
            "training_scope": "Full uses three fixed WM training seeds; BC uses one fixed historical policy. Confirmation inference does not cover arbitrary retraining.",
            "observation_scope": "The main frozen-policy comparison uses compatible legacy observations. Canonical/legacy newly trained BCs are a separate observation study, not relabeled historical weights.",
            "sample_scope": "三种子、两噪声和各方法共用60个独立原生起点；执行次数不增加独立起点数。",
            "stability_definition": "首次成功后另观察20控制步：保留在途队列和噪声，提交中性平移/旋转及开爪；20帧均满足原成功判据且末10帧物体差分速度小于0.02m/s。分母为全部评估，失败不通过。",
            "stability_scope": "额外稳定性诊断独立于400步正式成功判据，不计入策略步数、计时样本或新独立样本。",
            "case_scope": "保存日志的逐步轨迹重放；事后选例，不是实时仿真、预测序列、机器人视频或额外统计样本。",
            "limits": [
                "单任务 PickPlaceCan、Panda、23维含物体真值的仿真状态；未验证视觉或真机泛化。",
                "Full+v5展示完整世界模型系统；本批最高正式任务成功率属于BC+v5，未证明世界模型稳定优于BC。",
                "固定D2、400步、有限起点与固定权重；不能推及任意延迟、任务或重训种子。",
                "配对区间按60起点bootstrap，未做多重比较校正；三WM种子先在起点内平均。",
                "队列预算候选存在救回与退步，本轮未采用；历史v21也不替代冻结v5。",
                "展示计时不含物理推进、日志和真实通信；不构成真机端到端实时性或安全保证。",
            ],
            "source": [rel(summary_path), rel(STAGE / "REPORT.md"), rel(STAGE / "METHODS.md")],
        },
        "cells": cells, "effects": effects, "cases": build_cases(), "timing": build_timing(),
    }
    frame_count = sum(len(run["frames"]) for case in data["cases"] for run in case["runs"])
    actions, phases = pack_frames(data)
    effect_keys = list(effects[0])
    data["effects"] = [[effect[key] for key in effect_keys] for effect in effects]
    payload = {"data": data, "actions": actions, "phases": phases}
    compact = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    javascript = "/* Generated by python web/build_data.py; original evidence is read-only. */\n(() => {\nconst packed=" + compact + ";\n"
    javascript += "const keys=" + json.dumps(FRAME_KEYS, separators=(",", ":")) + ";\n"
    javascript += "const effectKeys=" + json.dumps(effect_keys, separators=(",", ":")) + ";\n"
    javascript += "packed.data.effects=packed.data.effects.map(row=>Object.fromEntries(effectKeys.map((key,i)=>[key,row[i]])));\n"
    javascript += "for(const c of packed.data.cases){for(const run of c.runs){run.frames=run.frames.map(row=>{const f=Object.fromEntries(keys.map((key,i)=>[key,row[i]]));f.phase=packed.phases[f.phase];f.nextPhase=packed.phases[f.nextPhase];f.submitted=packed.actions[f.submitted].slice();f.executed=packed.actions[f.executed].slice();f.queue=f.queue.map(i=>packed.actions[i].slice());return f;});}}\nwindow.CANLAB_DATA=packed.data;\n})();\n"
    WEB.mkdir(exist_ok=True)
    output_path = WEB / "data.js"
    output_path.write_text(javascript, encoding="utf-8", newline="\n")
    output_bytes = output_path.read_bytes()
    assert len(output_bytes) < 500 * 1024, f"Viewer data unexpectedly large: {len(output_bytes)} bytes"
    manifest = {
        "schema_version": 1, "command": "python web/build_data.py", "dependency_scope": "Python standard library only",
        "evidence_date": "2026-10-22", "source_mutation": False,
        "inputs": dict(sorted(INPUTS.items())),
        "outputs": {
            "web/data.js": {"sha256": hashlib.sha256(output_bytes).hexdigest(), "bytes": len(output_bytes)},
            "web/build_data.py": {"sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},
        },
        "manifest_self_hash": "Excluded to avoid a self-referential digest.",
        "counts": {"cells": len(cells), "effects": len(effects), "cases": len(data["cases"]),
                   "runs": 6, "frames": frame_count, "shared_actions": len(actions)},
        "fields": {
            "meta": "Only the 2026-10-22 confirmation batch; 60 independent starts, 1680 executions; no pooling with old v5 results.",
            "cells": "Counts pooled only over fixed WM seeds within the same policy/controller/noise. total is execution denominator; independent_starts always 60. stable uses all-evaluation denominator.",
            "effects": "Exact CSV values, including original metric/unit/contrast and source_row. equal_noise_joint means noise conditions are equally weighted within each start. No recomputation of historical confidence intervals.",
            "cases": "Three post hoc Full seed17 cases, each paired with the same demo/noise/seed without recovery. Every original benchmark control is retained; no subsampling, smoothing or terminal extrapolation.",
            "frames.eef/object": "state_before[0:3] / state_before[16:19], world coordinates in metres, before this control's physics step.",
            "frames.phase/nextPhase": "recovery.mode_before / recovery.mode: phase is the internal mode before entering choose; nextPhase is the stage that generated this control's action. It is different from recovery.next_mode (the internal state after choose), and is not the next physical frame.",
            "frames.holding": "Logged recovery.stable_hold, an observation-history holding estimate; not contact truth or force closure.",
            "frames.selected/scores": "Logged BC candidate index and four learned scores; not an exported future state sequence. A recovery override may replace the selected proposal.",
            "frames.submitted/executed/queue": "Submitted command; actual noisy command executed by FIFO; unnoised queue_before. Each action has seven dimensions, queue length is two.",
            "frames.success": "success_after from the physics step. Paired positions are pre-step while this flag is post-step, exactly as logged.",
            "frames.compute_ms": "Logged benchmark computation time only, excluding physics and JSON writing.",
            "display_precision": "展示副本的小数精度截断：坐标与动作保留6位，scores保留8位，逐帧compute_ms保留5位。原始日志不替换；量化值不用来重算成功、区间或统计。",
            "packing": "Internal frame/effect column rows, phase IDs and shared action IDs are lossless relative to the display-quantized copy; data.js immediately restores the public object/array schema. Effect values are not quantized.",
            "timing": "Raw compute_ms pooled by policy and noise; linear-interpolation quantiles over controls, not averaged episode quantiles. Only formal v5 jobs. Parallel load affects measurements.",
        },
    }
    (WEB / "data_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"status": "ok", "bytes": len(output_bytes), **manifest["counts"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
