"""Sparse soft piano, short distant truck cues and measured off-screen narration."""
import json
import subprocess
from pathlib import Path
import numpy as np

def piano(midi,length,sr):
    t=np.arange(round(length*sr))/sr
    f=440*2**((midi-69)/12)
    attack=np.minimum(t/.035,1)
    envelope=attack*np.exp(-t*2.3)*(1-np.minimum(1,np.maximum(0,t-length+.16)/.16))
    return (np.sin(2*np.pi*f*t)+.13*np.sin(2*np.pi*2*f*t)+.035*np.sin(2*np.pi*3*f*t))*envelope

def layers(root,sr,duration):
    n=round(sr*duration)
    bed=np.zeros((n,2),dtype=np.float32)
    narration=np.zeros((n,2),dtype=np.float32)
    events=[]
    def put(start,sig,amp,pan=0):
        j=round(start*sr);k=min(n,j+len(sig))
        if k>j:
            bed[j:k,0]+=sig[:k-j]*amp*np.sqrt((1-pan)/2)
            bed[j:k,1]+=sig[:k-j]*amp*np.sqrt((1+pan)/2)
    chords=[[60,64,67,74],[65,69,72,76],[60,64,69,74],[67,72,74,79]]
    # Gentle major/add-nine phrases; long silences instead of an insistent ostinato.
    for start,end,amp in [(3,22,.013),(33,44,.010),(78,99,.013),(108,123,.014),(132,144,.009),(150,159,.019)]:
        for step,b in enumerate(np.arange(start,end,4.8)):
            chord=chords[step%len(chords)]
            for i,midi in enumerate(chord):
                put(float(b)+i*.44,piano(midi,2.4,sr),amp,(-.3,.15,-.1,.35)[i])
        events.append({'start':start,'end':end,'type':'soft_piano','description':'Sparse warm major/add-nine phrases, no low drone'})
    tune=[(76,.25),(75,.25),(76,.25),(75,.25),(76,.25),(71,.25),(74,.25),(72,.25),(69,.7)]
    for start,amp in [(25.1,.012),(100.5,.024),(125.1,.020),(145.2,.007)]:
        pos=start
        for midi,length in tune:
            put(pos,piano(midi,length+.28,sr),amp,.4)
            pos+=length
        events.append({'start':start,'end':pos,'type':'truck_cue','description':'Short freshly synthesized public-domain melody cue, not continuous music'})
    manifest_path=root/'assets/narration_manifest.json'
    assert manifest_path.exists(),'Narration must exist for this version'
    manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
    plan=json.loads((root/'narration_plan.json').read_text(encoding='utf-8'))
    assert [x['id'] for x in manifest]==[x['id'] for x in plan]
    duck=np.ones(n,dtype=np.float32)
    for line in manifest:
        raw=subprocess.check_output(['ffmpeg','-v','error','-i',str(root/line['file']),'-f','f32le','-ac','1','-ar',str(sr),'-'])
        sig=np.frombuffer(raw,dtype='<f4').copy()
        assert len(sig)/sr<=line['end']-line['start']+.03
        rms=float(np.sqrt(np.mean(sig**2)))
        peak=float(np.max(np.abs(sig)))
        sig*=min(.105/max(rms,1e-6),.60/max(peak,1e-6))
        fade=np.minimum(1,np.arange(len(sig))/(sr*.015))*np.minimum(1,(len(sig)-np.arange(len(sig)))/(sr*.04))
        sig*=fade
        j=round(line['start']*sr);k=min(n,j+len(sig))
        narration[j:k,0]+=sig[:k-j];narration[j:k,1]+=sig[:k-j]
        a=max(0,j-round(.25*sr));b=min(n,k+round(.4*sr))
        envelope=np.ones(b-a,dtype=np.float32)*.35
        ramp=min(round(.25*sr),len(envelope)//2)
        envelope[:ramp]=np.linspace(1,.35,ramp);envelope[-ramp:]=np.linspace(.35,1,ramp)
        duck[a:b]=np.minimum(duck[a:b],envelope)
        events.append({'start':line['start'],'end':line['start']+len(sig)/sr,'type':'off_screen_narration','id':line['id'],'provider':line['provider'],'source_sha256':line['sha256']})
    bed*=duck[:,None]
    return bed,narration,duck,events
