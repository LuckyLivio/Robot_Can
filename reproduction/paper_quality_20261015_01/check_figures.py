"""Numerical source integrity and PDF raster proofs for all paper figures."""
from pathlib import Path
import csv, hashlib, json, math, sys, subprocess, shutil
from PIL import Image, ImageDraw, ImageFont
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1];FIG=RUN/'figures'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    sources=json.loads((RUN/'PLOT_SOURCES.json').read_text(encoding='utf8'));cat=json.loads((FIG/'CATALOG.json').read_text(encoding='utf8'))['figures']
    for p,r in sources.items():
        assert sha(ROOT/p)==r['sha256'],p
        if 'copy' in r:assert sha(RUN/r['copy'])==r['sha256'],p
    out=RUN/'validation';out.mkdir(exist_ok=True);rows=[];proofs=[]
    for g in cat:
        name=g['id'];png=FIG/(name+'.png');pdf=FIG/(name+'.pdf');svg=FIG/(name+'.svg');csvfile=FIG/(name+'.csv')
        with Image.open(png) as im:
            assert min(im.info.get('dpi',(0,0)))>=599
            expected=round(g['width_mm']/25.4*600);assert abs(im.width-expected)<=2
            im.verify()
        with csvfile.open(encoding='utf-8-sig') as f:
            marks=list(csv.DictReader(f))
        assert len(marks)==g['plotted_rows']
        for r in marks:
            for k in ['x','y','low','high']:
                if r[k]:assert math.isfinite(float(r[k])),(name,r)
        poppler=Path(shutil.which('pdftoppm')).parent
        def tool(binary,*args):
            exe=poppler/(binary+'.exe') if sys.platform=='win32' else poppler/binary
            if not exe.is_file():exe=Path(shutil.which(binary))
            r=subprocess.run([str(exe),*map(str,args)],check=True,capture_output=True,text=True,encoding='utf8',errors='replace')
            return r.stdout
        info=tool('pdfinfo',pdf);assert 'Pages:           1' in info
        image_listing=tool('pdfimages','-list',pdf);assert len(image_listing.strip().splitlines())==2,name
        fonts=tool('pdffonts',pdf);assert 'Type 3' not in fonts and len(fonts.strip().splitlines())>=3
        assert all('yes' in row for row in fonts.strip().splitlines()[2:]),fonts
        prefix=out/(name+'_pdf');tool('pdftoppm','-r','108','-singlefile','-png',pdf,prefix)
        p=prefix.with_suffix('.png');proofs.append((name,p))
        rows.append({'id':name,'png_sha256':sha(png),'pdf_sha256':sha(pdf),'svg_sha256':sha(svg),'csv_sha256':sha(csvfile),'marks':len(marks),'pdf_vector':True,'pdf_embedded_fonts':fonts,'pdf_rendered':True})
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',24)
    for page in range((len(proofs)+5)//6):
        sheet=Image.new('RGB',(1700,1500),'#e8ebef');draw=ImageDraw.Draw(sheet)
        for i,(name,p) in enumerate(proofs[page*6:page*6+6]):
            x=(i%2)*850;y=(i//2)*500
            with Image.open(p) as im:
                im.thumbnail((830,455));sheet.paste(im,(x+(850-im.width)//2,y+35))
            draw.text((x+15,y+4),name,font=font,fill='#111111')
        sheet.save(out/f'contact_{page+1:02}.jpg',quality=92)
    result={'passed':True,'figures':len(cat),'plotted_rows':sum(r['marks'] for r in rows),'sources_checked':len(sources),'png_dpi':600,'all_pdfs_rendered':True,'no_embedded_raster_in_pdfs':True,'records':rows,'visual_review':'Contact sheets and selected full-size proofs require separate human/model visual inspection.'}
    (out/'figure_validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps({k:v for k,v in result.items() if k!='records'},ensure_ascii=False))
if __name__=='__main__':main()
