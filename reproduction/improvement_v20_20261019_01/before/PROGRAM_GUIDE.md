# 项目运行指南（当前入口）

**v19 已完成八组共72回合小测试与消融，未通过预定门槛，未采用。**

实际 v17 3/9；实际 v18 2/9；原预算候选 7/9；仅 A 衔接窗口 2/9；仅 B 候选限额 2/9；仅 C 积分制动 2/9；A+B 2/9；完整 v19 2/9。

每组9个条件共用8个不同物理起点：8个标准条件与1个复用6000005起点的clearance专用配置。A/B/C/AB均加在完整v18上，原预算候选保护不同，仅作成功数参考。72回合不是72个独立起点，本组困难案例成功率不能当作整个项目总体成功率。

保留400步、D2 FIFO、原保护阈值与成功定义。752次扩展诊断、三版各240次开发对照（合计720）及1440次独立确认均未运行，未生成新确认起点；保留v18、预算候选及所有旧代码、权重、结果。未做泛化训练，未写论文。

[本轮完整报告](reproduction/improvement_v19_20261019_01/REPORT.md) · [v19 前端](reproduction/improvement_v19_20261019_01/index.html) · [正式协议](reproduction/improvement_v19_20261019_01/protocols/PLAN.md) · [v18 原报告](reproduction/improvement_v18_20261019_01/REPORT.md)

在PyCharm中沿用 `.venv\Scripts\python.exe` 解释器。

## 启动前端

```powershell
Set-Location 'C:\Users\Livio\Desktop\robot_can'
& '.\.venv\Scripts\python.exe' -m http.server 8766 --bind 127.0.0.1 --directory 'C:\Users\Livio\Desktop\robot_can'
```

打开完整地址：**http://127.0.0.1:8766/reproduction/improvement_v19_20261019_01/index.html** 。已有8766服务时直接打开，不重复启动；服务终端保持运行，用Ctrl+C停止。

## 核验和实验

[本轮README](reproduction/improvement_v19_20261019_01/README.md)提供核验命令。[协议](reproduction/improvement_v19_20261019_01/protocols/PLAN.md)锁定门槛；登记作业不代表执行。小测试未通过，不启动开发或独立确认。

早期训练、数据和历史命令保留在[此前指南快照](reproduction/improvement_v19_20261019_01/before/PROGRAM_GUIDE.md)，按对应版本使用。
