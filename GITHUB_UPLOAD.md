> 2026-10-15论文图表复查：[新图与数据总览](reproduction/paper_quality_20261015_01/index.html) · [全项目报告](reproduction/paper_quality_20261015_01/REPORT.md) · [当前提纲与证据映射](reproduction/paper_quality_20261015_01/THESIS_OUTLINE_REVIEWED.md)。36张图重新生成；没有新增训练、仿真或论文正文。

# GitHub 项目快照

仓库：https://github.com/LuckyLivio/Robot_can

本次上传包含代码、文档、数据、模型/策略权重、原始实验结果、逐步轨迹、图表及演示资源。保留早期负结果和各版本归档，体积较大。虚拟环境、IDE 本机配置、Python 缓存和本地凭据文件排除。

这是截至 2026-10-15 的实验快照。历史图表深查在 `reproduction/figures_deepcheck_20261014_01/`；根 `figures/` 为上一轮图表，各轮分析按各自报告解释。当前结果存在开发集泛化不足、评分对少量候选组敏感及部分消融退化到固定 BC 等限制，见该目录 REPORT.md。

## 下载与环境

```powershell
git clone https://github.com/LuckyLivio/Robot_can.git
Set-Location Robot_can
```

环境配置见 ENVIRONMENT_GUIDE.md，已有本机虚拟环境可以继续使用。新电脑应自行建立环境，并按文档核对依赖；仓库不包含 `.venv`。模型和实验数据本次直接随 Git 版本化，不需要 Git LFS 拉取。

## 前端

在项目根目录运行：

```powershell
& .\.venv\Scripts\python.exe -m http.server 8766 --bind 127.0.0.1
```

主展示：http://127.0.0.1:8766/

当前论文图表：http://127.0.0.1:8766/reproduction/paper_quality_20261015_01/index.html

## 本机原始资产完整性

```powershell
& .\.venv\Scripts\python.exe -X utf8 -B .\reproduction\paper_quality_20261015_01\verify.py
```

当前入口校验本轮修改前10,270个受管理路径；本轮活动文档更新映射到before备份，其他旧文件保持原路径，历史清单不改写。

部分历史脚本保留本机绝对路径或创建新输出的保护条件，直接克隆后重跑旧脚本可能需要调整路径；`git clone` 与完整性核对不等于所有历史脚本已在另一台机器重跑。查看已有前端与图表不需要重新训练。

## 当前发布边界（2026-10-15）

主仓库已有v11及完整原始JSONL，受管理文件约8.99 GiB，Git对象另占约1.42 GiB。旧写作包内652份gzip和本地两份ZIP被.git/info/exclude排除，不会随克隆出现；仅写作/展示带WRITING及增补、展示ZIP即可；若需完整历史压缩快照，再单独带FULL ZIP。当前恢复主版本仍v5，v11开发未采用。[当前资料交接](THESIS_HANDOFF_LATEST.md)。
