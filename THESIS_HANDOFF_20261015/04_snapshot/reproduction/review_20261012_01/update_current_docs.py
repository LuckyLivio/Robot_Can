"""Apply review corrections to current entry docs; archived editions stay intact."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];RUN=Path(__file__).resolve().parent
def update(name,fn):
    p=ROOT/name
    assert p.read_bytes()==(RUN/'previous_documents'/name).read_bytes(),name
    p.write_text(fn(p.read_text(encoding='utf-8')),encoding='utf-8')
def readme(s):
    s=s.replace('## 当前入口','## 当前入口\n\n- [PROJECT_AUDIT](PROJECT_AUDIT.md)：2026-10-12全项目复核、未完成项及本科毕业设计适用性。\n- [新版机器人演示](reproduction/review_20261012_01/demo/index.html)：Apple风格改版，沿用冻结视频与结果。')
    s=s.replace('新演示位于 `reproduction/release_20261012_01/demo/`。','原视频和上一版页面位于 `reproduction/release_20261012_01/demo/`；当前前端位于 `reproduction/review_20261012_01/demo/`，引用同一批视频。')
    s+='\n2026-10-12本次复核保存了修改前的11份根文档，见[本轮文档归档](reproduction/review_20261012_01/previous_documents/)。本轮不写论文正文，当前保护与验收入口见[运行指南](PROGRAM_GUIDE.md)。\n'
    return s
def program(s):
    s=s.replace(".\\reproduction\\release_20261012_01\\verify_release.py",".\\reproduction\\review_20261012_01\\verify_project.py")
    s=s.replace('该命令核对冻结文件、演示及文档验收清单，不重新训练。','该命令核对当前文档/前端与全部原有非根文档文件，不重新训练。上一版release验收脚本绑定上一版根文档，保留为历史入口；当前文档已获准修订，使用这里的新命令。')
    s=s.replace('视频使用当前机器已有FFmpeg和Pillow/OpenCV，不改变训练依赖。','视频使用当前机器已有FFmpeg和Pillow/OpenCV，不改变训练依赖。\n\n本次实测[pip/CUDA/版本](reproduction/review_20261012_01/environment.json)通过，另存[完整安装版本快照](reproduction/review_20261012_01/environment-freeze.txt)。根目录`requirements-repro.txt`是旧安装建议，其torch 2.9.1注释不代表冻结实验实际版本；当前实际为2.14.1+cu130。不要为了对齐旧注释降级现有环境。版本快照不是跨机器离线安装包，Windows DLL/WGL兼容配置见历史`data/windows_compatibility.json`和`setup_windows.py`；现环境已配置，本轮未执行安装或补丁。')
    s=s.replace('[演示页面](reproduction/release_20261012_01/demo/index.html)','[新版演示页面](reproduction/review_20261012_01/demo/index.html)')
    s=s.replace('## 3. 直接看当前成果','根目录共有33份Python脚本。上表是当前主线，完整逐项用途、历史运行证据和未完成范围见[全项目复核](PROJECT_AUDIT.md)及[模块清单](reproduction/review_20261012_01/module_inventory.json)。旧探索脚本的默认参数不是本轮锁定配置，部分旧脚本会写回固定路径，不要用“全部逐个执行”代替当前复核。\n\n## 3. 直接看当前成果')
    return s
def demo(s):
    s=s.replace('[演示页面](reproduction/release_20261012_01/demo/index.html)','[新版演示页面](reproduction/review_20261012_01/demo/index.html)')
    s=s.replace(".\\reproduction\\release_20261012_01\\serve_demo.py",".\\reproduction\\review_20261012_01\\serve_demo.py")
    s=s.replace('http://127.0.0.1:8766/reproduction/release_20261012_01/demo/index.html','http://127.0.0.1:8766/reproduction/review_20261012_01/demo/index.html')
    s=s.replace('终端保持运行，在浏览器打开','若上一版8766服务仍在运行，可直接打开下面的新版地址，无需重复启动。否则运行上述命令并保持终端打开，在浏览器打开')
    s=s.replace('项目内`reproduction/release_20261012_01/demo/index.html`','项目内`reproduction/review_20261012_01/demo/index.html`')
    s=s.replace('## 案例规则与结果','## 新版界面\n\n浅色Apple风格布局：先选“干净执行/加入扰动”，再选“共同成功/Full独胜/共同未完成”。支持播放暂停、0.5×/1×/2×速度、下载与原生全屏；下方是全部确认结果与证据说明，手机端自动单列。封面来自视频第一帧。\n\n新版只改展示，6段原视频的字节和统计不变；[上一版页面](reproduction/release_20261012_01/demo/index.html)完整保留。核验见[本轮验收](reproduction/review_20261012_01/review_validation.json)。\n\n## 案例规则与结果')
    s=s.replace('`make_demo.py --phase traces`执行案例复核','上一版release目录的`make_demo.py --phase traces`执行案例复核')
    return s
def status(s):
    s=s.replace('## 已完成','当前总核对见[PROJECT_AUDIT](PROJECT_AUDIT.md)。本轮明确不写论文正文。\n\n## 已完成')
    s=s.replace('## 结论边界','- 全项目存量检查：33根脚本分类、116源文件语法检查、36份NPZ有限值检查；15训练任务、60开发评估、14确认评估完成凭据齐全，9项确认配对区间独立复算一致。\n- 新版Apple风格演示前端，引用原视频；第一帧封面、条件/案例切换、对照统计与证据区。\n\n## 结论边界')
    s=s.replace('本轮是提纲和演示整理，不生成或宣称完成全文。','本轮是项目/文档复核与前端改版，不生成或宣称完成全文。')
    s=s.replace('[release验收](reproduction/release_20261012_01/release_validation.json)','[最新验收](reproduction/review_20261012_01/review_validation.json)')
    s+='\n尚未完整完成的原协议条目包括持续性弱基线、全面oracle闭环、H=1与候选数量系统扫描。queue_v2等已有历史探索结果，但未全部纳入当前三种子/独立确认；详见完整度报告，不把它们误记为缺文件或已完成正式确认。\n'
    return s
def plan(s):
    s=s.replace('## 下一阶段','## 当前复核与后续可选阶段\n\n2026-10-12按用户要求完成全项目审计和前端改版，本轮不写论文正文。主线未发现漏跑，无需因文档或前端修改重跑训练/确认。遗漏与原计划边界见[完整度报告](PROJECT_AUDIT.md)。下面是后续可能的交付工作，不代表本轮已执行。')
    return s
for name,fn in [('README.md',readme),('PROGRAM_GUIDE.md',program),('DEMO_GUIDE.md',demo),('STATUS.md',status),('REPRODUCTION_PLAN.md',plan)]:update(name,fn)
print('Updated 5 current documents; archived originals and historical releases unchanged.')
