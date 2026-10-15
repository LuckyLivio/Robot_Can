# v12：抓持等待修复实验

**实验已完成，v12未通过独立确认的采用门槛，不替换正式版本。** 已知持物等待由400步失败变为264步完成；开发236/240与v6持平。全新60起点、八条件确认中，v12为465/480，v6为473/480，救回1次、退步9次。详见[整体报告](REPORT.md)。

共1323次评估执行；400步、D2、最多两次恢复保持不变。先小测试/消融，再240开发，通过后冻结并完成新起点确认。旧代码、权重和结果保留；没有泛化训练或论文正文。

- [执行前计划](protocols/PLAN.md)
- [本轮前端](index.html)
- [机制检查](analysis/mechanisms_a.json)
- [独立确认及统计](analysis/confirmation.json)
- [四张图与原始绘图数据](figures/CATALOG.json)
- [历史完整前端](../progress_v11_20261015_01/demo/index.html)

在项目根目录启动前端（若8766已经运行，直接打开链接）：

```powershell
& .\.venv\Scripts\python.exe -m http.server 8766 --bind 127.0.0.1
```

打开 http://127.0.0.1:8766/reproduction/improvement_v12_20261015_01/index.html 。

重跑阶段必须使用新目录名；run_batch拒绝覆盖已存在阶段：

```powershell
& .\.venv\Scripts\python.exe -X utf8 -B reproduction/improvement_v12_20261015_01/run_batch.py --stage smoke_repeat_01 --jobs protocols/smoke_jobs.json --workers 3
```

只读核验原资产、活动文档备份、本轮交付和冻结源文件：

```powershell
& .\.venv\Scripts\python.exe -X utf8 -B reproduction/improvement_v12_20261015_01/verify_integrity.py
```

脚本仅支持本项目环境。历史路径是继承依赖，不删除或移动。确认阶段在开发门槛通过后才生成起点及任务；本轮确认已完成，不能覆盖或将其用于调参后继续称作独立确认。旧跨设备ZIP不含v12；迁移本轮时同时保留完整Git项目依赖。
