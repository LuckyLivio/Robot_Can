# 清理候选与保留理由

本轮删除0个文件。以下为可评估的临时副本，不是实验资产；所有旧代码、权重、结果保留。

| 路径（项目根下） | MiB | 处理状态 |
|---|---:|---|
| `reproduction/portable_delivery_20261015_01/builds/release_01` | 53.37 | 保留，待清理条件满足 |
| `reproduction/portable_delivery_20261015_01/builds/TRANSFER_DRAFT_01` | 273.88 | 保留，待清理条件满足 |
| `reproduction/portable_delivery_20261015_01/validation/relocated/run_01` | 32.59 | 保留，待清理条件满足 |
| `reproduction/portable_delivery_20261015_01/validation/relocated/run_02` | 32.59 | 保留，待清理条件满足 |

合计 **392.44 MiB**。旧run_02曾承担8767服务；本轮检查未观察到8767监听，仍应在实际清理时重新检查占用、release_02/最终迁移包完整性与路径范围。

前次自动审批拒绝过这四处临时清理与服务交接的组合命令，工具仅返回“blocked by policy”，未给详细原因。本轮没有重试删除，也没有换工具绕过。

项目之外/环境内部不清理。项目字节缓存5个文件约38 KiB可再生；Git临时对象曾记录约2.68 MiB，必须在无Git写入时单独确认，不递归删除objects、dangling恢复对象或整个.git。

原始JSONL约8.26 GiB是主要体积来源，权重315种内容/684路径、冻结快照、旧WRITING/FULL ZIP、652份gzip、v7中断记录及失败视频都不能按“重复/失败”批量删除。当前`.venv`继续保留。新图表目录的输入快照、逐图CSV和PDF渲染检查图是可追溯交付的一部分，不属于这次临时清理名单。
