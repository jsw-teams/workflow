"""Rebuild an explicit-keyframe GIF; no optical flow or invented inbetween poses."""
import argparse
import hashlib
import json
from pathlib import Path
from PIL import Image, ImageOps

p=argparse.ArgumentParser();p.add_argument('action',type=Path);a=p.parse_args()
manifest=json.loads((a.action/'manifest.json').read_text(encoding='utf-8'))
frames=[]
for f in manifest['frames']:
    path=a.action/f['file']
    assert hashlib.sha256(path.read_bytes()).hexdigest()==f['sha256']
    frames.append(ImageOps.contain(Image.open(path).convert('RGB'),(320,320),Image.Resampling.LANCZOS))
assert len(frames)>1
frames[0].save(a.action/'preview.gif',save_all=True,append_images=frames[1:],
               duration=[x['duration_ms'] for x in manifest['frames']],loop=0,disposal=2)
print(f'{len(frames)} key poses; duration={sum(x["duration_ms"] for x in manifest["frames"])}ms; seamless={manifest["seamless_loop"]}')
