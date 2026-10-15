# 项目运行指南（当前入口）

**v15已完成45次五组小测试：v14 / 仅搬运A / 仅分段B / 仅预算C / 完整v15为6/9、3/9、6/9、7/9、4/9。小测试未通过，v15未采用。**

沿用现有 `.venv\Scripts\python.exe`，在PyCharm选择它作为解释器。权重与依赖无需替换。

## 启动前端

```powershell
Set-Location 'C:\Users\Livio\Desktop\robot_can'
& '.\.venv\Scripts\python.exe' -m http.server 8766 --bind 127.0.0.1 --directory 'C:\Users\Livio\Desktop\robot_can'
```

打开完整地址：**http://127.0.0.1:8766/reproduction/improvement_v15_20261016_01/index.html** 。已有8766服务时直接打开，无需再启动；终端保持运行，Ctrl+C停止。


## 核验与实验

预算模块单独运行救回时间不足案例且未损失旧成功；搬运模块的局部IK误拒和转向耗时导致三个旧成功退步，两个主难例仍未完成。因此不替换既有正式成果，不进入470次消融、两版各240次开发或1440次全新起点确认。

[本轮README](reproduction/improvement_v15_20261016_01/README.md)提供只读核验命令。[执行前协议](reproduction/improvement_v15_20261016_01/protocols/PLAN.md)定义阶段顺序。`protocols/pilot_jobs.json`是已准备的470次作业，不是实验结果。开发冻结脚本同时检查结果、机制、保存输入和物理核验；本轮小测试失败，不能绕过它生成开发或确认结果。

[本轮完整报告](reproduction/improvement_v15_20261016_01/REPORT.md) · [v15前端](reproduction/improvement_v15_20261016_01/index.html) · [执行前协议](reproduction/improvement_v15_20261016_01/protocols/PLAN.md) · [v14原报告](reproduction/improvement_v14_20261016_01/REPORT.md)

早期数据、训练和历史运行步骤保留在[此前指南原样快照](reproduction/improvement_v15_20261016_01/before/PROGRAM_GUIDE.md)，请按对应版本使用。
