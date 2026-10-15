# 同一起点机器人对比演示

版本：2026-10-12。当前[新版演示页面](reproduction/review_20261012_01/demo/index.html)包含六段三栏同步视频：左BC k=2、中Full、右Plain（去排序），世界模型均固定为原登记中的第一个训练种子17。全部使用冻结权重，未重新训练。

## 在PyCharm终端打开

```powershell
Set-Location 'C:\Users\Livio\Desktop\robot_can'
& '.\.venv\Scripts\python.exe' -X utf8 -B -u '.\reproduction\review_20261012_01\serve_demo.py'
```

若上一版8766服务仍在运行，可直接打开下面的新版地址，无需重复启动。否则运行上述命令并保持终端打开，在浏览器打开 [本机演示页](http://127.0.0.1:8766/reproduction/review_20261012_01/demo/index.html)。停止服务按Ctrl+C。只绑定127.0.0.1；不对外发布。端口被占用时加`--port 8767`，并使用对应地址。

也可直接用浏览器打开项目内`reproduction/review_20261012_01/demo/index.html`，或播放下面的MP4；不需要再次采集、训练或评估。视频为H.264，已烧录中文说明，离开网页也保留方法、时间和成功状态标注。

## 新版界面

浅色Apple风格布局：先选“干净执行/加入扰动”，再选“共同成功/Full独胜/共同未完成”。支持播放暂停、0.5×/1×/2×速度、下载与原生全屏；下方是全部确认结果与证据说明，手机端自动单列。封面来自视频第一帧。

新版只改展示，6段原视频的字节和统计不变；[上一版页面](reproduction/release_20261012_01/demo/index.html)完整保留。核验见[本轮验收](reproduction/review_20261012_01/review_validation.json)。

## 案例规则与结果

本轮确认结果已知后，为说明行为而选例：分别在干净和噪声0.05条件，选“共同成功”“Full成功且BC/Plain未完成”“共同未完成”三类中的最小起点编号；固定种子17，不寻找最好种子。规则在渲染前保存于[demo_design.json](reproduction/release_20261012_01/demo_design.json)。这些案例并非随机代表样本，也不是新的独立确认，不计入成功率表。

| 条件/类别 | 起点 | BC k=2 | Full s17 | Plain s17 | 视频 |
| --- | --- | --- | --- | --- | --- |
| 干净/共同成功 | demo_1000001 | 成功95步 | 成功95步 | 成功95步 | [播放](reproduction/release_20261012_01/demo/videos/clean_shared_success.mp4) |
| 干净/Full独胜 | demo_1000026 | 400步未完成 | 成功133步 | 400步未完成 | [播放](reproduction/release_20261012_01/demo/videos/clean_full_only_success.mp4) |
| 干净/共同失败 | demo_1000000 | 400步未完成 | 400步未完成 | 400步未完成 | [播放](reproduction/release_20261012_01/demo/videos/clean_shared_failure.mp4) |
| 加噪/共同成功 | demo_1000002 | 成功110步 | 成功109步 | 成功110步 | [播放](reproduction/release_20261012_01/demo/videos/noise005_shared_success.mp4) |
| 加噪/Full独胜 | demo_1000011 | 400步未完成 | 成功165步 | 400步未完成 | [播放](reproduction/release_20261012_01/demo/videos/noise005_full_only_success.mp4) |
| 加噪/共同失败 | demo_1000000 | 400步未完成 | 400步未完成 | 400步未完成 | [播放](reproduction/release_20261012_01/demo/videos/noise005_shared_failure.mp4) |

## 建议的两分钟讲解

1. 展示共同成功：“左边是强基线。它不使用世界模型，但已经能完成很多起点，不能把它省略。”
2. 播放干净Full独胜：“三种方法从完全相同的状态开始。Full按预测后果选择候选，在这个案例里完成放置；这是说明案例，不代表所有起点。”
3. 播放加噪Full独胜：“三个方法共享相同的逐步位置动作噪声。画面上的k表示当前新提交的候选，真正执行仍要经过两步队列。”
4. 展示共同失败：“模型与门限仍存在失效场景；失败表示400步内未完成任务。评分门限不是通用安全保证。”
5. 回到[总体统计](RESULTS.md)：“60个新起点、全部三个种子的Full平均成功率为干净90.0%、加噪86.1%，观察到正向趋势。分条件区间仍接触零，排序模块的独立增益未确立。”

输入包含物体真值，是低维状态仿真。视频图像只作展示，没有作为控制策略输入；不能称为已完成纯视觉或真机实验。

## 画面怎样保证可比

每例三个方法共享保存的XML和初始状态、执行噪声、20Hz控制、D=2、400步预算与同一agentview相机。相机每2步取一帧，以10fps播放，保持仿真时间尺度；每段结尾加1秒停帧。较早成功的方法停在成功帧，其他方法继续，不能分别加速或循环。

先使用不变的确认评估核心重新生成完整动作记录，核对原始回合除计时外的全部结果字段；再重放**实际加噪且截断后的执行动作**。每一步核对观测、阶段奖励和成功标记。渲染器对求解器warmstart造成的舍入变化通过保存/恢复该辅助数组消除，每次渲染验证物理/控制器签名不变。

证据：[结果复跑核验](reproduction/release_20261012_01/demo/trace_validation.json)、[回放核验](reproduction/release_20261012_01/demo/replay_validation.json)、[媒体清单](reproduction/release_20261012_01/demo/media_manifest.json)、[最终验收](reproduction/release_20261012_01/release_validation.json)。分镜截图在同目录`posters/`，可用于答辩。

## 代码与保护

上一版release目录的`make_demo.py --phase traces`执行案例复核，`--phase render`生成视频。当前输出已存在时拒绝覆盖，不要删除旧文件来强行重跑。若另做演示版本，应先复制脚本到新的`reproduction/<新目录>`并单独登记输出和规则，保留本轮证据。冻结检查使用[PROGRAM_GUIDE中的命令](PROGRAM_GUIDE.md)。
