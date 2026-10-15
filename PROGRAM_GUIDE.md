# 项目运行指南（当前入口）

v14 两轮小测试共64次；最终 v13 / T / C / v14 为6/8、6/8、5/8、6/8。门槛未通过，未采用；未运行大规模消融、240次开发或全新起点确认。

## 环境

使用项目现有 `.venv\Scripts\python.exe`。在PyCharm将项目解释器设置为该文件；沿用现有依赖和数据路径，不需要为本轮重新安装或替换权重。

## 启动展示

```powershell
Set-Location 'C:\Users\Livio\Desktop\robot_can'
& '.\.venv\Scripts\python.exe' -m http.server 8766 --bind 127.0.0.1 --directory 'C:\Users\Livio\Desktop\robot_can'
```

打开完整地址：**http://127.0.0.1:8766/reproduction/improvement_v14_20261016_01/index.html** 。如果8766服务已经运行，直接打开即可；终端保持运行，Ctrl+C关闭。


## 实验与检查

本轮控制代码在 `reproduction/improvement_v14_20261016_01/recovery/`，运行器、逐步动作审计、物理回放和完整度检查均在同一目录。[本轮README](reproduction/improvement_v14_20261016_01/README.md)提供只读核验和新目录复跑命令。[执行前协议](reproduction/improvement_v14_20261016_01/protocols/PLAN.md)定义阶段门槛。

`protocols/pilot_jobs.json`代表已准备的372次作业，当前并未运行。开发冻结脚本会拒绝未过关的小测试；不要绕过它启动开发或独立确认。全新起点必须在版本冻结后生成，本轮尚未生成。

[本轮检查报告](reproduction/improvement_v14_20261016_01/REPORT.md) · [v14前端](reproduction/improvement_v14_20261016_01/index.html) · [执行前协议](reproduction/improvement_v14_20261016_01/protocols/PLAN.md) · [v13原报告](reproduction/improvement_v13_20261016_01/REPORT.md)

早期数据、训练和历史复现实验说明保留在[此前完整指南快照](reproduction/improvement_v14_20261016_01/before/PROGRAM_GUIDE.md)。它们对应各自冻结版本，请按原版本目录运行，不能与v14的64次诊断混为同一实验。
