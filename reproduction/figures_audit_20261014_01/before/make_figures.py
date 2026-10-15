"""Generate thesis-ready figures from the frozen delay-compensation runs.

Run from this directory with the GPU environment Python.  The script only
reads the JSON result files and writes PNG/PDF figures to ``figures/``.
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "figures"
OUT.mkdir(exist_ok=True)


def load(rel: str) -> dict:
    with (ROOT / rel).open("r", encoding="utf-8") as f:
        return json.load(f)


def records(rel: str):
    return load(rel)["records"]


def save(fig, name: str):
    fig.tight_layout()
    fig.savefig(OUT / f"{name}.png", dpi=220, bbox_inches="tight")
    fig.savefig(OUT / f"{name}.pdf", bbox_inches="tight")
    plt.close(fig)


plt.rcParams.update({"font.size": 10, "axes.titlesize": 12, "figure.dpi": 120})

# Figure 1: frozen baseline sweep on development data and sealed comparison.
labels = ["BC", "Shift k=0", "Shift k=1\n(strongest)", "Shift k=2", "Shift k=3", "WM + gate"]
dev = np.array([15, 15, 24, 23, 21, 25]) / 30
clean = np.array([17, np.nan, 21, 22, np.nan, 23]) / 30
noise = np.array([19, np.nan, 19, 24, np.nan, 23]) / 30
x = np.arange(len(labels))
fig, ax = plt.subplots(figsize=(8.6, 4.5))
w = 0.25
for off, vals, name, color in [(-w, dev, "开发集", "#4C78A8"), (0, clean, "封存测试·干净", "#F58518"), (w, noise, "封存测试·σ=0.05", "#54A24B")]:
    ax.bar(x + off, vals, width=w, label=name, color=color)
ax.axhline(0.8, color="#777", ls="--", lw=0.8)
ax.set_ylim(0, 1.03)
ax.set_ylabel("闭环成功率")
ax.set_xticks(x, labels)
ax.set_title("延迟 D=2：候选时间偏移扫描与风险门控世界模型")
ax.legend(frameon=False, ncol=3, loc="lower left")
ax.text(5, 0.96, "+2 / +4 个成功回合", ha="center", va="top", fontsize=9, color="#222")
save(fig, "figure_success_rate")

# Figure 2: structural ablation under the predeclared noisy sealed condition.
ab_names = ["强基线\nShift k=1", "完整 WM\n+门控", "Plain future\n(去排序)", "Direct scorer\n(无未来状态)"]
ab_values = np.array([19, 23, 23, 22]) / 30
fig, ax = plt.subplots(figsize=(7.2, 4.2))
bars = ax.bar(ab_names, ab_values, color=["#9C9C9C", "#4C78A8", "#72B7B2", "#B279A2"])
ax.set_ylim(0, 1.0)
ax.set_ylabel("闭环成功率（封存测试，σ=0.05）")
ax.set_title("结构消融：递归未来状态、排序监督与风险门控")
for b, v in zip(bars, [19, 23, 23, 22]):
    ax.text(b.get_x() + b.get_width()/2, b.get_height() + 0.02, f"{v}/30", ha="center")
ax.axhline(19/30, color="#777", ls="--", lw=0.8)
save(fig, "figure_ablation")

# Figure 3: paired outcomes against the strongest fixed shift.
def paired(a_rel: str, b_rel: str):
    a = {r["demo"]: bool(r["success"]) for r in records(a_rel)}
    b = {r["demo"]: bool(r["success"]) for r in records(b_rel)}
    # WM is a, shift is b.
    return np.array([[int(a[k]), int(b[k])] for k in sorted(a)])

for tag, wm_rel, shift_rel in [
    ("clean", "models/full_future_delay2_shift_v0/delay_wm_sealed_test_d2_shift_fbshift_fbi1_gm0.02_score.json", "models/full_future_delay2_shift_v0/delay_bc_shift_sealed_test_d2_k1.json"),
    ("noise005", "models/full_future_delay2_shift_v0/delay_wm_sealed_test_d2_shift_fbshift_fbi1_gm0.02_noise0.05_score.json", "models/full_future_delay2_shift_v0/delay_bc_shift_sealed_test_d2_k1_noise0.05.json"),
]:
    p = paired(wm_rel, shift_rel)
    # columns: WM, shift; categories are WM/shift.
    counts = [int(((p[:, 0] == 1) & (p[:, 1] == 1)).sum()), int(((p[:, 0] == 1) & (p[:, 1] == 0)).sum()), int(((p[:, 0] == 0) & (p[:, 1] == 1)).sum()), int(((p[:, 0] == 0) & (p[:, 1] == 0)).sum())]
    fig, ax = plt.subplots(figsize=(6.2, 4.0))
    bars = ax.bar(["两者成功", "WM 独胜", "固定偏移独胜", "两者失败"], counts, color=["#72B7B2", "#4C78A8", "#F58518", "#BDBDBD"])
    ax.set_ylabel("回合数（n=30）")
    ax.set_title(f"成对比较：WM 门控 vs 固定偏移 k=1（{tag}）")
    for b, c in zip(bars, counts):
        ax.text(b.get_x()+b.get_width()/2, c+0.3, str(c), ha="center")
    save(fig, f"figure_paired_{tag}")

# Figure 4: successful episode length.  This is a useful efficiency sanity check.
method_specs = [
    ("固定偏移 k=1", "models/full_future_delay2_shift_v0/delay_bc_shift_sealed_test_d2_k1.json", "#F58518"),
    ("WM + 门控", "models/full_future_delay2_shift_v0/delay_wm_sealed_test_d2_shift_fbshift_fbi1_gm0.02_score.json", "#4C78A8"),
]
fig, ax = plt.subplots(figsize=(6.5, 4.1))
data = []
for name, rel, color in method_specs:
    rr = records(rel)
    data.append([r["steps"] for r in rr if r["success"]])
bp = ax.boxplot(data, labels=[m[0] for m in method_specs], patch_artist=True, showmeans=True, meanline=True)
for patch, (_, _, color) in zip(bp["boxes"], method_specs):
    patch.set_facecolor(color); patch.set_alpha(0.65)
ax.set_ylabel("成功回合步数（越低越快）")
ax.set_title("成功回合的控制步数分布（干净封存测试）")
save(fig, "figure_success_steps")

# Figure 5: learning curves from training logs.
log = load("models/full_future_delay2_shift_v0/log.json")
epochs = np.arange(1, len(log) + 1)
fig, ax = plt.subplots(figsize=(7.0, 4.0))
for key, label, color in [("loss", "总损失", "#4C78A8"), ("prediction_loss", "状态预测损失", "#F58518"), ("ranking_loss", "候选排序损失", "#54A24B")]:
    if key in log[0]:
        ax.plot(epochs, [x[key] for x in log], label=label, color=color)
ax.set_xlabel("训练 epoch")
ax.set_ylabel("训练值")
ax.set_title("完整世界模型训练曲线")
ax.legend(frameon=False)
save(fig, "figure_training_curves")

# Figure 6: method diagram for the thesis chapter.
fig, ax = plt.subplots(figsize=(11.5, 3.0))
ax.set_xlim(0, 13); ax.set_ylim(0, 3); ax.axis("off")
boxes = [
    (0.2, 1.0, 1.7, 1.0, "当前状态\n+safety FIFO"),
    (2.4, 1.0, 1.7, 1.0, "BC 动作块\n候选 k=0..3"),
    (4.6, 1.0, 1.9, 1.0, "Action-conditioned\nGRU rollout"),
    (7.0, 1.0, 1.8, 1.0, "未来进度 /\n失败风险"),
    (9.3, 1.0, 1.9, 1.0, "风险门控\n与固定先验"),
]
for x0, y0, w0, h0, text0 in boxes:
    patch = plt.Rectangle((x0, y0), w0, h0, facecolor="#EAF2F8", edgecolor="#4C78A8", lw=1.6)
    ax.add_patch(patch); ax.text(x0+w0/2, y0+h0/2, text0, ha="center", va="center")
for x0 in [1.9, 4.1, 6.5, 8.8]:
    ax.annotate("", xy=(x0+0.42, 1.5), xytext=(x0, 1.5), arrowprops=dict(arrowstyle="->", lw=1.4, color="#444"))
ax.annotate("执行动作", xy=(12.6, 1.5), xytext=(11.8, 1.5), arrowprops=dict(arrowstyle="->", lw=1.4, color="#444"), ha="left", va="center")
ax.text(6.0, 2.55, "延迟感知的风险门控世界模型控制器", ha="center", fontsize=13, weight="bold")
ax.text(5.55, 0.35, "仅当候选预测分数超过固定偏移先验 δ=0.02 时覆盖先验", ha="center", color="#555")
save(fig, "figure_method_diagram")

print(f"wrote figures to {OUT}")
