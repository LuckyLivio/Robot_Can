> 2026-10-15论文图表复查：[新图与数据总览](reproduction/paper_quality_20261015_01/index.html) · [全项目报告](reproduction/paper_quality_20261015_01/REPORT.md) · [当前提纲与证据映射](reproduction/paper_quality_20261015_01/THESIS_OUTLINE_REVIEWED.md)。36张图重新生成；没有新增训练、仿真或论文正文。

# 当前论文资料交接说明（2026-10-15交付更新）

跨设备资料已集中到 `reproduction/portable_delivery_20261015_01/builds/TRANSFER_TO_NEW_DEVICE/`，可直接复制整个文件夹。[交付说明](reproduction/portable_delivery_20261015_01/README.md) · [验收页面](reproduction/portable_delivery_20261015_01/index.html) · [目标设备清单](reproduction/portable_delivery_20261015_01/TARGET_DEVICE_CHECKLIST.md)。

三个ZIP合计约273.9 MiB：旧WRITING主线包252.6 MiB、新写作增补4.8 MiB、新展示包16.5 MiB。旧ZIP原位置保留，新文件夹中是经哈希核对的副本。

- 旧THESIS_HANDOFF_20261015及WRITING/FULL ZIP对应c8bbe86：原世界模型与v5主线、40张表、19组图和提纲，不含v6—v11。
- 新CAN_LAB_WRITING_ADDENDUM对应fad3100：v6—v11各报告、逐回合结果、表、图、协议/校验资料、v11视频及全项目审查。含29份文档阅读视图和706份候选结果JSON索引；中断记录保留并标记，不把它们计为完整批次。
- 新CAN_LAB_DEMO为独立静态展示：11段已有视频、两张v11原始轨迹图、八种开发条件。无需PyTorch/GPU，使用包内portable.py在8767启动。

主线仍是v5；v11开发235/240，未采用。写作先读[最新贡献](CONTRIBUTIONS.md)、[当前结果](RESULTS.md)、[当前提纲](THESIS_OUTLINE.md)。详细结构优先使用本轮提纲；[旧详细提纲](THESIS_HANDOFF_20261015/01_outline/THESIS_OUTLINE_REVISED.md)及其对应批次数据仅作冻结记录参考。

生成ZIP和解压副本不随Git克隆提供，避免反复提交大副本。克隆后可用新build_packages.py重建两个新包；旧WRITING ZIP需单独复制，旧包652份gzip也不随克隆提供。完整原始轨迹仍在仓库原路径。

本机干净标准库环境、移位中文路径、文件/ZIP与前端检查已通过；第二台电脑实际验收未执行。没有论文正文、新训练或新仿真实验，尚未实施v12控制修复。

本轮新增独立图表与提纲ZIP，见 [下载与命令](reproduction/paper_quality_20261015_01/README.md)。旧三ZIP不覆盖；换设备时额外带本轮ZIP，写作优先使用新图注和提纲。
