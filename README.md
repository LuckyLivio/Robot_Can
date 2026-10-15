# CAN LAB · 机器人世界模型与恢复控制

本项目研究延迟控制下的机器人罐体抓取搬运：冻结BC策略产生候选，世界模型预测并评分，恢复控制器处理抓取失效、姿态变化和路径约束。实验使用仿真中的特权当前状态，不等同于视觉输入或实机验证。

## 当前状态（2026-10-16）

**v14 两轮小测试共64次；最终 v13 / T / C / v14 为6/8、6/8、5/8、6/8。门槛未通过，未采用；未运行大规模消融、240次开发或全新起点确认。**

斜靠案例的首次接近、抓取和抬升已改善；剩余失败为持物搬运的关节可达性与箱沿路径耗时。C单独消融还损失一个旧成功，不能宣称总体改善。既有正式成果、v13及全部旧代码、权重和结果保留。本轮没有训练，也没有论文正文。

[本轮检查报告](reproduction/improvement_v14_20261016_01/REPORT.md) · [v14前端](reproduction/improvement_v14_20261016_01/index.html) · [执行前协议](reproduction/improvement_v14_20261016_01/protocols/PLAN.md) · [v13原报告](reproduction/improvement_v13_20261016_01/REPORT.md)

## 启动前端

```powershell
Set-Location 'C:\Users\Livio\Desktop\robot_can'
& '.\.venv\Scripts\python.exe' -m http.server 8766 --bind 127.0.0.1 --directory 'C:\Users\Livio\Desktop\robot_can'
```

打开完整地址：**http://127.0.0.1:8766/reproduction/improvement_v14_20261016_01/index.html** 。如果8766服务已经运行，直接打开即可；终端保持运行，Ctrl+C关闭。


页面展示两轮四组结果、两个同起点真实动作回放、失败原因与门槛。视频双方均如实显示400步未完成。旧v13页面仍可直接访问：http://127.0.0.1:8766/reproduction/improvement_v13_20261016_01/index.html 。

## 导航

- [项目分类导航](PROJECT_NAVIGATION.md)
- [环境与运行指南](PROGRAM_GUIDE.md)
- [当前状态与门槛](STATUS.md)
- [结果索引](RESULTS.md)
- [证据索引](EVIDENCE_INDEX.md)
- [前端演示指南](DEMO_GUIDE.md)
- [写作材料交接状态](THESIS_HANDOFF_LATEST.md)
- [本轮目录及复查命令](reproduction/improvement_v14_20261016_01/README.md)
- [此前README原样快照](reproduction/improvement_v14_20261016_01/before/README.md)

当前v14不可替换已经封存的对照结果。实验完成、保存输入回放、物理回放与预先准备的作业分别计数；失败记录不删除，缺失实验不以图表补成成功。
