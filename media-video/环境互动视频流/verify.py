"""Validate the actual encoded artifact and source/voice manifests."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--video',type=Path,default=ROOT/'output/film.mp4');a=p.parse_args()
project=json.loads((ROOT/'project.json').read_text(encoding='utf-8'))
probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-count_frames','-show_streams','-of','json',str(a.video)],encoding='utf-8'))
v=next(x for x in probe['streams'] if x['codec_type']=='video');audio=next(x for x in probe['streams'] if x['codec_type']=='audio')
assert int(v['nb_read_frames'])==project['fps']*project['duration']
assert v['avg_frame_rate']==f'{project["fps"]}/1'
assert [v['width'],v['height']]==project['resolution']
assert abs(float(v['duration'])-project['duration'])<.03
assert abs(float(audio['duration'])-project['duration'])<.06
assert not any(x['codec_type']=='subtitle' for x in probe['streams'])
decoded=subprocess.run(['ffmpeg','-v','error','-i',str(a.video),'-f','null','-'],capture_output=True,text=True)
assert decoded.returncode==0 and not decoded.stderr.strip(),decoded.stderr
for frame in project['edits']:
    path=ROOT/frame['file']
    assert path.resolve().is_relative_to(ROOT/'assets/frames')
    assert hashlib.sha256(path.read_bytes()).hexdigest()==frame['sha256']
voices=json.loads((ROOT/'assets/narration_manifest.json').read_text(encoding='utf-8'))
for line in voices:
    assert hashlib.sha256((ROOT/line['file']).read_bytes()).hexdigest()==line['sha256']
    assert line['duration']<=line['end']-line['start']
result={'duration':float(v['duration']),'fps':v['avg_frame_rate'],'frames':int(v['nb_read_frames']),
        'source_poses':len(project['edits']),'narration_clips':len(voices),'subtitles':'off-screen narration captions',
        'whole_stream_decode':True,'source_hashes_verified':True,'sha256':hashlib.sha256(a.video.read_bytes()).hexdigest()}
(ROOT/'output').mkdir(exist_ok=True)
(ROOT/'output/verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result))
