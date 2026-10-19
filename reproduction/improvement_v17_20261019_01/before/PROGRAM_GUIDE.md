# 项目运行指南（当前入口）

**v16已完成63次七组小测试：v14 / v15 / 预算候选 / IK修复 / 持物修复 / 箱沿修复 / 完整v16为6/9、4/9、7/9、2/9、4/9、2/9、2/9。门槛未通过，完整v16未采用。**

沿用现有 `.venv\Scripts\python.exe`，在PyCharm选择它作为解释器。权重与依赖无需替换。

## 启动前端

```powershell
Set-Location 'C:\Users\Livio\Desktop\robot_can'
& '.\.venv\Scripts\python.exe' -m http.server 8766 --bind 127.0.0.1 --directory 'C:\Users\Livio\Desktop\robot_can'
```

打开完整地址：**http://127.0.0.1:8766/reproduction/improvement_v16_20261016_01/index.html** 。已有8766服务时直接打开，无需再启动；终端保持运行，Ctrl+C停止。


## 核验与实验

局部IK找到更多合法路径，部分持物转向达标，但没有提高整回合成功率。新的等待、规划与运输耗时导致预算不足，另有等价大角转向超时及观测失抓信号并触发恢复。预算模块继续保留为候选。既有正式成果不替换；658次扩展消融、三版各240次开发（共720次）和1440次全新起点确认均未运行。

[本轮README](reproduction/improvement_v16_20261016_01/README.md)提供只读核验命令。[执行前协议](reproduction/improvement_v16_20261016_01/protocols/PLAN.md)定义阶段顺序。`protocols/pilot_jobs.json`是已准备的658次作业，不是实验结果。开发冻结脚本同时检查结果、机制、保存输入和物理核验；本轮小测试失败，不能绕过它生成开发或确认结果。

[本轮完整报告](reproduction/improvement_v16_20261016_01/REPORT.md) · [v16前端](reproduction/improvement_v16_20261016_01/index.html) · [执行前协议](reproduction/improvement_v16_20261016_01/protocols/PLAN.md) · [v15原报告](reproduction/improvement_v15_20261016_01/REPORT.md)

早期数据、训练和历史运行步骤保留在[此前指南原样快照](reproduction/improvement_v16_20261016_01/before/PROGRAM_GUIDE.md)，请按对应版本使用。
