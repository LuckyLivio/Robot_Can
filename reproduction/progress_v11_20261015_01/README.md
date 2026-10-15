# v11成果展示

在项目根目录用PowerShell启动，已有8766服务时直接打开网页即可：

```powershell
Set-Location 'C:\Users\Livio\Desktop\robot_can'
& '.\.venv\Scripts\python.exe' -m http.server 8766 --bind 127.0.0.1
```

打开 <http://127.0.0.1:8766/>，根入口跳转到本页。直接地址：<http://127.0.0.1:8766/reproduction/progress_v11_20261015_01/demo/index.html>。

本页新增：最终消融与240回合开发表；v10/v11箱沿同状态20 fps视频；四组原始曲线；持物等待退步的原始曲线与解释。v11局部修复成立，但开发235/240低于历史v6的236/240，不替换v5，也没有进入独立确认。

新视频是已知诊断BC k=2、噪声0.05、demo_6000005。v10失败400步，v11成功380步；421帧、20 fps、21.05秒，成功后保持终点，未平滑或插值动作。根据保存动作重新仿真，逐步核对状态、奖励、成功标记；不新增统计样本。视频生成入口 `render_edge.py` 禁止覆盖已有输出，核验见 `edge_replay_validation.json`。

下方原始BC/Full/Plain视频仍固定seed17，不含后续恢复；v6/v8历史恢复视频含Full三个训练种子与BC案例，v4/v5日志动画保持历史标签。不要把不同版本或不同起点拼成一个对照。

实验报告：[v11报告](../improvement_v11_20261015_01/REPORT.md)。页面语法、链接、资源哈希与HTTP检查见 `frontend_validation.json`；实际浏览器显示和播放检查见 `browser_validation.json`，截图为 `frontend_preview.jpg`。

未新增训练、模型权重或论文正文，旧前端保持原路径不变。
