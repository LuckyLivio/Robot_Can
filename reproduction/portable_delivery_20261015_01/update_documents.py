"""Update only the five backed-up active documents and add the delivery portal."""
from pathlib import Path
import json
import shutil
from portable import digest
from build_packages import CSS, write, page

RUN = Path(__file__).resolve().parent
ROOT = RUN.parents[1]


def main():
    frozen = json.loads((RUN / 'baseline.json').read_text())
    for rel in frozen['authorized_documents']:
        if digest(ROOT / rel) != frozen['files'][rel]:
            raise ValueError('Document already changed: ' + rel)
    docs = {rel: (ROOT / rel).read_text(encoding='utf8') for rel in frozen['authorized_documents']}
    docs['README.md'] = '> 跨设备交付已整理：[使用说明](reproduction/portable_delivery_20261015_01/README.md) · [下载与验收页面](reproduction/portable_delivery_20261015_01/index.html)。含独立展示包、v6—v11增补与三个ZIP的迁移文件夹；第二台电脑实际验收仍待完成。\n\n' + docs['README.md']
    docs['README.md'] = docs['README.md'].replace('reproduction\\project_audit_20261015_01\\verify.py', 'reproduction\\portable_delivery_20261015_01\\launcher.py verify')
    docs['README.md'] = docs['README.md'].replace('10,146 个路径', '10,230 个路径')
    docs['README.md'] = docs['README.md'].replace('本轮代码、结果与前端交付清单', '本轮交付工具、文档与打包凭据清单')
    docs['STATUS.md'] = docs['STATUS.md'].replace('本轮全仓文件/数据/权重/视频/统计检查通过', '上一轮全仓文件/数据/权重/视频/统计检查通过')
    docs['STATUS.md'] = docs['STATUS.md'].replace('；最新迁移增补包', '')
    docs['STATUS.md'] = docs['STATUS.md'].replace('reproduction/project_audit_20261015_01/verify.py', 'reproduction/portable_delivery_20261015_01/verify_delivery.py')
    docs['STATUS.md'] += '\n跨设备交付P1-A：本机侧已完成独立展示包（11段视频）、v6—v11写作增补、三ZIP集中迁移文件夹和可移植复核/重跑入口；干净标准库环境、中文路径移位、HTTP及浏览器播放检查通过。第二台电脑安装与物理运行尚未执行；v12控制修复未开始。[交付报告](reproduction/portable_delivery_20261015_01/REPORT.md)。\n'
    docs['PROGRAM_GUIDE.md'] = docs['PROGRAM_GUIDE.md'].replace('reproduction\\project_audit_20261015_01\\verify.py', 'reproduction\\portable_delivery_20261015_01\\launcher.py verify').replace('审查前10,146个登记文件', '交付整理前10,230个登记文件')
    docs['PROGRAM_GUIDE.md'] += '\n## 换设备或只展示\n\n[便携交付说明](reproduction/portable_delivery_20261015_01/README.md)提供展示包、v6—v11写作增补和三个ZIP的集中迁移目录。解压展示包后，在CAN_LAB_DEMO目录执行 `python -B portable.py serve --port 8767 --open`，首页为 http://127.0.0.1:8767/ 。无需安装仿真依赖。\n\n新重跑包装入口在 `reproduction/portable_delivery_20261015_01/launcher.py`：无参数只显示帮助，rerun默认只列计划，必须显式实验名、新output及--execute才会仿真；源代码/权重/数据先做589项哈希核验。历史jobs保留原样。第二台电脑按[清单](reproduction/portable_delivery_20261015_01/TARGET_DEVICE_CHECKLIST.md)逐项验收。\n'
    docs['THESIS_HANDOFF_LATEST.md'] = '''# 当前论文资料交接说明（2026-10-15交付更新）

跨设备资料已集中到 `reproduction/portable_delivery_20261015_01/builds/TRANSFER_TO_NEW_DEVICE/`，可直接复制整个文件夹。[交付说明](reproduction/portable_delivery_20261015_01/README.md) · [验收页面](reproduction/portable_delivery_20261015_01/index.html) · [目标设备清单](reproduction/portable_delivery_20261015_01/TARGET_DEVICE_CHECKLIST.md)。

三个ZIP合计约273.9 MiB：旧WRITING主线包252.6 MiB、新写作增补4.8 MiB、新展示包16.5 MiB。旧ZIP原位置保留，新文件夹中是经哈希核对的副本。

- 旧THESIS_HANDOFF_20261015及WRITING/FULL ZIP对应c8bbe86：原世界模型与v5主线、40张表、19组图和提纲，不含v6—v11。
- 新CAN_LAB_WRITING_ADDENDUM对应fad3100：v6—v11各报告、逐回合结果、表、图、协议/校验资料、v11视频及全项目审查。含29份文档阅读视图和706份候选结果JSON索引；中断记录保留并标记，不把它们计为完整批次。
- 新CAN_LAB_DEMO为独立静态展示：11段已有视频、两张v11原始轨迹图、八种开发条件。无需PyTorch/GPU，使用包内portable.py在8767启动。

主线仍是v5；v11开发235/240，未采用。写作先读[最新贡献](CONTRIBUTIONS.md)、[当前结果](RESULTS.md)、[当前提纲](THESIS_OUTLINE.md)，再使用[旧详细提纲](THESIS_HANDOFF_20261015/01_outline/THESIS_OUTLINE_REVISED.md)和各批次数据。

生成ZIP和解压副本不随Git克隆提供，避免反复提交大副本。克隆后可用新build_packages.py重建两个新包；旧WRITING ZIP需单独复制，旧包652份gzip也不随克隆提供。完整原始轨迹仍在仓库原路径。

本机干净标准库环境、移位中文路径、文件/ZIP与前端检查已通过；第二台电脑实际验收未执行。没有论文正文、新训练或新仿真实验，尚未实施v12控制修复。
'''
    docs['WORKSPACE/index.html'] = docs['WORKSPACE/index.html'].replace('<section><h2>当前审查与版本</h2>', '<section><h2>跨设备交付</h2><p>独立展示、v6—v11写作增补与三个ZIP的集中迁移目录已准备；第二台电脑实际验收待完成。</p><a href="../reproduction/portable_delivery_20261015_01/index.html">打开下载与验收页面</a> · <a href="../reproduction/portable_delivery_20261015_01/README.md">启动和复核命令</a></section><section><h2>当前审查与版本</h2>')
    for rel, text in docs.items():
        write(ROOT / rel, text)
    write(RUN / 'style.css', CSS)
    body = '''<p class="eyebrow">DELIVERY / 2026.10.15</p><h1>换一台电脑。<br>带走完整的论据。</h1><p class="muted">本机交付整理已完成。代码、权重、历史结果保留；没有新增训练、实验或论文正文。</p><div class="cards"><article class="card"><small>只展示</small><div class="number">16.5 MiB</div><p>11段视频、两张轨迹图、最新开发结果，无需GPU。</p><a href="builds/release_02/CAN_LAB_DEMO.zip" download>下载展示包</a> · <a href="builds/release_02/CAN_LAB_DEMO/index.html">预览</a></article><article class="card"><small>最新写作增补</small><div class="number">4.8 MiB</div><p>v6—v11报告、分析数据、图、协议与审查凭据。</p><a href="builds/release_02/CAN_LAB_WRITING_ADDENDUM.zip" download>下载增补包</a> · <a href="builds/release_02/CAN_LAB_WRITING_ADDENDUM/index.html">阅读资料</a></article><article class="card"><small>三个包，一次带走</small><div class="number">273.9 MiB</div><p>旧主线WRITING + 新增补 + 独立展示，附校验工具。</p><a href="builds/TRANSFER_TO_NEW_DEVICE/">打开迁移文件夹</a></article></div><p class="notice">v5仍是冻结主版本；v11未采用。第二台电脑尚未实测，本页不会把本机移位测试称作跨设备复现成功。</p><h2>启动方式</h2><p>解压展示包后，在CAN_LAB_DEMO目录终端执行：</p><pre>python -B portable.py verify
python -B portable.py serve --port 8767 --open</pre><p>打开 http://127.0.0.1:8767/ 。服务根目录就是展示首页。已有服务时直接打开，端口占用则改8768。</p><h2>已完成与仍待完成</h2><div class="scroll"><table><tr><th>检查</th><th>当前状态</th></tr><tr><td>ZIP CRC、SHA与解压内容</td><td>通过；原始包保留</td></tr><tr><td>中文/空格路径 + 新标准库环境</td><td>通过；未安装PyTorch</td></tr><tr><td>11段视频浏览器加载与开始播放</td><td>通过；没有控制台错误</td></tr><tr><td>当前环境7个模型前向与pip check</td><td>通过；没有创建仿真环境</td></tr><tr><td>重跑包装入口</td><td>默认帮助/只列计划、589项输入核对；本轮未执行仿真</td></tr><tr><td>第二台电脑安装、播放与物理一致性</td><td>待目标设备完成</td></tr><tr><td>v12持物等待修复</td><td>下一算法阶段，尚未实施</td></tr></table></div><h2>资料与操作清单</h2><p><a href="REPORT.md">本轮报告</a> · <a href="README.md">完整命令</a> · <a href="TARGET_DEVICE_CHECKLIST.md">目标设备验收表</a> · <a href="REPRODUCTION_MANIFEST.json">复核/重跑输入清单</a> · <a href="BUILD_RECEIPT.json">构建与ZIP哈希</a></p><footer>本页下载链接对应本机已生成文件。GitHub克隆后需按README运行构建脚本；旧主线WRITING ZIP需单独提供。生成包不重复提交到Git。</footer>'''
    # Portal uses its tracked build receipt rather than a package manifest.
    write(RUN / 'index.html', page('CAN LAB · 跨设备交付', body).replace('href="PACKAGE_MANIFEST.json"', 'href="BUILD_RECEIPT.json"'))
    manifests = RUN / 'package_manifests'
    manifests.mkdir(exist_ok=False)
    for kind, name in [('demo', 'CAN_LAB_DEMO'), ('writing', 'CAN_LAB_WRITING_ADDENDUM')]:
        shutil.copy2(RUN / 'builds/release_02' / name / 'PACKAGE_MANIFEST.json', manifests / (kind + '.json'))
    shutil.copy2(RUN / 'builds/TRANSFER_TO_NEW_DEVICE/TRANSFER_MANIFEST.json', manifests / 'transfer.json')
    print(json.dumps({'active_documents_updated': len(docs), 'old_experiment_changes': 0}))


if __name__ == '__main__':
    main()
