# v13：侧倒箱沿、斜靠支撑与有界重规划

本轮进行中，阶段状态以[前端](index.html)和analysis中的已完成记录为准。400步、20Hz、D2、两次抓取尝试保持不变，旧代码、权重、结果保留。无泛化训练和论文正文。

- [执行前协议与门槛](protocols/PLAN.md)
- [最终小测试机制核验](analysis/mechanisms_e.json)
- [v12历史结果](../improvement_v12_20261015_01/REPORT.md)

在robot_can根目录的PyCharm PowerShell终端启动：

```powershell
& .\.venv\Scripts\python.exe -m http.server 8766 --bind 127.0.0.1
```

打开 http://127.0.0.1:8766/reproduction/improvement_v13_20261016_01/index.html 。已有该端口服务可直接打开。

运行器拒绝覆盖已有阶段。若以后复核，在新阶段名下运行：

```powershell
& .\.venv\Scripts\python.exe -X utf8 -B reproduction/improvement_v13_20261016_01/run_batch.py --stage smoke_repeat_01 --jobs protocols/smoke_jobs.json --workers 4
```

已有起点重复运行属于复核，不是新的独立确认。控制器依赖冻结v5—v12模块和既有权重，迁移时需完整项目，旧ZIP不含本轮。
