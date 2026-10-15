#!/usr/bin/env python3
"""Local media / locked-reference QA; deliberately NOT a semantic action verifier.
Usage: python qa_media.py --video /path/to/clip.mp4 --contract shot_contract.json --out out/clip
"""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def probe_video(video: Path):
    result = subprocess.run(['ffprobe', '-v', 'error', '-show_format',
                             '-show_streams', '-of', 'json', str(video)],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode:
        raise RuntimeError('ffprobe error: ' + result.stderr.strip())
    data = json.loads(result.stdout)
    stream = next((s for s in data['streams'] if s['codec_type'] == 'video'), None)
    if stream is None:
        raise RuntimeError('No video stream')
    return data, stream


def inspect_video(video: Path, out: Path, n_images=12):
    data, stream = probe_video(video)
    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        raise RuntimeError('OpenCV could not decode video')
    fps = cap.get(cv2.CAP_PROP_FPS)
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if fps <= 0 or n <= 0:
        raise RuntimeError(f'Unusable fps/frame_count: {fps}/{n}')
    duration = n / fps
    sample_every = max(1, round(fps / 4))
    key_indices = set(int(round(x)) for x in np.linspace(0, max(n-1,0), n_images))
    gray_prev = None
    activity = []
    thumbs = []
    frame_index = 0
    decoded = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        decoded += 1
        if frame_index in key_indices:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            im = Image.fromarray(rgb).resize((320,180), Image.Resampling.LANCZOS)
            thumbs.append((frame_index/fps, im))
        if frame_index % sample_every == 0:
            gray = cv2.cvtColor(cv2.resize(frame, (160,90)), cv2.COLOR_BGR2GRAY)
            if gray_prev is not None:
                delta = np.abs(gray.astype(np.int16)-gray_prev.astype(np.int16))
                # Activity measured in changed pixels and intensity. A heuristic only.
                activity.append({'time_sec': round(frame_index/fps,3),
                                 'changed_pixel_fraction': round(float(np.mean(delta>8)),5),
                                 'mean_gray_difference': round(float(np.mean(delta)),3)})
            gray_prev = gray
        frame_index += 1
    cap.release()
    if decoded < n - 1:
        raise RuntimeError(f'Decode incomplete: {decoded} vs reported {n}')
    if not thumbs:
        raise RuntimeError('No frames extracted')

    w,h=320,180
    cols = 3
    rows = (len(thumbs)+cols-1)//cols
    sheet = Image.new('RGB', (cols*w, rows*(h+24)), '#1b2027')
    draw = ImageDraw.Draw(sheet)
    for idx, (t, im) in enumerate(thumbs):
        x=(idx%cols)*w
        y=(idx//cols)*(h+24)
        sheet.paste(im, (x,y))
        draw.text((x+8,y+h+3),f't={t:.2f}s',fill='white')
    sheet.save(out/'contact_sheet.png')

    # Never reject from stillness alone: emotional holds can be intentional.
    # Consecutive 4-fps samples that barely change are only review candidates.
    still_candidates = []
    block_start = None
    for item in activity + [{'time_sec':duration, 'changed_pixel_fraction':1, 'mean_gray_difference':255}]:
        t=item['time_sec']
        is_still=item['changed_pixel_fraction']<0.008 and item['mean_gray_difference']<1.2
        if is_still and block_start is None:
            block_start = max(0,t-sample_every/fps)
        if not is_still and block_start is not None:
            if t-block_start>=1.5:
                still_candidates.append({'start_sec':round(block_start,2),
                                         'end_sec':round(t,2),
                                         'duration_sec':round(t-block_start,2),
                                         'finding':'Possible still / no new visual information; review context'})
            block_start=None
    return {
      'fps':round(float(fps),3), 'frames_reported':n, 'frames_decoded':decoded,
      'duration_sec_observed':round(float(duration),3),
      'resolution':[int(stream['width']),int(stream['height'])],
      'codec':stream.get('codec_name'),
      'audio_stream_exists':any(s['codec_type']=='audio' for s in data.get('streams',[])),
      'review_frames':len(thumbs), 'stillness_candidates':still_candidates,
      'sample_rate_for_activity':round(fps/sample_every,2),
      'note':'Motion heuristics are not event completion or physical correctness proofs.'
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--video',type=Path,required=True)
    p.add_argument('--contract',type=Path,default=Path(__file__).resolve().parent/'shot_contract.json')
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    a.out.mkdir(parents=True,exist_ok=True)
    errors=[]
    warnings=[]
    contract=json.loads(a.contract.read_text(encoding='utf-8'))
    ref_audit={}
    for key,ref in contract.get('references',{}).items():
        f=a.contract.resolve().parent/ref['path']
        if not f.is_file():
            ref_audit[key]={'verified':False, 'reason':'missing'}
            errors.append(f'P0 missing reference: {key}')
            continue
        actual=sha256(f)
        ref_audit[key]={'path':ref['path'],'sha256_actual':actual,
                        'verified':actual.lower()==ref['sha256'].lower()}
        if not ref_audit[key]['verified']:
            errors.append(f'P0 reference hash mismatch: {key}')
    video_audit={}
    try:
        if not a.video.is_file():
            raise RuntimeError('Missing video file')
        video_audit=inspect_video(a.video,a.out)
    except Exception as exc:
        errors.append('P0 video technical error: '+str(exc))
    if video_audit.get('stillness_candidates'):
        warnings.append('Visual-stillness intervals detected; judge whether they contain purposeful emotion/atmosphere.')

    needed=['prompt_type','reference_binding','scene_geography','character_identity',
            'prop_inventory','action_causality','hand_occlusion','foot_support',
            'camera_axis','narrative_progress','edit_transition']
    semantic={name:{'status':'unverified','evidence':'','notes':''} for name in needed}
    report={
       'shot_id':contract.get('shot_id'), 'source_video':str(a.video.resolve()),
       'source_video_sha256':sha256(a.video) if a.video.is_file() else None,
       'reference_audit':ref_audit, 'video_audit':video_audit,
       'technical_errors':errors,'auto_review_warnings':warnings,
       'semantic_checklist_FOR_CODEX_OR_HUMAN':semantic,
       'verdict':'REJECT' if errors else 'NEEDS_SEMANTIC_REVIEW',
       'disclaimer':'Technical checks cannot prove contact, spatial coherence, or narrative quality; no automatic PASS.'
    }
    (a.out/'qa_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'verdict':report['verdict'],'technical_errors':errors,
                      'review_warnings':warnings,'report':str(a.out/'qa_report.json'),
                      'contact_sheet':str(a.out/'contact_sheet.png') if video_audit else None},ensure_ascii=False,indent=2))
    return 2 if errors else 0

if __name__=='__main__':
    sys.exit(main())
