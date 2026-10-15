"""Copy three verified ZIPs into one new transfer folder; keep all originals."""
from pathlib import Path
import argparse
import json
import shutil
import zipfile
from portable import digest

RUN = Path(__file__).resolve().parent
ROOT = RUN.parents[1]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build', required=True, type=Path)
    p.add_argument('--base-writing-zip', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    args = p.parse_args()
    output = args.output.resolve()
    if output.is_relative_to(ROOT) and not output.is_relative_to(RUN / 'builds'):
        raise ValueError('Repository transfer folders must be in delivery/builds')
    sources = [args.base_writing_zip.resolve(), args.build.resolve() / 'CAN_LAB_DEMO.zip',
               args.build.resolve() / 'CAN_LAB_WRITING_ADDENDUM.zip']
    for src in sources:
        if not src.is_file():
            raise FileNotFoundError(src)
    output.mkdir(parents=True, exist_ok=False)
    rows = []
    for src in sources:
        with zipfile.ZipFile(src) as z:
            if z.testzip():
                raise ValueError('Archive CRC failure: ' + src.name)
        sha = digest(src)
        sidecar = src.with_suffix('.zip.sha256')
        if sidecar.exists() and sidecar.read_text().split()[0] != sha:
            raise ValueError('Archive sidecar differs: ' + src.name)
        target = output / src.name
        shutil.copy2(src, target)
        if digest(target) != sha:
            raise ValueError('Copy differs')
        rows.append({'path': target.name, 'bytes': target.stat().st_size, 'sha256': sha})
    (output / 'TRANSFER_MANIFEST.json').write_text(json.dumps({'files': rows}, indent=2), encoding='utf8')
    script = '''from pathlib import Path
import hashlib,json
root=Path(__file__).resolve().parent
rows=json.loads((root/'TRANSFER_MANIFEST.json').read_text())['files']
for r in rows:
    p=(root/r['path']).resolve()
    if not p.is_relative_to(root) or p.stat().st_size!=r['bytes']:raise ValueError(r['path'])
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
    if h.hexdigest()!=r['sha256']:raise ValueError(r['path'])
print(json.dumps({'passed':True,'archives':len(rows)}))
'''
    (output / 'verify_transfer.py').write_text(script, encoding='utf8')
    (output / '先读我.txt').write_text('三个包一起带走，原始包保留。\n\n1. 终端执行 python -B verify_transfer.py。\n2. 分别解压，不覆盖合并。\n3. 进入CAN_LAB_DEMO，执行 python -B portable.py verify，然后 python -B portable.py serve --port 8767 --open。\n4. 浏览器地址 http://127.0.0.1:8767/。Ctrl+C停止。\n5. 写作先读CAN_LAB_WRITING_ADDENDUM，用同样命令在8768启动；原世界模型/v5数据在THESIS_HANDOFF_20261015。\n\n旧写作包对应c8bbe86；新增补来源fad3100，包含v6—v11与审查。v5仍为采用主版本，v11未采用。本次没有论文正文、新训练或新实验。\n展示只需Python3.10或更新版本标准库。目标电脑实际验收仍需你在该电脑完成，不复制.venv。\n', encoding='utf8')
    result = {'passed': True, 'archives': rows, 'total_zip_bytes': sum(r['bytes'] for r in rows),
              'originals_preserved': True, 'output': str(output)}
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
