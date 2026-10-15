# 2026-10-15 实验进展与回放前端

从项目根目录执行：

```powershell
& '.\.venv\Scripts\python.exe' -m http.server 8766 --bind 127.0.0.1
```

打开 **http://127.0.0.1:8766/**，或 http://127.0.0.1:8766/reproduction/progress_20261015_01/demo/index.html 。已有服务运行时直接刷新页面即可。

页面包括冻结的世界模型和 v5 主结果、v6/v7/v8 候选状态、原始三方法视频、v6/v8 恢复对比和历史日志动画。主版本与未采用候选明确分开。

## 视频与数据

- 六段原始视频重绘为 20 fps，逐控制步渲染，不使用动作插帧。见 [原始回放验证](original_20fps_validation.json)。
- 四段新恢复视频包含 Full 的 seed17、23、41 与一个 BC 退步案例。每段内部同起点；跨选项起点不一定相同。见 [候选回放验证](candidate_replay_validation.json)。
- 成功后保持真实终点，结尾增加 1 秒停帧；不增加实验样本。
- 历史轨迹动画提供可关闭的**游标**插值，原始折线与数值不变。真实运动振荡不会被视频重绘或游标插值删除。
- 已冻结结果不通过浏览器修改。`update_progress.py` 从报告 JSON 生成状态，并为脚本/样式加内容哈希，页面每 30 秒读取状态文件。

## 版本状态

v5 主线结果保留；v6 开发集未提高；v7、v8 合用诊断均为 30/37，低于 v6 31/37，因此均未采用。v8 两轮共 370 回合，不是 370 个独立起点。

静态资源、实际浏览器交互和媒体帧率检查记录见 [frontend_validation_final.json](frontend_validation_final.json)，实际浏览器检查另存于 [browser_validation.json](browser_validation.json)。旧 `consolidation_20261012_01` 页面及视频未改写。
