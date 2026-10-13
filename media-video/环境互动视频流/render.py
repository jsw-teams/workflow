"""Rebuild the narrated whole-scene film from portable manifests and saved pixels."""
import hashlib
import json
import subprocess
import sys
import os
import re
from pathlib import Path
from PIL import Image,ImageOps

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'output'

def main():
    project=json.loads((ROOT/'project.json').read_text(encoding='utf-8'))
    edits=project['edits'];fps=project['fps']
    OUT.mkdir(exist_ok=True);(OUT/'frames').mkdir(exist_ok=True)
    lines=['ffconcat version 1.0']
    expected=0
    for i,edit in enumerate(edits):
        source=ROOT/edit['file']
        assert source.resolve().is_relative_to(ROOT/'assets/frames')
        assert hashlib.sha256(source.read_bytes()).hexdigest()==edit['sha256']
        assert edit['start_frame']==expected
        expected+=edit['frame_count']
        im=Image.open(source).convert('RGB')
        assert list(im.size)==edit['native_size']
        edge=edit['presentation_crop_edge_px']
        if edge:im=im.crop((edge,edge,im.width-edge,im.height-edge))
        im=ImageOps.fit(im,tuple(project['resolution']),method=Image.Resampling.LANCZOS)
        im.save(OUT/'frames'/f'{i:03}.jpg',quality=97,subsampling=0)
        lines.extend([f"file 'frames/{i:03}.jpg'",f'duration {edit["frame_count"]/fps:.9f}'])
    assert expected==round(project['duration']*fps)
    lines.append(f"file 'frames/{len(edits)-1:03}.jpg'")
    (OUT/'edit.ffconcat').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    captions=[]
    voices=json.loads((ROOT/'assets/narration_manifest.json').read_text(encoding='utf-8'))
    for line in voices:
        parts=re.findall(r'[^，。！？]+[，。！？]?',line['text'])
        weights=[len(x)+1.5 for x in parts]
        pos=line['start']
        for text,weight in zip(parts,weights):
            end=pos+line['duration']*weight/sum(weights)
            captions.append({'start':pos,'end':end,'text':text,'role':'off-screen narrator',
                             'timing':'proportional phrase timing within measured clip; not word alignment'})
            pos=end
    (ROOT/project['caption_file']).write_text(json.dumps(captions,ensure_ascii=False,indent=2),encoding='utf-8')
    font='Microsoft JhengHei' if os.name=='nt' else 'Noto Sans CJK TC'
    def stamp(sec):
        cs=round(sec*100)
        return f'{cs//360000}:{cs//6000%60:02}:{cs//100%60:02}.{cs%100:02}'
    head=f'''[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Narrator,{font},54,&H00FFFFFF,&H000000FF,&H00161616,&H70000000,0,0,0,0,100,100,1,0,1,3,1,2,80,80,68,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''
    events=[f'Dialogue: 0,{stamp(x["start"])},{stamp(x["end"])},Narrator,Narrator,0,0,0,,{x["text"]}' for x in captions]
    (OUT/'subtitles.ass').write_text(head+'\n'.join(events)+'\n',encoding='utf-8-sig')
    # Audio regeneration is local and uses validated pre-synthesized narration.
    subprocess.run([sys.executable,str(ROOT/'sound.py')],check=True)
    cmd=['ffmpeg','-hide_banner','-loglevel','warning','-y','-f','concat','-safe','0','-i','output/edit.ffconcat',
         '-i','assets/soundtrack.wav','-vf',f'fps={fps},subtitles=output/subtitles.ass,fade=t=out:st={project["duration"]-2}:d=2',
         '-frames:v',str(expected),'-t',str(project['duration']),'-c:v','libx264','-preset','medium','-crf','19',
         '-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-movflags','+faststart','output/film.mp4']
    subprocess.run(cmd,cwd=ROOT,check=True)
    print(f'{len(edits)} whole-scene poses, {expected} encoded frames, narration captions.')

if __name__=='__main__':main()
