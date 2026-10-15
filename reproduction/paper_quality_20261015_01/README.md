# 新论文图表、提纲与全项目复查

本轮重新生成36张图，每张提供600 dpi PNG、矢量PDF/SVG与测量CSV；附图注、来源哈希、详细提纲和曲线解释。原始代码、权重、结果、旧图及旧写作包保留。没有新训练、仿真或论文正文。

## 先打开

- [图表浏览器](index.html)：可直接双击离线打开，支持主题搜索、正文/附录过滤。
- [检查报告](REPORT.md)、[清单](CHECKLIST.csv)、[曲线为什么跳变](CURVE_EXPLANATIONS.md)。
- [当前详细提纲](THESIS_OUTLINE_REVIEWED.md)、[逐图图注](FIGURE_CATALOG.md)、[下一步计划](PLAN_AND_NEXT_STEPS.md)。

项目根目录PyCharm终端：

```powershell
& .\.venv\Scripts\python.exe -m http.server 8766 --bind 127.0.0.1
```

保持运行，打开 **http://127.0.0.1:8766/reproduction/paper_quality_20261015_01/index.html**。已有8766服务可直接刷新。机器人主前端仍是 http://127.0.0.1:8766/ ，现已链接新图并更新当前展示的轨迹和RMSE图。

## 不运行实验的验证与重绘

项目根目录核验历史资产与本轮交付：

```powershell
& .\.venv\Scripts\python.exe -X utf8 -B .\reproduction\paper_quality_20261015_01\verify.py
```

重绘必须选择一个不存在/空的新输出目录，不改旧图：

```powershell
& .\.venv\Scripts\python.exe -X utf8 -B .\reproduction\paper_quality_20261015_01\build_figures.py --output .\reproduction\paper_figures_preview
```

需要NumPy、Matplotlib与中文字体（Microsoft YaHei或Noto Sans CJK SC）。已保存绘图输入随包提供，不需要Torch、GPU、原始完整数据集或机器人仿真。重绘数值应一致，PDF元数据时间及字体环境可使字节SHA不同。

`check_figures.py`是本次PDF渲染验收工具，另需Poppler的pdfinfo/pdffonts/pdfimages/pdftoppm与Pillow；不是浏览图片或写论文的必装依赖。`prepare_inputs.py`、`audit_project.py`和`publish_documents.py`用于本仓整理，不能在小包里运行，也不要反复运行来修改历史目录。

## 换设备

[下载本轮图表与提纲ZIP](builds/CAN_LAB_PAPER_FIGURES_20261015.zip)。本机文件位于本目录builds下，下载文件不会重复提交Git；克隆后运行`build_package.py`重建。

解压后在包目录执行：

```powershell
python -B verify.py --package
```

然后直接打开`index.html`；需要重新绘图时，配置上面的绘图依赖并运行`python -B build_figures.py --output figures_preview`。

本包是新增图表/提纲/小型来源增补。换设备写作时，与上一轮的旧WRITING、v6—v11增补、独立展示三个ZIP一起携带；旧包不覆盖，新图与新提纲优先使用。本包不包含全部原始JSONL或权重，不声称能独立完成物理重跑。

## 论文插图标准与边界

按180.3 mm原宽插入，标签9 pt、刻度8 pt；学校版心更窄时先检查缩放后的字号。图号F/A是资料编号，终稿按章节重排。PDF已全部实际渲染检查，SVG文字转路径避免换设备缺字。PNG高分辨率不等于算法有效，负结果完整保留。

全部旧图主题覆盖，但不重写历史存档、截图、视频和封面。旧F19与F09重复，合并；密集图拆开后总计36张，正文只选与研究问题直接相关的图。

CSV各列的物理单位与统计含义见[数据字典](DATA_DICTIONARY.md)；19,012条是图中测量/统计导出行数，不是独立实验数。
