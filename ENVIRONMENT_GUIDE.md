# 冻结实验环境与提交说明

PyCharm沿用项目 `.venv\Scripts\python.exe`，工作目录项目根。已有实验快照：Python3.10.9、torch2.14.1+cu130、NumPy1.26.4、robosuite1.5.1、MuJoCo3.3.0，完整字段在[environment.json](reproduction/review_20261012_01/environment.json)、[已安装版本](reproduction/review_20261012_01/environment-freeze.txt)。本整合阶段没有重新测试CUDA、运行模型或重装依赖。

`requirements-repro.txt`保留的是旧安装建议，其torch2.9.1注释不是实际冻结版本，不应据此降级当前环境。完整版本快照也不是已验证的跨电脑离线安装包。

Windows兼容记录在 `data/windows_compatibility.json`。`setup_windows.py`仅面向当前项目虚拟环境，复制MuJoCo DLL并设置WGL相关宏；它有写入，不要在已工作的环境中为“看演示”反复执行。新电脑需要根据其系统单独确认，不能直接复制`.venv`当完整安装方案。

数据：[来源和SHA](data/can_ph_lowdim_v15.manifest.json)。BC：[冻结路径](policy/bc_chunk_dev_v4/policy_15000.pt)。Full/Plain：models/multiseed_20261012_01_{full,plain}_s{17,23,41}/model.pt。原学习权重在本阶段不变。

提交副本建议包含源码、必要权重、数据下载校验与划分、协议/配置、主结果/验证记录、演示与文档；虚拟环境和IDE缓存不当作研究成果。先整理清单，后续在目标演示电脑做独立安装/展示验证。

版本：2026-10-12 成果整合版；旧根文档见 reproduction/consolidation_20261012_01/previous_documents/
