"""Whole tracked-repository inventory, syntax and reference audit. No experiments."""
from pathlib import Path
from collections import Counter,defaultdict
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlsplit,unquote
import ast,csv,hashlib,json,os,re,shutil,subprocess,datetime
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1]
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
    return h.hexdigest()
def tracked():return subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode('utf8').split('\0')[:-1]
def dump(name,obj):
    with (RUN/name).open('x',encoding='utf8') as f:json.dump(obj,f,ensure_ascii=False,indent=2)
def main():
    paths=tracked();print('Tracked paths',len(paths),flush=True)
    def item(rel):
        p=ROOT/rel
        return {'path':rel,'bytes':p.stat().st_size,'sha256':sha(p),'suffix':p.suffix.lower(),'top':p.parts[len(ROOT.parts)]}
    with ThreadPoolExecutor(max_workers=4) as pool:rows=list(pool.map(item,paths))
    dump('before_manifest.json',{r['path']:r['sha256'] for r in rows})
    with (RUN/'FILE_INVENTORY.csv').open('x',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    backups=[]
    for rel in paths:
        if ('/' not in rel and rel.endswith('.md')) or rel.startswith('WORKSPACE/') or rel=='index.html':
            dest=RUN/'before'/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/rel,dest);backups.append(rel)
    dump('authorized_document_backups.json',backups)
    syntax=[];fail=[];jsons=[];badjson=[];links=[];absolutes=[];markers=[];dups=defaultdict(list)
    for row in rows:
        rel=row['path'];p=ROOT/rel
        dups[(row['bytes'],row['sha256'])].append(rel)
        if p.suffix.lower()=='.py':
            text=p.read_text(encoding='utf-8-sig')
            try:ast.parse(text,filename=rel);syntax.append(rel)
            except SyntaxError as e:fail.append({'file':rel,'line':e.lineno,'error':e.msg})
            for i,line in enumerate(text.splitlines(),1):
                if re.search(r'[A-Za-z]:[\\/]|/home/|/root/',line):absolutes.append({'file':rel,'line':i,'text':line[:400]})
                if re.search(r'TODO|FIXME|NotImplementedError',line):markers.append({'file':rel,'line':i,'text':line[:400]})
        elif p.suffix.lower()=='.json':
            try:json.loads(p.read_text(encoding='utf-8-sig'));jsons.append(rel)
            except Exception as e:badjson.append({'file':rel,'error':str(e)[:400]})
        elif p.suffix.lower()=='.md':
            for i,line in enumerate(p.read_text(encoding='utf-8-sig').splitlines(),1):
                for target in re.findall(r'\]\(([^)]+)\)',line):
                    target=target.strip('<>');u=urlsplit(target)
                    if u.scheme or not u.path or '{' in target:continue
                    path=(p.parent/unquote(u.path)).resolve()
                    if not path.exists():links.append({'file':rel,'line':i,'target':target,'active_root':'/' not in rel})
    dump('syntax.json',{'passed':not fail,'checked':len(syntax),'errors':fail})
    dump('json_validation.json',{'passed':not badjson,'checked':len(jsons),'errors':badjson})
    dump('missing_markdown_links.json',links);dump('absolute_path_references.json',absolutes);dump('source_markers.json',markers)
    duplicate=[{'bytes_each':size,'sha256':h,'paths':ps,'extra_bytes':size*(len(ps)-1)} for (size,h),ps in dups.items() if size and len(ps)>1]
    duplicate.sort(key=lambda x:x['extra_bytes'],reverse=True);dump('duplicate_groups.json',duplicate)
    ignored=subprocess.check_output(['git','ls-files','--others','--ignored','--exclude-standard','-z'],cwd=ROOT).decode('utf8').split('\0')[:-1]
    ig=defaultdict(lambda:{'files':0,'bytes':0})
    cachefiles=[]
    for rel in ignored:
        p=ROOT/rel;category='.venv' if rel.startswith('.venv/') else '.idea' if rel.startswith('.idea/') else 'bytecode_cache' if '__pycache__/' in rel or p.suffix in ['.pyc','.pyo'] else 'other'
        ig[category]['files']+=1;ig[category]['bytes']+=p.stat().st_size
        if category=='bytecode_cache':cachefiles.append(rel)
    dump('ignored_files_summary.json',dict(ig));dump('regenerable_cache_files.json',cachefiles)
    totals=defaultdict(lambda:{'files':0,'bytes':0})
    for row in rows:totals[row['top']]['files']+=1;totals[row['top']]['bytes']+=row['bytes']
    summary={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'git_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT).decode().strip(),
       'tracked_files':len(rows),'tracked_bytes':sum(r['bytes'] for r in rows),'extensions':dict(Counter(r['suffix'] for r in rows)),
       'top_level':dict(totals),'syntax_files':len(syntax),'syntax_errors':len(fail),'json_files':len(jsons),'json_errors':len(badjson),
       'missing_markdown_links':len(links),'active_root_missing_links':sum(r['active_root'] for r in links),'duplicate_groups':len(duplicate),'byte_identical_extra_bytes':sum(r['extra_bytes'] for r in duplicate),
       'ignored_categories':dict(ig),'largest_files':sorted(rows,key=lambda r:r['bytes'],reverse=True)[:20]}
    dump('inventory_summary.json',summary)
    print(json.dumps({k:v for k,v in summary.items() if k not in ['top_level','largest_files','extensions']},ensure_ascii=False),flush=True)
if __name__=='__main__':main()
