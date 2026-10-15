"""Build a tool-ready whole-scene ImageGen request without an automatic paid call."""
import argparse,json
from pathlib import Path
p=argparse.ArgumentParser()
p.add_argument('--prompt',type=Path,required=True)
p.add_argument('--previous',type=Path,required=True)
p.add_argument('--reference',type=Path,action='append',default=[])
a=p.parse_args()
refs=[a.previous,*a.reference]
assert all(x.is_file() for x in refs)
args={'prompt':a.prompt.read_text(encoding='utf-8'),'referenced_image_paths':[str(x.resolve()) for x in refs],'transparent_background':False}
print(json.dumps(args,ensure_ascii=False))
