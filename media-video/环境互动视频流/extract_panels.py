"""Extract generated full-scene panels without modifying the source illustration."""
import argparse,hashlib,json
from pathlib import Path
from PIL import Image
p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('output',type=Path)
p.add_argument('--columns',type=int,default=2);p.add_argument('--rows',type=int,default=2);a=p.parse_args()
assert a.columns>0 and a.rows>0
im=Image.open(a.source).convert('RGB');a.output.mkdir(parents=True,exist_ok=True)
records=[]
for r in range(a.rows):
    for c in range(a.columns):
        # Split evenly; review separator placement before selecting panels.
        x0=round(c*im.width/a.columns);x1=round((c+1)*im.width/a.columns)
        y0=round(r*im.height/a.rows);y1=round((r+1)*im.height/a.rows)
        out=a.output/f'{r*a.columns+c+1:02}.png';im.crop((x0,y0,x1,y1)).save(out)
        records.append({'file':out.name,'crop_box':[x0,y0,x1,y1],'native_size':[x1-x0,y1-y0],'sha256':hashlib.sha256(out.read_bytes()).hexdigest()})
(a.output/'manifest.json').write_text(json.dumps({'source_sha256':hashlib.sha256(a.source.read_bytes()).hexdigest(),'frames':records},indent=2),encoding='utf-8')
