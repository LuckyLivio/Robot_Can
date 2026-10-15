# v10 实验进展页

在项目根目录运行：

```powershell
& '.\.venv\Scripts\python.exe' -m http.server 8766 --bind 127.0.0.1
```

打开 <http://127.0.0.1:8766/> 或 <http://127.0.0.1:8766/reproduction/progress_v10_20261015_01/demo/index.html>。

首页呈现v10负结果、同起点原始轨迹对比和证据链接。四组各30/37，未进入240回合开发。机器人视频来自历史原始/恢复演示，明确标注旧版本；没有把旧视频冒充v10。

`update_progress.py` 从保存结果生成状态，更新JS/CSS内容哈希；不要把它当作实验执行器。`verify_frontend.py` 检查链接、语法、历史视频校验和HTTP状态；浏览器截图与交互核查单列。
