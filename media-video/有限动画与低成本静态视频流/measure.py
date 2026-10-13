import argparse,json
from pathlib import Path
import cv2
import numpy as np

def read_video(path):
    cap=cv2.VideoCapture(str(path))
    frames=[]
    while True:
        ok,frame=cap.read()
        if not ok:
            break
        frames.append(frame)
    cap.release()
    return frames

def shoe_tracking(frames,timeline,sliding=False):
    measurements=[]
    for leg in ['rear','front']:
        for first in range(0,234,3):
            last=first+6
            a=timeline[first]['feet'][leg]
            b=timeline[last]['feet'][leg]
            if not (a['planted'] and b['planted'] and a['cycle']==b['cycle']):
                continue
            # Reject mutual shoe occlusion before measuring either condition.
            other='front' if leg=='rear' else 'rear'
            if any(np.linalg.norm(np.array(timeline[i]['feet'][leg]['sole'])-
                                  np.array(timeline[i]['feet'][other]['sole']))<45 for i in [first,last]):
                continue
            p=np.array(a['sole'])
            q=np.array(b['sole'])
            if sliding:
                p[0]+=78*((first/24+(0.9 if leg=='rear' else 0))%1.8)
                q[0]+=78*((last/24+(0.9 if leg=='rear' else 0))%1.8)
            px,py=[round(v) for v in p]
            template=frames[first][py-8:py+3,px-10:px+11]
            if template.shape!=(11,21,3):
                continue
            # Prediction only selects the correct shoe's search window; displacement
            # is measured by template correlation on H.264-decoded pixels.
            qx,qy=[round(v) for v in q]
            left,top=qx-22,qy-20
            search=frames[last][top:qy+15,left:qx+24]
            if search.shape[0]<template.shape[0] or search.shape[1]<template.shape[1]:
                continue
            scores=cv2.matchTemplate(search,template,cv2.TM_CCOEFF_NORMED)
            _,score,_,position=cv2.minMaxLoc(scores)
            if score<0.8:
                continue
            measured=np.array([left+position[0]+10,top+position[1]+8])
            displacement=float(np.linalg.norm(measured-np.array([px,py])))
            measurements.append({'leg':leg,'first_frame':first,'last_frame':last,
                'seconds':0.25,'correlation':round(score,5),
                'measured_shoe_displacement_pixels':round(displacement,4),
                'first_shoe_point':[px,py],'matched_shoe_point':measured.tolist()})
    distances=[m['measured_shoe_displacement_pixels'] for m in measurements]
    return {'method':'visible sole texture template correlation on decoded H.264 frames',
        'template_size':[21,11],'window_seconds':0.25,'minimum_correlation':0.8,
        'rejected_cases':'not in one stance cycle, mutually occluded shoes, or correlation below 0.8',
        'eligible_measurements':len(distances),'median_pixels':float(np.median(distances)),
        'p95_pixels':float(np.percentile(distances,95)),'maximum_pixels':max(distances),
        'measurements':measurements,
        'scope':'Visible, unoccluded 0.25s stance windows; does not verify hidden feet or an entire anatomical gait.'}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,default=Path(__file__).resolve().parent/'evidence');a=p.parse_args()
    timeline=json.loads((a.evidence/'timeline.json').read_text(encoding='utf-8'))
    grounded=read_video(a.evidence/'grounded.mp4');control=read_video(a.evidence/'control.mp4')
    assert len(grounded)==len(control)==len(timeline)==240
    results={'grounded':shoe_tracking(grounded,timeline),'sliding_control':shoe_tracking(control,timeline,True)}
    assert results['grounded']['median_pixels']<=1.5 and results['grounded']['p95_pixels']<=3
    assert results['sliding_control']['median_pixels']>=10
    (a.evidence/'measurements.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
    print(json.dumps({k:{f:r[f] for f in ['eligible_measurements','median_pixels','p95_pixels']} for k,r in results.items()}))
