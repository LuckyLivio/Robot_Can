# 小测试C：记录格式修复

smoke_b部分任务在写日志时中断：新增 `retreat_already_elevated` 使用了numpy.bool_，标准JSON无法序列化。已将其显式转换为Python bool，并补记录可序列化检查；决策数值和阈值未改。

保留smoke_b全部日志、部分轨迹、已完成任务和源码快照。该批不视为完成，也不进入采用门槛。以新目录smoke_c完整重跑24次；后续门槛核验使用smoke_c和mechanisms_c。smoke_a及其预算失败仍保留。
