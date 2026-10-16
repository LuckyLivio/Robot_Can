# CAN LAB · 机器人世界模型与恢复控制

本项目研究延迟控制下的罐体抓取搬运：冻结BC策略产生候选，世界模型预测并评分，恢复控制器处理失抓、支撑姿态和路径约束。当前使用特权状态仿真，不等同于视觉输入或实机验证。

## 当前状态（2026-10-16）

**v15已完成45次五组小测试：v14 / 仅搬运A / 仅分段B / 仅预算C / 完整v15为6/9、3/9、6/9、7/9、4/9。小测试未通过，v15未采用。**

9个条件包含8个标准条件和1个复用6000005起点的预算配置profile，不能当作9个独立起点。标准条件下完整v15为3/8、父v14为6/8；预算专用profile为v15成功、父版失败。

预算模块单独运行救回时间不足案例且未损失旧成功；搬运模块的局部IK误拒和转向耗时导致三个旧成功退步，两个主难例仍未完成。因此不替换既有正式成果，不进入470次消融、两版各240次开发或1440次全新起点确认。 v14及全部旧代码、权重和结果保留。本轮未训练，也未写论文。

[本轮完整报告](reproduction/improvement_v15_20261016_01/REPORT.md) · [v15前端](reproduction/improvement_v15_20261016_01/index.html) · [执行前协议](reproduction/improvement_v15_20261016_01/protocols/PLAN.md) · [v14原报告](reproduction/improvement_v14_20261016_01/REPORT.md)

## 启动前端

```powershell
Set-Location 'C:\Users\Livio\Desktop\robot_can'
& '.\.venv\Scripts\python.exe' -m http.server 8766 --bind 127.0.0.1 --directory 'C:\Users\Livio\Desktop\robot_can'
```

打开完整地址：**http://127.0.0.1:8766/reproduction/improvement_v15_20261016_01/index.html** 。已有8766服务时直接打开，无需再启动；终端保持运行，Ctrl+C停止。


页面展示真实五组结果、三目标完成情况、未执行阶段与可下载图表。v15没有新增机器人视频；页面链接的v14视频明确标注历史版本，不冒充本轮成果。

## 导航

- [分类导航](PROJECT_NAVIGATION.md)
- [环境与运行指南](PROGRAM_GUIDE.md)
- [项目状态](STATUS.md)
- [结果索引](RESULTS.md)
- [证据索引](EVIDENCE_INDEX.md)
- [前端演示指南](DEMO_GUIDE.md)
- [写作材料交接](THESIS_HANDOFF_LATEST.md)
- [本轮目录与核验命令](reproduction/improvement_v15_20261016_01/README.md)
- [此前README原样快照](reproduction/improvement_v15_20261016_01/before/README.md)
