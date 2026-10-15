# v13：侧倒箱沿、斜靠支撑与有界重规划

v13完成：开发236/240；全新60起点确认v6 445/480、v12 437/480、v13 448/480。未通过本轮对照采用门槛，保留为候选；主要配对区间未完全高于零，不能宣称总体成功率改善。

[整体评估](REPORT.md) · [前端](index.html) · [执行前协议](protocols/PLAN.md) · [图表解释](FIGURE_GUIDE.md) · [执行台账](analysis/execution_inventory.json)。

全部旧代码、权重和结果保留；400步、20Hz、D2、最多两次抓取尝试不变。没有泛化训练和论文正文。v13继承v5—v12，迁移时需要完整项目。

在robot_can根目录的PyCharm PowerShell终端启动：

```powershell
Set-Location 'C:\Users\Livio\Desktop\robot_can'
& '.\.venv\Scripts\python.exe' -m http.server 8766 --bind 127.0.0.1
```

保持终端运行，打开 **http://127.0.0.1:8766/** 。根入口自动跳到v13。已有该端口服务时直接打开，不必重复启动。关闭服务按`Ctrl+C`；另用端口时命令和网址一起修改。


直达：http://127.0.0.1:8766/reproduction/improvement_v13_20261016_01/index.html 。

## 只读完整性检查

```powershell
& '.\.venv\Scripts\python.exe' -X utf8 -B reproduction/improvement_v13_20261016_01/verify_integrity.py
```

只读检查本轮前10982个登记路径、9份活动文档的原样备份、当前交付清单及开发/确认冻结锁。不会训练或仿真。旧verify绑定当时根文档，可能因后续授权更新而提示差异；不要改旧manifest或删除结果绕过检查。


## 重复复核（会运行仿真）

运行器拒绝覆盖已有目录。使用新阶段名，例如：

```powershell
& '.\.venv\Scripts\python.exe' -X utf8 -B reproduction/improvement_v13_20261016_01/run_batch.py --stage smoke_repeat_01 --jobs protocols/smoke_jobs.json --workers 4
& '.\.venv\Scripts\python.exe' -X utf8 -B reproduction/improvement_v13_20261016_01/verify_run.py --stage smoke_repeat_01
& '.\.venv\Scripts\python.exe' -X utf8 -B reproduction/improvement_v13_20261016_01/verify_physics.py --stage smoke_repeat_01
```

开发与确认的已锁任务分别是`protocols/dev_jobs.json`和`protocols/confirmation_jobs.json`。重复旧确认起点只算复核，不能算另一批独立实验。不要覆盖旧分析、源码快照、清单或冻结锁。

五张图有600dpi PNG、PDF/SVG、CSV和来源SHA256；两个20fps视频逐保存动作物理回放。验证记录在`validation/`。中断的smoke_b及所有未通过迭代保留，不计作完整阶段通过证据。旧写作ZIP不含本轮，请使用同步后的完整仓库。
