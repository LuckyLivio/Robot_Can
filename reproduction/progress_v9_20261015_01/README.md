# v9 进展展示页

在项目根目录启动 HTTP 服务，打开 <http://127.0.0.1:8766/> 或直接打开 `demo/index.html` 对应 HTTP 地址。根入口已指向本页，旧前端目录保留。

本页新增 v9 最终五路小测试与耗时摘要，明确未采用、未进入开发对照，并链接坐标系修复记录和完整报告。`update_progress.py` 从实验记录生成 `progress.json`，不会触发实验、训练或后台任务。

原始 BC/Full/Plain 视频及 v6/v8 恢复视频继续引用上一版 20 fps 文件，不重编码、不修改动作。页面注明它们是历史演示，不是 v9 视频。日志游标插值仍可关闭。

当前研究结果：[v9 REPORT](../improvement_v9_20261015_01/REPORT.md)。历史视频核验：[20 fps原视频](../progress_20261015_01/original_20fps_validation.json)、[v6/v8恢复视频](../progress_20261015_01/candidate_replay_validation.json)。
