import json,wave
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parent
SR=24000
DURATION=160

def sound():
    rng=np.random.default_rng(20261013)
    n=SR*DURATION
    mix=np.zeros((n,2),dtype=np.float32)
    events=[]
    def insert(start,signal,amp=1,pan=0,label=None):
        j=round(start*SR)
        k=min(n,j+len(signal))
        if k<=j:
            return
        mix[j:k,0]+=signal[:k-j]*amp*np.sqrt((1-pan)/2)
        mix[j:k,1]+=signal[:k-j]*amp*np.sqrt((1+pan)/2)
        if label:
            events.append({'time':start,'duration':len(signal)/SR,'label':label})
    t=np.arange(n,dtype=np.float32)/SR
    outdoor=np.interp(t,[0,4,5,98,100,156,160],[1,1,.22,.22,1,.9,0])
    # Subdued synthetic room/alley ambience, no voices.
    noise=rng.normal(0,1,n).astype(np.float32)
    smooth=np.convolve(noise,np.ones(60,dtype=np.float32)/60,mode='same')
    base=smooth*.014*outdoor
    mix[:,0]+=base;mix[:,1]+=base
    def thump(sec,amp=.09):
        tt=np.arange(int(.13*SR))/SR
        sig=np.sin(2*np.pi*(95*tt-100*tt*tt))*np.exp(-tt*36)
        sig+=rng.normal(0,.10,len(tt))*np.exp(-tt*50)
        insert(sec,sig,amp,label='鞋底輕落地')
    for sec in [1.5,2.8,14.1,37.2,42.2,45.4,47.8,54.2,57,59,61.5,63,80.1,83.8,97.2,99,100.7,103.3,106.5,109.5,112.3,113.4,114.6,116.1,118.1,119.4,120.3,121.7,123,140.5,145.2,148,150.5,156.6]:
        thump(sec,.065 if sec<100 else .085)
    for sec,label in [(10.8,'小包放在櫃上'),(45.3,'房門關閉'),(49.6,'鑰匙鎖門'),(77,'放下兩袋'),(98.5,'提袋拿起'),(130,'袋子交接')]:
        tt=np.arange(int(.24*SR))/SR
        sig=(rng.normal(0,.16,len(tt))+np.sin(2*np.pi*160*tt))*np.exp(-tt*24)
        insert(sec,sig,.075,label=label)
    for sec,label in [(41,'提袋窸窣'),(73,'回收袋勾住'),(80,'整理提袋'),(93,'塑膠瓶放入袋中'),(95,'塑膠瓶入袋'),(96.6,'鋁罐入袋'),(138,'回收物落入容器')]:
        tt=np.arange(int(.5*SR))/SR
        sig=rng.normal(0,1,len(tt))*np.sin(np.pi*tt/.5)**2
        sig=np.convolve(sig,np.ones(5)/5,mode='same')
        insert(sec,sig,.027,label=label)
    for sec,freq,label in [(75.5,520,'第一個瓶子碰地'),(76,660,'第二個瓶子碰地'),(76.3,1750,'鋁罐碰地'),(96.5,1500,'拾起鋁罐'),(137.8,1300,'回收容器瓶罐聲'),(138.4,1900,'回收容器瓶罐聲')]:
        tt=np.arange(int(.38*SR))/SR
        sig=(np.sin(2*np.pi*freq*tt)+.25*np.sin(2*np.pi*freq*2.73*tt))*np.exp(-tt*15)
        insert(sec,sig,.07,label=label)
    from warm_soundtrack import layers
    bed,narrator,duck,new_events=layers(ROOT,SR,DURATION)
    mix*=10**(6/20)  # SFX remain below narrator.
    mix*=np.maximum(duck,.65)[:,None]
    mix+=bed+narrator
    events.extend(new_events)
    fade=np.minimum(1,t/.35)*np.minimum(1,(DURATION-t)/2)
    mix*=fade[:,None]
    peak=float(np.max(np.abs(mix)))
    assert peak<1
    pcm=(np.clip(mix,-1,1)*32767).astype('<i2')
    with wave.open(str(ROOT/'assets/soundtrack.wav'),'wb') as w:
        w.setnchannels(2);w.setsampwidth(2);w.setframerate(SR);w.writeframes(pcm.tobytes())
    (ROOT/'output/sound_design.json').write_text(json.dumps({'sample_rate':SR,'duration':160,'peak_linear':peak,'voice_included':True,'subtitles_included':True,'method':'wangwangit/tts off-screen narration; warm sparse piano, short truck cues and original SFX; no low drone','events':events},ensure_ascii=False,indent=2),encoding='utf-8')

if __name__=='__main__':
    (ROOT/'output').mkdir(exist_ok=True)
    sound()
