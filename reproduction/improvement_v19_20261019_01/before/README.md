# CAN LAB · 机器人世界模型与恢复控制

本项目研究延迟控制下的罐体抓取搬运：冻结 BC 策略产生候选，世界模型预测并评分，恢复控制器处理失抓、支撑姿态和路径约束。当前使用特权状态仿真，不等同于视觉输入或实机验证。

## 当前状态（2026-10-19）

**v18 已完成六组共 54 回合小测试及单项消融：实际 v16 2/9、实际 v17 3/9、原预算候选 7/9、仅衔接修复 2/9、仅短路线修复 2/9、完整 v18 2/9。未通过预定门槛，完整 v18 未采用。**

每组 9 个条件包括 8 个标准条件和 1 个复用 6000005 起点的 clearance-only 配置，只有 8 个不同起点。两个单项修复分别加在完整 v17 上；预算候选仍为原 v15 仅预算 C，保护条件不同，仅用于成功数参考。54 次执行不是 54 个独立起点。

本轮实现下降指令连续衔接，以及原朝向、内移端点的直接路线候选。组件和静态认证通过不等于整回合成功。未绕过小测试门槛：564 次扩展诊断、三版各 240 次开发（共 720 次）及 1440 次全新起点确认均未运行，未生成新确认起点。保留 v17、预算候选及全部旧代码、权重和结果。未做泛化训练，未写论文。

[完整报告](reproduction/improvement_v18_20261019_01/REPORT.md) · [v18 前端](reproduction/improvement_v18_20261019_01/index.html) · [执行前协议](reproduction/improvement_v18_20261019_01/protocols/PLAN.md) · [v17 原报告](reproduction/improvement_v17_20261019_01/REPORT.md)

## 启动前端

```powershell
Set-Location 'C:\Users\Livio\Desktop\robot_can'
& '.\.venv\Scripts\python.exe' -m http.server 8766 --bind 127.0.0.1 --directory 'C:\Users\Livio\Desktop\robot_can'
```

打开完整地址：**http://127.0.0.1:8766/reproduction/improvement_v18_20261019_01/index.html** 。已有 8766 服务时直接打开；终端保持运行，Ctrl+C 停止。


页面包含六组实际结果、目标完成情况、失败诊断、未执行阶段及可下载图表。本轮没有新增机器人视频，页面中的 v14 视频明确标注为历史版本。

## 导航

- [项目分类导航](PROJECT_NAVIGATION.md)
- [环境与运行指南](PROGRAM_GUIDE.md)
- [项目状态](STATUS.md)
- [实验结果](RESULTS.md) · [证据索引](EVIDENCE_INDEX.md)
- [前端演示指南](DEMO_GUIDE.md)
- [写作材料交接](THESIS_HANDOFF_LATEST.md)
- [本轮目录与核验命令](reproduction/improvement_v18_20261019_01/README.md)
- [此前 README 原样快照](reproduction/improvement_v18_20261019_01/before/README.md)
