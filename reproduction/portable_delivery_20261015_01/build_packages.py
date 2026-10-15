"""Build new portable demo and v6-v11 writing addendum; never overwrite a build."""
from pathlib import Path
from urllib.parse import quote, urlsplit, unquote
import argparse
import csv
import html
import json
import re
import shutil
import zipfile
from portable import digest, verify

RUN = Path(__file__).resolve().parent
ROOT = RUN.parents[1]
FRONT = ROOT / 'reproduction/progress_v11_20261015_01/demo'
CSS = '''*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:#f5f5f7;color:#1d1d1f;font:16px/1.65 -apple-system,BlinkMacSystemFont,"Segoe UI","Microsoft YaHei",sans-serif}a{color:#0066cc;text-decoration:none}a:hover{text-decoration:underline}nav{padding:18px max(5vw,20px);background:#fff;border-bottom:1px solid #ddd;display:flex;gap:24px;flex-wrap:wrap}main{max-width:1120px;margin:auto;padding:56px 24px}h1{font-size:clamp(32px,5vw,60px);line-height:1.15;letter-spacing:-2px}h2{margin-top:44px;font-size:28px}small,.muted{color:#62626b}.eyebrow{text-transform:uppercase;letter-spacing:2px;font-size:12px;color:#5d6470}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:18px}.card{background:#fff;padding:24px;border-radius:22px;border:1px solid #e8e8ed}.number{font-size:38px;font-weight:650;line-height:1.3}video{width:100%;background:#111;border-radius:18px;margin-top:20px}select{width:100%;font:inherit;padding:14px;border:1px solid #ccc;border-radius:12px;background:#fff}img{width:100%;height:auto;border-radius:14px}table{border-collapse:collapse;width:100%;font-size:14px}th,td{text-align:left;border-bottom:1px solid #ddd;padding:12px;vertical-align:top}.scroll{overflow:auto}code,pre{font-family:Consolas,monospace;background:#eeeef1}pre{padding:18px;border-radius:12px;overflow:auto;white-space:pre-wrap;overflow-wrap:anywhere}footer{padding:30px 0;color:#666;font-size:13px}.notice{border-left:3px solid #0066cc;padding:8px 18px;margin:24px 0}details{background:#fff;padding:18px;border-radius:14px;margin:12px 0}button{font:inherit;border:0;background:#0066cc;color:#fff;padding:10px 18px;border-radius:12px;cursor:pointer}.doc{white-space:pre-wrap;overflow-wrap:anywhere;line-height:1.85}.sources{font-size:13px}'''


def write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf8')


def page(title, body):
    return '<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>' + html.escape(title) + '</title><link rel="icon" href="data:,"><link rel="stylesheet" href="style.css"><nav><b>CAN LAB / PORTABLE</b><a href="index.html">交付首页</a><a href="README.md">使用说明</a><a href="PACKAGE_MANIFEST.json">文件与来源清单</a></nav><main>' + body + '</main></html>'


def js_data(name):
    return json.loads((FRONT / name).read_text(encoding='utf8').split('=', 1)[1].strip().rstrip(';'))


def copy_source(package, source, manifest, expected):
    source = source.resolve()
    rel = source.relative_to(ROOT).as_posix()
    if rel not in expected or digest(source) != expected[rel]:
        raise ValueError('Source is not the frozen version: ' + rel)
    dest = package / 'snapshot' / rel
    if not dest.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, dest)
        manifest.append({'source_path': rel, 'package_path': 'snapshot/' + rel, 'sha256': expected[rel]})
    return 'snapshot/' + rel


def make_demo(package, source_rows, frozen):
    cases = []
    raw = js_data('data.js')['cases']
    for c in raw:
        cases.append({'id': c['id'], 'label': '原始 BC / Full / Plain · seed17 · ' + ('噪声0.05' if c['condition'] != 'clean' else '干净') + ' · ' + c['label'],
                      'video': c['video'], 'poster': c['poster'], 'results': c['results'],
                      'note': '无共享恢复；起点 ' + c['state_name'] + '。事后选取的说明案例，不是新的统计样本。'})
    for c in js_data('recovery-media.js'):
        cases.append({'id': c['id'], 'label': 'v6 / v8 恢复对比 · ' + c['label'],
                      'video': c['video'], 'poster': c['poster'], 'results': c['results'],
                      'note': '起点 ' + c['demo'] + '；保留已知成功及失败。Full包含17、23、41三个训练种子。'})
    cases.append({'id': 'v11-edge', 'label': 'v10 / v11 箱沿对比 · BC k=2 · 噪声0.05',
                  'video': 'v11_edge20/bc_wall_edge.mp4', 'poster': 'v11_edge20/poster.png',
                  'results': {'v10': {'success': False, 'steps': 400}, 'v11': {'success': True, 'steps': 380}},
                  'note': 'demo_6000005，已知诊断案例；局部成功不代表开发集整体改善。'})
    for c in cases:
        for key in ['video', 'poster']:
            c[key] = copy_source(package, FRONT / c[key], source_rows, frozen['files'])
    plots = []
    for file, caption in [('wall_edge_comparison.png', '箱沿四组原始轨迹：v11在380步完成，其余三组到400步未完成。'),
                          ('development_regression.png', '开发退步：已经持物，仍等待支撑，未转入搬运。')]:
        p = ROOT / 'reproduction/improvement_v11_20261015_01/analysis' / file
        plots.append((copy_source(package, p, source_rows, frozen['files']), caption))
    receipt_path = ROOT / 'reproduction/improvement_v11_20261015_01/analysis/final_receipt.json'
    receipt = json.loads(receipt_path.read_text())
    evidence = copy_source(package, receipt_path, source_rows, frozen['files'])
    if receipt['development']['v11_success'] != 235 or receipt['adopted']:
        raise ValueError('Unexpected frozen conclusion')
    group_rows = ''.join(f"<tr><td>{g['condition']}</td><td>{g['v6_success']}/30</td><td>{g['v11_success']}/30</td></tr>" for g in receipt['development']['groups'])
    body = '''<p class="eyebrow">FROZEN EVIDENCE / 2026.10.15</p><h1>把成果带走。<br>让证据留在每一步。</h1><p class="muted">无需 PyTorch 或 GPU 的便携展示：11段已有对比视频、最新开发结果、两组原始轨迹图。纯静态页面，不运行机器人仿真。</p><div class="cards"><article class="card"><small>冻结主版本 / v5</small><div class="number">464 / 480</div><p>独立原生确认，60个起点 × 8条件。</p></article><article class="card"><small>最新候选 / v11</small><div class="number">235 / 240</div><p>开发低于v6的236/240，未采用。</p></article><article class="card"><small>全部案例都有版本标签</small><div class="number">11 段</div><p>包含成功、失败，以及三个Full训练种子。</p></article></div><p class="notice">视频用于解释机制。不同版本、不同起点不可拼成同一组统计；世界模型优势仍有条件限制。v12尚未实施。</p><h2>机器人对比</h2><label for="case">选择实验与案例</label><select id="case"></select><video id="player" controls playsinline preload="metadata"></video><p id="caption"></p><p id="outcome"></p><a id="download" download>下载当前原视频</a><h2>开发结果 · 同30个起点</h2><div class="scroll"><table><thead><tr><th>条件</th><th>历史v6</th><th>v11</th></tr></thead><tbody>''' + group_rows + '</tbody></table></div><p><a href="' + evidence + '">查看冻结结果来源</a></p><h2>原始轨迹与未解决问题</h2>'
    body += ''.join(f'<figure><a href="{p}"><img src="{p}" loading="lazy" alt="{html.escape(c)}"></a><figcaption>{c}</figcaption></figure>' for p, c in plots)
    body += '<footer>来源提交 ' + frozen['source_commit'][:12] + '。视频与图片按原字节复制；未插帧、未平滑动作、未新增实验。</footer><script src="media-data.js"></script><script src="app.js"></script>'
    write(package / 'index.html', page('CAN LAB · 便携展示', body))
    write(package / 'media-data.js', 'const CASES=' + json.dumps(cases, ensure_ascii=False) + ';')
    write(package / 'app.js', '''const select=document.querySelector('#case'),player=document.querySelector('#player');
for(const c of CASES){const o=document.createElement('option');o.value=c.id;o.textContent=c.label;select.append(o);}
function show(){const c=CASES.find(x=>x.id===select.value);player.pause();player.src=c.video;player.poster=c.poster;player.load();document.querySelector('#caption').textContent=c.note;document.querySelector('#outcome').textContent=Object.entries(c.results).map(([m,r])=>`${m}：${r.success?'成功':'未完成'}，${r.steps}步`).join(' / ');document.querySelector('#download').href=c.video;}
select.addEventListener('change',show);show();
player.addEventListener('error',()=>{document.querySelector('#caption').textContent+=' 视频读取失败，请运行 portable.py verify 并检查本地服务。';});''')
    return cases


def make_writing(package, source_rows, frozen):
    selected = set()
    for rel in frozen['files']:
        p = Path(rel)
        if re.match(r'reproduction/improvement_v(?:6|7|8|9|10|11)_20261015_01/', rel):
            tail = p.parts[2:]
            if any(x in tail for x in ['before', 'source', '__pycache__']):
                continue
            if p.suffix in {'.md', '.csv', '.png', '.svg', '.pdf'} or p.name == 'result.json':
                selected.add(rel)
            elif p.suffix == '.json' and ('analysis' in tail or 'protocols' in tail or len(tail) == 1 or p.name in {'jobs.json', 'completed.json'}):
                if 'manifest' not in p.name and 'inventory' not in p.name:
                    selected.add(rel)
    for name in ['REPORT.md', 'CHECKLIST.md', 'CLEANUP.md', 'IMPROVEMENT_PLAN.md', 'environment_and_inference.json', 'environment-freeze-current.txt', 'statistics_validation.json']:
        selected.add('reproduction/project_audit_20261015_01/' + name)
    selected |= {'CONTRIBUTIONS.md', 'RESULTS.md', 'THESIS_OUTLINE.md', 'RELATED_WORK.md', 'ENVIRONMENT_GUIDE.md'}
    for rel in sorted(selected):
        copy_source(package, ROOT / rel, source_rows, frozen['files'])
    video = copy_source(package, FRONT / 'v11_edge20/bc_wall_edge.mp4', source_rows, frozen['files'])
    (package / 'reports').mkdir()
    report_links = []
    missing = []
    for rel in sorted(selected):
        if not rel.endswith('.md'):
            continue
        source = ROOT / rel
        text = source.read_text(encoding='utf-8-sig')
        def replace_link(match):
            label, target = match.groups()
            parsed = urlsplit(target)
            if parsed.scheme:
                url = target
            else:
                candidate = (source.parent / unquote(parsed.path)).resolve()
                if not candidate.is_relative_to(ROOT):
                    return html.escape(match.group(0))
                target_rel = candidate.relative_to(ROOT).as_posix()
                if (package / 'snapshot' / target_rel).is_file():
                    url = '../snapshot/' + quote(target_rel)
                else:
                    url = 'https://github.com/LuckyLivio/Robot_can/blob/' + frozen['source_commit'] + '/' + quote(target_rel)
                    missing.append({'report': rel, 'source_reference': target_rel, 'online_url': url})
            return '<a href="' + html.escape(url, quote=True) + '">' + html.escape(label) + '</a>'
        # Escaped preformatted source: preserves all numbers/tables; only links become clickable.
        chunks = []
        pos = 0
        for match in re.finditer(r'\[([^\]]+)\]\(([^)]+)\)', text):
            chunks += [html.escape(text[pos:match.start()]), replace_link(match)]
            pos = match.end()
        chunks.append(html.escape(text[pos:]))
        title = next((line[2:].strip() for line in text.splitlines() if line.startswith('# ')), source.stem)
        name = str(len(report_links) + 1).zfill(3) + '.html'
        body = '<p><a href="../index.html">← 增补资料首页</a></p><h1 style="font-size:32px">' + html.escape(title) + '</h1><p class="notice">这是原文阅读视图。包内来源直接打开；未收入的引用指向固定提交的GitHub，需联网。原始Markdown逐字节保留。</p><div class="doc">' + ''.join(chunks) + '</div>'
        write(package / 'reports' / name, page(title, body).replace('href="style.css"', 'href="../style.css"').replace('href="index.html"', 'href="../index.html"').replace('href="README.md"', 'href="../README.md"').replace('href="PACKAGE_MANIFEST.json"', 'href="../PACKAGE_MANIFEST.json"'))
        report_links.append((rel, title, name))
    result_rows = []
    for rel in sorted(selected):
        if Path(rel).name != 'result.json':
            continue
        data = json.loads((ROOT / rel).read_text())
        if not isinstance(data, dict) or 'records' not in data:
            continue
        result_rows.append({'source': rel, 'status': data.get('status', 'historical_unspecified'),
                            'episodes_saved': len(data['records']), 'successes_saved': sum(bool(r['success']) for r in data['records']),
                            'eligible_complete_batch': data.get('status') == 'complete', 'sha256': frozen['files'][rel]})
    with (package / 'CANDIDATE_RESULT_INDEX.csv').open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(result_rows[0])); writer.writeheader(); writer.writerows(result_rows)
    write(package / 'ONLINE_REFERENCES.json', json.dumps(missing, ensure_ascii=False, indent=2))
    main_reports = [(r, t, n) for r, t, n in report_links if Path(r).name in {'REPORT.md', 'CHECKLIST.md'} or '/' not in r]
    def report_order(item):
        rel = item[0]
        version = re.search(r'improvement_v(\d+)_', rel)
        return (0, rel) if '/' not in rel else ((1, int(version.group(1))) if version else (2, rel))
    main_reports.sort(key=report_order)
    links = ''.join(f'<li><a href="reports/{n}">{html.escape(t)}</a><br><small>{html.escape(r)}</small></li>' for r, t, n in main_reports)
    all_reports = ''.join(f'<li><a href="reports/{n}">{html.escape(r)}</a></li>' for r, t, n in report_links)
    plots = ''.join(f'<figure><img src="snapshot/reproduction/improvement_v11_20261015_01/analysis/{n}" alt="{c}"><figcaption>{c}</figcaption></figure>' for n, c in [('wall_edge_comparison.png','箱沿四组轨迹'),('development_regression.png','已持物等待导致开发退步')])
    body = '<p class="eyebrow">WRITING ADDENDUM / V6—V11</p><h1>材料更新。<br>结论保持准确。</h1><p>与旧 WRITING 包一起使用：旧包负责原世界模型与v5主线，本包补齐v6—v11及全项目审查。没有论文正文，没有新增实验。</p><p class="notice">v5仍为主版本。v11开发235/240，未采用；不要把候选案例或负结果省略，也不要把不同批次直接合并。</p><h2>优先阅读</h2><ul>' + links + '</ul><h2>可直接取用的数据</h2><p><a href="CANDIDATE_RESULT_INDEX.csv">全部候选结果索引CSV</a> · <a href="SOURCE_MANIFEST.json">原文件路径与SHA</a> · <a href="ONLINE_REFERENCES.json">未收录的在线引用清单</a></p><p>snapshot保留已选报告、逐回合结果JSON、分析表、图、配置和校验凭据；不包含全部原始JSONL、模型或仿真数据，不是完整复现实验包。3份中断running结果保留并标记，不能当完整批次。</p><h2>v11原始图与视频</h2>' + plots + f'<video controls preload="metadata" src="{video}"></video><details><summary>所有文档阅读视图</summary><ul>' + all_reports + '</ul></details><footer>资料冻结于提交 ' + frozen['source_commit'] + '。新设备实际安装/仿真验收尚待完成。</footer>'
    write(package / 'index.html', page('CAN LAB · 写作资料增补', body))
    return {'results': len(result_rows), 'reports': len(report_links), 'online_references': len(missing)}


def build(profile, dest, frozen):
    dest.mkdir(parents=True, exist_ok=False)
    rows = []
    metadata = make_demo(dest, rows, frozen) if profile == 'demo' else make_writing(dest, rows, frozen)
    write(dest / 'style.css', CSS)
    shutil.copy2(RUN / 'portable.py', dest / 'portable.py')
    write(dest / 'README.md', '# ' + ('便携展示包' if profile == 'demo' else 'v6—v11写作增补包') + '\n\n解压后在本文件所在目录打开终端。只需Python 3.10或更新版本的标准库，无需安装仿真依赖。\n\n```powershell\npython -B portable.py verify\npython -B portable.py serve --port 8767 --open\n```\n\n浏览器访问 http://127.0.0.1:8767/ 。不要只复制index.html，也不要直接双击HTML作为完整验收。若8767占用，改为8768并使用对应地址。Ctrl+C停止。\n\n第一次运行不带参数只显示帮助，不启动实验。\n\n' + ('本包有11段已有视频（原始三方法6段、v6/v8恢复4段、v10/v11箱沿1段），视频中方法/版本/起点分别标注。' if profile == 'demo' else '配合旧THESIS_HANDOFF_20261015_WRITING.zip使用；主文数据仍在旧包，本包是增补。包内未收录的原文链接在阅读视图指向固定GitHub提交，需要联网。') + '\n\n这是本机移位验证的交付包，不表示另一台电脑已验收。重跑机器人需完整仓库和仿真环境。\n')
    write(dest / 'SOURCE_MANIFEST.json', json.dumps({'source_commit': frozen['source_commit'], 'files': rows}, ensure_ascii=False, indent=2))
    files = [{'path': p.relative_to(dest).as_posix(), 'bytes': p.stat().st_size, 'sha256': digest(p)} for p in sorted(dest.rglob('*')) if p.is_file()]
    manifest = {'profile': profile, 'source_commit': frozen['source_commit'], 'files': files,
                'source_assets': len(rows), 'new_experiment_episodes': 0,
                'requires': ['Python >= 3.10 standard library', 'modern browser'],
                'scope': 'Portable selected presentation' if profile == 'demo' else 'Addendum; requires old WRITING package for the original main study'}
    write(dest / 'PACKAGE_MANIFEST.json', json.dumps(manifest, ensure_ascii=False, indent=2))
    verified = verify(dest)
    archive = dest.with_suffix('.zip')
    with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for p in sorted(dest.rglob('*')):
            if p.is_file():
                z.write(p, dest.name + '/' + p.relative_to(dest).as_posix())
    with zipfile.ZipFile(archive) as z:
        bad = z.testzip()
        if bad:
            raise ValueError('ZIP CRC failed: ' + bad)
    write(archive.with_suffix('.zip.sha256'), digest(archive) + '  ' + archive.name + '\n')
    return {**verified, 'bytes_uncompressed': sum(x['bytes'] for x in files), 'zip': archive.name,
            'zip_bytes': archive.stat().st_size, 'zip_sha256': digest(archive), 'source_assets': len(rows),
            'metadata': {'videos': len(metadata)} if profile == 'demo' else metadata}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', required=True, type=Path, help='A new directory; existing paths are refused.')
    args = p.parse_args()
    output = args.output.resolve()
    if output.is_relative_to(ROOT) and not output.is_relative_to(RUN / 'builds'):
        raise ValueError('Repository builds must be under portable_delivery/builds')
    output.mkdir(parents=True, exist_ok=False)
    frozen = json.loads((RUN / 'baseline.json').read_text())
    records = [build('demo', output / 'CAN_LAB_DEMO', frozen), build('writing', output / 'CAN_LAB_WRITING_ADDENDUM', frozen)]
    write(output / 'BUILD_RECEIPT.json', json.dumps({'passed': True, 'source_commit': frozen['source_commit'], 'packages': records}, ensure_ascii=False, indent=2))
    print(json.dumps({'passed': True, 'output': str(output), 'packages': records}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
