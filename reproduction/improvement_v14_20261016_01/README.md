# v14：接近跟踪与下降回正诊断

**本轮未通过小测试门槛，保留为诊断版本。** 第二轮 v13 / 仅 T / 仅 C / v14 分别为 6/8、6/8、5/8、6/8。斜靠案例首次接近、抓取及抬升改善，但搬运与箱沿路径仍未完成。旧代码、权重和结果保留；不替换正式成果。

详细结果见 [REPORT.md](REPORT.md)，执行约束见 [protocols/PLAN.md](protocols/PLAN.md)，网页见 [index.html](index.html)。两轮完整小测试共 64 次；没有进行 372 次大规模消融、240 次开发对照或独立确认，也没有训练。

## 启动前端（PyCharm PowerShell）

从项目根目录运行；如果 8766 已有本项目服务，直接打开下面完整地址即可。

```powershell
Set-Location 'C:\Users\Livio\Desktop\robot_can'
& '.\.venv\Scripts\python.exe' -m http.server 8766 --bind 127.0.0.1 --directory 'C:\Users\Livio\Desktop\robot_can'
```

打开 **http://127.0.0.1:8766/reproduction/improvement_v14_20261016_01/index.html** 。服务器终端需保持运行；Ctrl+C 关闭。旧 v13 页面仍在 http://127.0.0.1:8766/reproduction/improvement_v13_20261016_01/index.html 。

## 本目录内容

| 路径 | 内容 |
|---|---|
| recovery/ | v14 继承控制器；T 跟踪，C 回正 |
| protocols/ | 执行前方案、预先生成的实验作业；作业文件不等于已运行 |
| smoke_a/、smoke_b/ | 两轮各 32 次真实执行，包含源码快照、逐步轨迹和失败结果 |
| analysis/ | 配对表、动作/物理回放、机制测试、失败定位 |
| figures/ | 原始表格支持的 600 dpi PNG、矢量 PDF/SVG、CSV |
| demo/ | 两个预先指定目标的 v13/v14 同起点物理回放视频，两者均如实显示未完成 |
| before/、before_manifest.json | 旧文件校验及九个入口文档的原样备份 |
| validation/ | 图表、视频、页面、文档验证 |

## 核验与自行复跑

最终交付封存后可只读核验：

```powershell
& '.\.venv\Scripts\python.exe' -X utf8 -B reproduction/improvement_v14_20261016_01/verify_integrity.py
```

如需自行复跑小测试，必须用新目录名，避免覆盖；这会再产生 32 次闭环执行，不属于本次封存结果。

```powershell
$v14Stage = 'smoke_manual_' + (Get-Date -Format 'yyyyMMdd_HHmmss')
& '.\.venv\Scripts\python.exe' -X utf8 -B -u reproduction/improvement_v14_20261016_01/run_batch.py --stage $v14Stage --jobs protocols/smoke_jobs.json --workers 4
& '.\.venv\Scripts\python.exe' -X utf8 -B reproduction/improvement_v14_20261016_01/analyze.py --stage $v14Stage --save
& '.\.venv\Scripts\python.exe' -X utf8 -B reproduction/improvement_v14_20261016_01/verify_run.py --stage $v14Stage
& '.\.venv\Scripts\python.exe' -X utf8 -B reproduction/improvement_v14_20261016_01/verify_physics.py --stage $v14Stage
```

开发冻结和确认脚本有强制门槛。当前门槛失败，不应跳过检查启动大批实验，也不要把准备好的确认脚本当作已取得新确认结果。

所有统计仅来自明确列出的已知诊断条件。闭环执行、保存输入回放和物理重放分别计数。几何检查不等价于全臂安全证明；当前状态属于特权观测，不能直接外推到真实相机或实机。
