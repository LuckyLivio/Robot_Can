# 跨设备交付：先展示与写作，再按需复核

本目录落实全项目审查计划P1-A。冻结资料来源为提交 `fad3100c22b238a12fd433bddc4c5d897c436b98`，新增便携展示、v6—v11写作增补、复核/重跑包装入口。未修改控制器或模型，未新增实验，未写论文正文。

## 现在可以带走什么

推荐直接复制 [TRANSFER_TO_NEW_DEVICE](builds/TRANSFER_TO_NEW_DEVICE/) 整个文件夹：三个ZIP、校验文件和中文操作说明已经放在一起，原ZIP未移动。

| 用途 | 内容 | 边界 |
|---|---|---|
| 展示 | [CAN_LAB_DEMO.zip](builds/release_02/CAN_LAB_DEMO.zip)，约16.5 MiB | 11段已有视频、两张v11图、开发表；无需GPU/仿真依赖 |
| 最新写作增补 | [CAN_LAB_WRITING_ADDENDUM.zip](builds/release_02/CAN_LAB_WRITING_ADDENDUM.zip)，约4.8 MiB | v6—v11报告、结果、分析表、图、配置和本次审查；不替代旧主线包 |
| 主线写作 | 原 `THESIS_HANDOFF_20261015_WRITING.zip`，约252.6 MiB | 原世界模型、v5、40张表、19组图及提纲；版本c8bbe86 |
| 复核/重跑 | [REPRODUCTION_MANIFEST.json](REPRODUCTION_MANIFEST.json) + 完整仓库 | 检查589项冻结输入，提供v5原生/几何和v11开发入口；不含可移植虚拟环境 |

旧主线包与增补包分开解压，先读增补说明，再按各批次取数据。不要覆盖旧包，不要把v11当作采用版本。展示包覆盖11段选定视频，并不是原研究前端所有历史页面的完整镜像。

## 在新设备启动展示

解压 `CAN_LAB_DEMO.zip`，进入里面的 `CAN_LAB_DEMO` 文件夹，在该目录终端执行：

```powershell
python -B portable.py verify
python -B portable.py serve --port 8767 --open
```

准确地址：<http://127.0.0.1:8767/>。服务根目录就是展示首页，不会显示项目文件列表。已有服务时直接访问；端口被其他程序占用则改为8768。Ctrl+C停止。只需Python3.10或更新版本标准库、现代浏览器，不需pip安装任何包。

写作增补包可以用同样命令在8768打开。包内报告提供阅读视图；未收录的来源链接明确指向固定GitHub提交，离线时不可访问。原文Markdown原样保留，其原项目相对路径不保证在精简包内全部存在。

## 在当前项目使用入口

在项目根目录运行；路径不含用户名称，也不依赖旧jobs中的解释器路径：

```powershell
& '.\.venv\Scripts\python.exe' -X utf8 -B reproduction\portable_delivery_20261015_01\launcher.py
& '.\.venv\Scripts\python.exe' -X utf8 -B reproduction\portable_delivery_20261015_01\launcher.py verify
& '.\.venv\Scripts\python.exe' -X utf8 -B reproduction\portable_delivery_20261015_01\launcher.py probe-models
```

第一条仅显示帮助；第二条检查旧资产和新交付；第三条执行pip check以及一个保存观测上的BC与六个WM前向，不创建仿真环境。

**以下只生成计划，当前任务没有执行仿真：**

```powershell
& '.\.venv\Scripts\python.exe' -X utf8 -B reproduction\portable_delivery_20261015_01\launcher.py list-jobs
& '.\.venv\Scripts\python.exe' -X utf8 -B reproduction\portable_delivery_20261015_01\launcher.py rerun --experiment v11-development --job-id v11_full_s41_noise005 --output reproduction\portable_delivery_20261015_01\outputs\device_check_01
```

实际运行必须另外添加 `--execute`；新输出路径不得存在。省略job-id会运行整套冻结任务：v11开发240回合，v5原生2400回合，v5几何80回合。它们都是旧起点的重复核验，不是新的独立确认。新入口只验证输入、运行完成标记和回合数；不冒充逐步物理一致性核验，后者需另行安排。

## 从GitHub克隆后重建

生成的ZIP、重复解压副本和本机测试虚拟环境不纳入Git；生成脚本、清单、校验凭据已纳入。保持来源文件未改，在项目根运行（标准库即可）：

```powershell
python -B reproduction\portable_delivery_20261015_01\build_packages.py --output reproduction\portable_delivery_20261015_01\builds\release_02
```

输出目录必须是新的。重建逐文件内容可按清单核验；ZIP含生成时的时间信息，不承诺ZIP字节跨次完全一致。若要组装三个包的迁移文件夹，还需单独提供旧WRITING ZIP；它不在Git克隆中。参见 [目标设备清单](TARGET_DEVICE_CHECKLIST.md) 和 [本轮报告](REPORT.md)。

本机验证已通过；第二台电脑实际安装、视频播放及物理仿真仍未执行。v12持物等待修复留作下一算法阶段。
