# 前端与机器人演示

```powershell
Set-Location 'C:\Users\Livio\Desktop\robot_can'
& '.\.venv\Scripts\python.exe' -m http.server 8766 --bind 127.0.0.1 --directory 'C:\Users\Livio\Desktop\robot_can'
```

打开完整地址：**http://127.0.0.1:8766/reproduction/improvement_v14_20261016_01/index.html** 。如果8766服务已经运行，直接打开即可；终端保持运行，Ctrl+C关闭。


建议演示顺序：先看“未通过门槛”及四组结果，再播放斜靠和箱沿两段同起点对比，最后查看原始证据与改进计划。两段都是预先指定的已知难例，均未在400步完成；它们解释失败机制，不能充当总体成功率证据。

每个视频20fps对应20Hz控制，421帧、21.05秒；逐步重放实际动作，末尾保持终点，无平滑插帧。页面支持浏览器原生播放、暂停与进度定位。演示前端不启动训练或新物理控制实验。

[本轮检查报告](reproduction/improvement_v14_20261016_01/REPORT.md) · [v14前端](reproduction/improvement_v14_20261016_01/index.html) · [执行前协议](reproduction/improvement_v14_20261016_01/protocols/PLAN.md) · [v13原报告](reproduction/improvement_v13_20261016_01/REPORT.md)

历史演示说明：[此前DEMO_GUIDE快照](reproduction/improvement_v14_20261016_01/before/DEMO_GUIDE.md)。
