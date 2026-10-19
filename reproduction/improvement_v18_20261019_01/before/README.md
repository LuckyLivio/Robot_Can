# CAN LAB · 机器人世界模型与恢复控制

本项目研究延迟控制下的罐体抓取搬运：冻结 BC 策略产生候选，世界模型预测并评分，恢复控制器处理失抓、支撑姿态和路径约束。当前使用特权状态仿真，不等同于视觉输入或实机验证。

## 当前状态（2026-10-19）

**v17 已完成七组共 63 次小测试：v15 4/9、v16 2/9、原预算候选 7/9、路径单项 2/9、箱沿单项 2/9、持物单项 2/9、完整 v17 3/9。未通过预定门槛，完整 v17 未采用。**

每组 9 个条件包括 8 个标准条件和 1 个复用 6000005 起点的 clearance-only 父配置 profile，只有 8 个不同起点；不得将 63 次执行视为 63 个独立样本。三个单项修复分别加在完整 v16 上，预算候选仍为原 v15 仅预算 C。

公共路径复用、短路线和反馈控制已实现并接受闭环检验；组件检查通过不等于整回合成功。预算候选的 7/9 仅表示任务成功，其中两个成功条件在 CARRY/PLACE 阶段低于现行 0.04 rad 关节余量，不能整体回退采用。658 次扩展消融、v15/v16/v17 各 240 次开发（共 720 次）及 1440 次全新起点确认均未运行。保留预算候选，既有主成果不替换。

[完整报告](reproduction/improvement_v17_20261019_01/REPORT.md) · [v17 前端](reproduction/improvement_v17_20261019_01/index.html) · [执行前协议](reproduction/improvement_v17_20261019_01/protocols/PLAN.md) · [v16 原报告](reproduction/improvement_v16_20261016_01/REPORT.md)

保留 v16 及全部旧代码、权重和结果。本轮没有泛化训练，没有写论文。

## 启动前端

```powershell
Set-Location 'C:\Users\Livio\Desktop\robot_can'
& '.\.venv\Scripts\python.exe' -m http.server 8766 --bind 127.0.0.1 --directory 'C:\Users\Livio\Desktop\robot_can'
```

打开完整地址：**http://127.0.0.1:8766/reproduction/improvement_v17_20261019_01/index.html** 。已有 8766 服务时直接打开，无需再次启动；终端保持运行，Ctrl+C 停止。


页面展示真实七组结果、目标完成情况、失败诊断、未执行阶段和可下载图表。本轮没有新增 v17 机器人视频；页面中的 v14 视频链接明确标注为历史版本。

## 导航

- [项目分类导航](PROJECT_NAVIGATION.md)
- [环境与运行指南](PROGRAM_GUIDE.md)
- [项目状态](STATUS.md)
- [实验结果](RESULTS.md) · [证据索引](EVIDENCE_INDEX.md)
- [前端演示指南](DEMO_GUIDE.md)
- [写作材料交接](THESIS_HANDOFF_LATEST.md)
- [本轮目录与核验命令](reproduction/improvement_v17_20261019_01/README.md)
- [此前 README 原样快照](reproduction/improvement_v17_20261019_01/before/README.md)
