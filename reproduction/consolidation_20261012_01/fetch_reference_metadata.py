"""Fetch official citation metadata only; never guess bibliography fields."""
import concurrent.futures,datetime,json,re,urllib.request
from html.parser import HTMLParser
from pathlib import Path
RUN=Path(__file__).resolve().parent
SOURCES=[('robomimic2021','https://arxiv.org/abs/2108.03298'),('planet2018','https://arxiv.org/abs/1811.04551'),
 ('vaml2017','https://proceedings.mlr.press/v54/farahmand17a.html'),('dinowm2024','https://arxiv.org/abs/2411.04983'),
 ('act2023','https://arxiv.org/abs/2304.13705'),('recoveryrl2020','https://arxiv.org/abs/2010.15920'),
 ('pets2018','https://arxiv.org/abs/1805.12114'),('robosuite2020','https://arxiv.org/abs/2009.12293')]
class Metadata(HTMLParser):
 def __init__(self):super().__init__();self.values={}
 def handle_starttag(self,tag,attrs):
  if tag!='meta':return
  d=dict(attrs);key=d.get('name','')
  if key.startswith('citation_') and d.get('content'):self.values.setdefault(key,[]).append(d['content'])
def get(item):
 key,url=item;req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 (academic metadata verification)'})
 with urllib.request.urlopen(req,timeout=45) as r:source=r.read().decode('utf8');resolved=r.url
 p=Metadata();p.feed(source);m=p.values
 assert m.get('citation_title') and m.get('citation_author'),(url,m)
 date=(m.get('citation_date') or m.get('citation_publication_date') or [''])[0]
 assert re.search(r'\d{4}',date),(url,date)
 return {'key':key,'url':url,'resolved_url':resolved,'checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
         'title':m['citation_title'][0],'authors':m['citation_author'],'date':date,'official_metadata':m,
         'scope':'Official citation metadata fetched; focused method passages separately audited in RELATED_WORK.md. Not an exhaustive literature review.'}
def main():
 with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:rows=list(pool.map(get,SOURCES))
 target=RUN/'references_metadata.json'
 with target.open('x',encoding='utf8') as f:json.dump(rows,f,ensure_ascii=False,indent=2)
 entries=[]
 for r in rows:
  m=r['official_metadata'];fields={'title':r['title'],'author':' and '.join(r['authors']),'year':re.search(r'\d{4}',r['date']).group(),'url':r['url']}
  arxiv=re.search(r'arxiv.org/abs/(\d+\.\d+)',r['url'])
  if arxiv:fields.update(eprint=arxiv.group(1),archivePrefix='arXiv');kind='misc'
  else:
   kind='inproceedings'
   for name,keys in [('booktitle',['citation_conference_title']),('volume',['citation_volume']),('publisher',['citation_publisher']),('doi',['citation_doi'])]:
    if any(k in m for k in keys):fields[name]=next(m[k][0] for k in keys if k in m)
   if m.get('citation_firstpage') and m.get('citation_lastpage'):fields['pages']=m['citation_firstpage'][0]+'--'+m['citation_lastpage'][0]
  entries.append('@'+kind+'{'+r['key']+',\n'+',\n'.join('  '+k+' = {'+v.replace('&',r'\&')+'}' for k,v in fields.items())+'\n}')
 with (RUN/'references_verified.bib').open('x',encoding='utf8') as f:f.write('% Fetched from official metadata; arXiv years denote first submission, not inferred conference years.\n\n'+'\n\n'.join(entries)+'\n')
 print(json.dumps([{'key':r['key'],'title':r['title'],'author_count':len(r['authors']),'date':r['date']} for r in rows],ensure_ascii=False,indent=2))
if __name__=='__main__':main()
