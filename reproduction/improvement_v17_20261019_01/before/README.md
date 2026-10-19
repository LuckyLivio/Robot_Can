# CAN LAB · 机器人世界模型与恢复控制

本项目研究延迟控制下的罐体抓取搬运：冻结BC策略产生候选，世界模型预测并评分，恢复控制器处理失抓、支撑姿态和路径约束。当前使用特权状态仿真，不等同于视觉输入或实机验证。

## 当前状态（2026-10-16）

**v16已完成63次七组小测试：v14 / v15 / 预算候选 / IK修复 / 持物修复 / 箱沿修复 / 完整v16为6/9、4/9、7/9、2/9、4/9、2/9、2/9。门槛未通过，完整v16未采用。**

9个条件包含8个标准条件和1个复用6000005起点的预算配置profile，只有8个不同起点。标准条件下v16为2/8、v15为3/8、v14为6/8。三个修复单项分别加在完整v15之上；预算候选沿用原v15仅预算配置。

局部IK找到更多合法路径，部分持物转向达标，但没有提高整回合成功率。新的等待、规划与运输耗时导致预算不足，另有等价大角转向超时及观测失抓信号并触发恢复。预算模块继续保留为候选。既有正式成果不替换；658次扩展消融、三版各240次开发（共720次）和1440次全新起点确认均未运行。 v15及全部旧代码、权重和结果保留。本轮未训练，也未写论文。

[本轮完整报告](reproduction/improvement_v16_20261016_01/REPORT.md) · [v16前端](reproduction/improvement_v16_20261016_01/index.html) · [执行前协议](reproduction/improvement_v16_20261016_01/protocols/PLAN.md) · [v15原报告](reproduction/improvement_v15_20261016_01/REPORT.md)

## 启动前端

```powershell
Set-Location 'C:\Users\Livio\Desktop\robot_can'
& '.\.venv\Scripts\python.exe' -m http.server 8766 --bind 127.0.0.1 --directory 'C:\Users\Livio\Desktop\robot_can'
```

打开完整地址：**http://127.0.0.1:8766/reproduction/improvement_v16_20261016_01/index.html** 。已有8766服务时直接打开，无需再启动；终端保持运行，Ctrl+C停止。


页面展示真实七组结果、三目标完成情况、未执行阶段与可下载图表。v16没有新增机器人视频；页面链接的v14视频明确标注历史版本，不冒充本轮成果。

## 导航

- [分类导航](PROJECT_NAVIGATION.md)
- [环境与运行指南](PROGRAM_GUIDE.md)
- [项目状态](STATUS.md)
- [结果索引](RESULTS.md)
- [证据索引](EVIDENCE_INDEX.md)
- [前端演示指南](DEMO_GUIDE.md)
- [写作材料交接](THESIS_HANDOFF_LATEST.md)
- [本轮目录与核验命令](reproduction/improvement_v16_20261016_01/README.md)
- [此前README原样快照](reproduction/improvement_v16_20261016_01/before/README.md)
