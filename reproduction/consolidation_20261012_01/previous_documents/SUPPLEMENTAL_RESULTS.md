# 最新补充实验与整体评估

日期：2026-10-12。本次指定的持续性弱预测基线、真值候选排序、H=1（另加H=3）、候选数量实验已全部完成：**88个执行任务、900个回合**。旧权重、结果、代码、文档与演示均保留，没有写论文。

完整报告：[补充实验报告与整体评估](reproduction/extensions_20261012_01/REPORT.md)。

真值排序无噪声25/30、加噪25/30；BC k=2为25/30、24/30。即使真实短期后果可用，当前规划器仍会失败。持续性、H=1、K=1均回退至k=2；H=3改选很少；K=8没有稳定改善。学习动力学的短期位置预测优于持续性预测，但不能据此宣称完整控制方法稳定显著胜出。

演示“共同未完成”表示三个方法在该回合400步内未完成机器人任务，不是实验漏跑。无噪声示例抓住后未搬运成功，Full/Plain全程回退k=2；加噪示例第105步起失抓，未恢复。

当前低维仿真主线适合作为本科毕业设计的实现与实验分析基础；方法显著优越性、纯视觉/真机/多任务、正式论文与学校审核仍是不同层面的要求。详见报告中的证据与边界。

此前根目录PROJECT_AUDIT、STATUS、PROTOCOL是本轮补跑前的保留快照。四类缺项的最新状态以本页和本轮报告为准。

[只读验收脚本](reproduction/extensions_20261012_01/verify.py) · [最终哈希验收](reproduction/extensions_20261012_01/final_validation.json) · [主结果图](reproduction/extensions_20261012_01/analysis/controls.png) · [时域/候选图](reproduction/extensions_20261012_01/analysis/sensitivity.png) · [预测误差图](reproduction/extensions_20261012_01/analysis/prediction.png)
