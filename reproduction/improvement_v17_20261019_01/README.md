# v17：路径搜索、箱沿收敛和持物稳定性对照

本目录保存 v17 候选的独立实现、预先锁定协议、实际运行结果和审计回执。旧代码、权重和实验结果保留在原路径。结果结论以 [REPORT.md](REPORT.md) 和 [SUMMARY.json](SUMMARY.json) 为准；本目录不包含论文正文，也没有新增训练。

## 入口与证据

| 路径 | 内容 |
| --- | --- |
| [index.html](index.html) | 本轮前端结果页、图表与原始证据链接 |
| [REPORT.md](REPORT.md) / [SUMMARY.json](SUMMARY.json) | 实际完成数、阶段门槛、失败原因、适用范围和后续建议 |
| [protocols/PLAN.md](protocols/PLAN.md) | 冻结前登记的版本、阈值、样本与阶段门槛 |
| [recovery/](recovery/) | 本轮控制器、路径搜索和位姿证书；不替换旧实现 |
| [smoke_a/](smoke_a/) | 七组小测试的实际记录、逐步轨迹和运行时源码快照 |
| [analysis/](analysis/) | 静态测试、机制检查、动作复核、物理复核和只读轨迹诊断 |
| [figures/](figures/) | 600 dpi PNG、矢量 PDF/SVG、对应 CSV 和来源哈希目录 |
| [validation/](validation/) | 图表、链接、文档及最终交付核验回执 |
| [../improvement_v16_20261016_01/](../improvement_v16_20261016_01/) | 原 v16 结果；仍保留原版本与证据 |

七组为 v15、v16、仅预算 C、v16 + 路径修复、v16 + 箱沿修复、v16 + 持物修复、完整 v17。每组 8 个标准条件与 1 个预算专用配置；预算配置复用 6000005 起点，因此不能把 9 个配置计作 9 个独立起点。小测试门槛通过后才可启动 658 次已知条件消融、720 回合开发对照及冻结后的 1440 回合独立确认，实际执行状态见报告。

## 在 PyCharm 的 PowerShell 终端查看前端

从项目根目录启动静态服务器；这个命令会持续占用当前终端，停止时按 Ctrl+C：

```powershell
Set-Location 'C:\Users\Livio\Desktop\robot_can'
& '.\.venv\Scripts\python.exe' -m http.server 8766 --bind 127.0.0.1 --directory 'C:\Users\Livio\Desktop\robot_can'
```

浏览器打开完整地址：

<http://127.0.0.1:8766/reproduction/improvement_v17_20261019_01/index.html>

如果 8766 已有本项目服务器运行，直接打开上面的完整地址。最终交付的根入口 `/` 会跳转当前报告；推荐使用上面的完整版本地址，确保查看的是 v17。

## 只读核验已完成交付

最终封存后，在项目根目录运行以下命令。它检查历史文件保留、当前交付哈希、冻结源码、各阶段审计和完成计数；不会运行新实验、改写文件或安装依赖。

```powershell
Set-Location 'C:\Users\Livio\Desktop\robot_can'
& '.\.venv\Scripts\python.exe' -X utf8 -B 'reproduction\improvement_v17_20261019_01\verify_integrity.py'
```

`passed: true` 表示交付一致性检查通过，不等于候选效果门槛通过。效果、动作一致性、物理复核、静态几何证书的范围分别记录，不能互相替代。
