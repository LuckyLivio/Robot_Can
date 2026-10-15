# v12：抓持等待修复实验

保持旧代码、权重和结果。400步、D2、最多两次恢复。先小测试/消融，过门槛再240开发，达标冻结后新起点确认。没有泛化训练或论文正文。

- [执行前计划](protocols/PLAN.md)
- [本轮前端](index.html)
- [机制检查](analysis/mechanisms_a.json)
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

脚本仅支持本项目环境。历史路径是继承依赖，不删除或移动。确认阶段只有门槛通过后才生成起点及任务；不能跳过freeze与起点检查。
