#!/usr/bin/env python3
"""Trim only after a reviewer marks that a filmed narrative event has completed.
Does NOT assign a script duration and does NOT detect completion automatically.
Usage: python apply_review_cut.py --decision filled_review.json --video clip.mp4 --out chosen_clip.mp4
"""
import argparse
import json
import subprocess
from pathlib import Path

p=argparse.ArgumentParser()
p.add_argument('--decision', type=Path, required=True)
p.add_argument('--video',type=Path,required=True)
p.add_argument('--out',type=Path,required=True)
a=p.parse_args()
d=json.loads(a.decision.read_text(encoding='utf-8'))
e=d.get('event_observation',{})
if e.get('event_reached') is not True or not isinstance(e.get('observed_completion_sec'),(int,float)):
    raise SystemExit('No confirmed observed event completion. Refusing automatic edit.')
end=e.get('suggested_cut_sec')
if not isinstance(end,(int,float)) or end <= 0 or end < e['observed_completion_sec']:
    raise SystemExit('Require a positive cut sec >= observed completion sec.')
if e.get('purposeful_hold_after_completion') is True and not e.get('hold_reason','').strip():
    raise SystemExit('Intentional hold requires a specific narrative purpose.')
probe=subprocess.run(['ffprobe','-v','error','-show_entries','format=duration','-of','default=noprint_wrappers=1:nokey=1',str(a.video)],capture_output=True,text=True,check=True)
duration=float(probe.stdout.strip())
if end>duration+0.001:
    raise SystemExit('Cut point is beyond actual file duration.')
if end>=duration-.04:
    print(f'No trim needed; selected end={end:.2f}s duration={duration:.2f}s')
    raise SystemExit(0)
a.out.parent.mkdir(parents=True,exist_ok=True)
subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(a.video),'-t',f'{end:.3f}',
                '-c:v','libx264','-crf','19','-preset','medium','-pix_fmt','yuv420p',
                '-c:a','aac','-b:a','192k','-movflags','+faststart',str(a.out)],check=True)
print(f'Edited only verified useful portion: selected end={end:.2f}s, source={duration:.2f}s.')
