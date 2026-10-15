# 当前项目状态

v14 两轮小测试共64次；最终 v13 / T / C / v14 为6/8、6/8、5/8、6/8。门槛未通过，未采用；未运行大规模消融、240次开发或全新起点确认。

[本轮检查报告](reproduction/improvement_v14_20261016_01/REPORT.md) · [v14前端](reproduction/improvement_v14_20261016_01/index.html) · [执行前协议](reproduction/improvement_v14_20261016_01/protocols/PLAN.md) · [v13原报告](reproduction/improvement_v13_20261016_01/REPORT.md)

| 项目 | 当前证据 |
|---|---|
| v14小测试与局部四组消融 | smoke_a、smoke_b共64次，完整保留 |
| 动作与物理核验 | 64次、22,174步，精确通过；不新增统计样本 |
| 新代码机制检查 | 25项，88项继承配置不变 |
| 372次大规模消融 | 门槛未过，未运行 |
| 240次开发对照 | 未运行 |
| 全新起点确认 | 未运行，起点尚未生成 |
| 采用 / 冻结用于确认 | 未采用 / 未冻结 |
| 泛化训练、论文正文 | 本轮均未进行 |

下一步应先验证持物搬运姿态与分段箱沿路径，保持400步及原保护。回正模块必须消除额外耗时造成的旧成功退步。详见报告第6节。

历史状态：[v13报告](reproduction/improvement_v13_20261016_01/REPORT.md)；[此前状态原样快照](reproduction/improvement_v14_20261016_01/before/STATUS.md)。历史主成果不因本轮局部改善而自动替换。
