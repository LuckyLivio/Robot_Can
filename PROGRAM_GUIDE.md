# 项目运行指南（当前入口）

**v17 已完成七组共 63 次小测试：v15 4/9、v16 2/9、原预算候选 7/9、路径单项 2/9、箱沿单项 2/9、持物单项 2/9、完整 v17 3/9。未通过预定门槛，完整 v17 未采用。**

每组 9 个条件包括 8 个标准条件和 1 个复用 6000005 起点的 clearance-only 父配置 profile，只有 8 个不同起点；不得将 63 次执行视为 63 个独立样本。三个单项修复分别加在完整 v16 上，预算候选仍为原 v15 仅预算 C。

公共路径复用、短路线和反馈控制已实现并接受闭环检验；组件检查通过不等于整回合成功。预算候选的 7/9 仅表示任务成功，其中两个成功条件在 CARRY/PLACE 阶段低于现行 0.04 rad 关节余量，不能整体回退采用。658 次扩展消融、v15/v16/v17 各 240 次开发（共 720 次）及 1440 次全新起点确认均未运行。保留预算候选，既有主成果不替换。

[完整报告](reproduction/improvement_v17_20261019_01/REPORT.md) · [v17 前端](reproduction/improvement_v17_20261019_01/index.html) · [执行前协议](reproduction/improvement_v17_20261019_01/protocols/PLAN.md) · [v16 原报告](reproduction/improvement_v16_20261016_01/REPORT.md)

沿用 `.venv\Scripts\python.exe`，在 PyCharm 中选择它作为解释器；不替换权重或旧环境。

## 启动前端

```powershell
Set-Location 'C:\Users\Livio\Desktop\robot_can'
& '.\.venv\Scripts\python.exe' -m http.server 8766 --bind 127.0.0.1 --directory 'C:\Users\Livio\Desktop\robot_can'
```

打开完整地址：**http://127.0.0.1:8766/reproduction/improvement_v17_20261019_01/index.html** 。已有 8766 服务时直接打开，无需再次启动；终端保持运行，Ctrl+C 停止。


## 核验与实验

[本轮 README](reproduction/improvement_v17_20261019_01/README.md)提供只读核验命令。阶段顺序由[执行前协议](reproduction/improvement_v17_20261019_01/protocols/PLAN.md)锁定，登记作业不代表已执行。小测试失败，不绕过门槛进入开发或确认。

早期训练、数据与历史运行命令保留在[此前指南快照](reproduction/improvement_v17_20261019_01/before/PROGRAM_GUIDE.md)，按对应版本使用。
