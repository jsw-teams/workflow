import hashlib, json, math, subprocess
from pathlib import Path
import cv2
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'output'
W,H,FPS=1280,720,24

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def save_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')

def encode(path, frames, size=(W, H)):
    process = subprocess.Popen(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y',
        '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{size[0]}x{size[1]}', '-r', str(FPS),
        '-i', '-', '-an', '-c:v', 'libx264', '-preset', 'fast', '-crf', '18',
        '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(path)], stdin=subprocess.PIPE)
    try:
        for frame in frames:
            process.stdin.write(np.asarray(frame, dtype=np.uint8).tobytes())
    finally:
        process.stdin.close()
    if process.wait() != 0:
        raise RuntimeError(f'Encoding failed: {path}')

def ik(hip, ankle, lengths):
    """Two rigid links, forward knee bend; clamp unreachable targets explicitly."""
    delta = ankle-hip
    distance = float(np.linalg.norm(delta))
    a, b = lengths
    clamped = min(max(distance, abs(a-b)+0.01), a+b-0.01)
    direction = delta/max(distance, 0.01)
    along = (a*a-b*b+clamped*clamped)/(2*clamped)
    height = math.sqrt(max(a*a-along*along, 0))
    normal = np.array([direction[1], -direction[0]], dtype=np.float32)
    return hip+direction*along+normal*height, abs(distance-clamped)

class TextureRig:
    def __init__(self):
        self.source_path = ROOT / 'assets/actor-sheet.png'
        self.full_source = Image.open(self.source_path).convert('RGBA')
        self.image = np.array(self.full_source.crop((0, 0, 627, 627)), dtype=np.float32)/255
        # Correct alpha compositing: hidden RGB at alpha=1 must not become a fringe.
        self.image[:, :, :3] *= self.image[:, :, 3:4]
        self.scale = 0.5
        self.center = np.array([364, 340], dtype=np.float32)
        self.rest = {
            'rear': [np.array(p, dtype=np.float32) for p in [(335,340),(290,455),(247,566),(256,590)]],
            'front': [np.array(p, dtype=np.float32) for p in [(386,340),(433,460),(493,585),(500,611)]],
        }
        self.lengths = {leg: (float(np.linalg.norm(p[1]-p[0])), float(np.linalg.norm(p[2]-p[1])))
                        for leg, p in self.rest.items()}
        # Separate the rigid torso, medicine bag and coat from articulated leg pixels.
        # These are video layer masks; the original source PNG remains byte-identical.
        body_mask=np.zeros((627,627),dtype=np.float32)
        body_mask[:341]=1
        for polygon in [
            [(294,284),(352,340),(333,427),(275,505),(191,459),(243,315)],
            [(399,305),(434,288),(496,474),(471,484),(435,389)],
            [(381,365),(405,410),(400,480),(357,475)],
            [(200,360),(235,342),(264,359),(258,432),(229,442),(190,416)],
        ]:
            cv2.fillPoly(body_mask,[np.array(polygon,dtype=np.int32)],1)
        self.body_image=self.image*body_mask[:,:,None]
        self.image=self.image*(1-body_mask[:,:,None])
        self.rigid_coat = np.array([(180,330),(320,340),(342,423),(273,506),(180,454)],dtype=np.float32)
        self.points = []
        for y in [0,150,300,340,410,460,510,555,580,610,626]:
            for x in [0,180,230,280,330,380,430,480,530,626]:
                self.points.append((x,y))
        self.points += [(float(p[0]),float(p[1])) for leg in self.rest.values() for p in leg]
        self.points += [tuple(p) for p in self.rigid_coat]
        self.points = np.unique(np.array(self.points, dtype=np.float32), axis=0)
        subdivision = cv2.Subdiv2D((0,0,627,627))
        for p in self.points:
            subdivision.insert(tuple(float(v) for v in p))
        self.triangles = []
        for triangle in subdivision.getTriangleList().reshape(-1,3,2):
            ids = [int(np.argmin(np.linalg.norm(self.points-p, axis=1))) for p in triangle]
            if all(np.linalg.norm(self.points[i]-p) < 0.01 for i,p in zip(ids,triangle)):
                source = self.points[ids]
                bx,by,bw,bh = cv2.boundingRect(source)
                if self.image[by:by+bh,bx:bx+bw,3].max() > 0.03:
                    self.triangles.append(ids)

    @staticmethod
    def route(x):
        # Full foreground route below the near fence endpoint; no crossing into traffic.
        if x < 760:
            u = max(0,min(1,(x-350)/410))
            return 590+96*(u*u*(3-2*u))
        if x < 1010:
            return 686
        u = max(0,min(1,(x-1010)/250))
        return 686-30*(u*u*(3-2*u))

    def body(self, t):
        x = 360+78*t
        y=self.route(x)-129+1.2*math.cos(t*2*math.pi/0.9)
        for leg,rest in self.rest.items():
            sole,_,_=self.foot(t,leg)
            angle=-math.atan2(37,68) if leg=='rear' else 0
            c,s=math.cos(angle),math.sin(angle)
            rotation=np.array([[c,-s],[s,c]],dtype=np.float32)
            ankle=sole+rotation@(rest[2]-rest[3])*self.scale
            hip_x=x+(rest[0][0]-self.center[0])*self.scale
            reach=sum(self.lengths[leg])*self.scale-0.5
            vertical=math.sqrt(max(0,reach*reach-(float(ankle[0])-float(hip_x))**2))
            y=max(y,float(ankle[1])-vertical)
        return np.array([x,y],dtype=np.float32)

    def foot(self, t, leg):
        cycle, stance = 1.8, 0.62
        phase_time = t+(0.9 if leg == 'rear' else 0)
        cycle_id = math.floor(phase_time/cycle)
        phase = (phase_time-cycle_id*cycle)/cycle
        landing_t = cycle_id*cycle-(0.9 if leg == 'rear' else 0)
        landing_x = 360+78*landing_t+45
        landing_y = self.route(landing_x)
        if phase < stance:
            return np.array([landing_x,landing_y],dtype=np.float32), True, cycle_id
        u = (phase-stance)/(1-stance)
        smooth = u*u*(3-2*u)
        next_x = landing_x+78*cycle
        x = landing_x+(next_x-landing_x)*smooth
        y = landing_y+(self.route(next_x)-landing_y)*smooth-21*math.sin(math.pi*u)
        return np.array([x,y],dtype=np.float32), False, cycle_id

    @staticmethod
    def bone_map(point, rest_a, rest_b, target_a, target_b):
        src = rest_b-rest_a
        dst = target_b-target_a
        angle = math.atan2(float(dst[1]),float(dst[0]))-math.atan2(float(src[1]),float(src[0]))
        c,s = math.cos(angle),math.sin(angle)
        rotation = np.array([[c,-s],[s,c]],dtype=np.float32)
        return target_a+rotation@(point-rest_a)*0.5

    def vertices(self, t, sliding=False):
        body = self.body(t)
        limbs, audit = {}, {}
        for leg, rest in self.rest.items():
            sole, planted, cycle = self.foot(t,leg)
            if sliding and planted:
                # Deliberate ablation: whole figure translated during nominal contact.
                phase_time = t+(0.9 if leg == 'rear' else 0)
                elapsed = phase_time % 1.8
                sole = sole+np.array([78*elapsed,0],dtype=np.float32)
            hip = body+(rest[0]-self.center)*self.scale
            shoe_angle = -math.atan2(37,68) if leg == 'rear' else 0
            c,s=math.cos(shoe_angle),math.sin(shoe_angle)
            rotation=np.array([[c,-s],[s,c]],dtype=np.float32)
            ankle=sole+rotation@(rest[2]-rest[3])*self.scale
            knee, error=ik(hip,ankle,[x*self.scale for x in self.lengths[leg]])
            limbs[leg]=(hip,knee,ankle,sole,rotation)
            audit[leg]={'planted':planted,'cycle':cycle,'sole':sole.tolist(),
                        'ik_unreachable_pixels':round(error,4)}
        output=[]
        for point in self.points:
            x,y=point
            rigid=body+(point-self.center)*self.scale
            if y <= 340 or (y<510 and (x<210 or x>485)) or cv2.pointPolygonTest(self.rigid_coat,(float(x),float(y)),False)>=0:
                output.append(rigid)
                continue
            leg='rear' if x<350 else 'front'
            rest=self.rest[leg]
            hip,knee,ankle,sole,rotation=limbs[leg]
            thigh=self.bone_map(point,rest[0],rest[1],hip,knee)
            shin=self.bone_map(point,rest[1],rest[2],knee,ankle)
            shoe=sole+rotation@(point-rest[3])*self.scale
            blend=max(0,min(1,(float(y)-float(rest[1][1])+20)/40))
            mapped=thigh*(1-blend)+shin*blend
            shoe_blend=max(0,min(1,(float(y)-float(rest[2][1])+8)/16))
            mapped=mapped*(1-shoe_blend)+shoe*shoe_blend
            hip_blend=max(0,min(1,(float(y)-340)/40))
            output.append(rigid*(1-hip_blend)+mapped*hip_blend)
        return np.array(output,dtype=np.float32),audit

    def render(self, t, background, sliding=False, markers=False):
        targets,audit=self.vertices(t,sliding)
        layer=np.zeros((H,W,4),dtype=np.float32)
        for ids in self.triangles:
            src=self.points[ids]
            dst=targets[ids]
            x,y,w,h=cv2.boundingRect(dst)
            left,top=max(0,x),max(0,y)
            right,bottom=min(W,x+w),min(H,y+h)
            if left>=right or top>=bottom:
                continue
            shifted=dst-np.array([left,top],dtype=np.float32)
            matrix=cv2.getAffineTransform(src,shifted)
            patch=cv2.warpAffine(self.image,matrix,(right-left,bottom-top),flags=cv2.INTER_LINEAR,
                                 borderMode=cv2.BORDER_CONSTANT)
            mask=np.zeros((bottom-top,right-left),dtype=np.uint8)
            cv2.fillConvexPoly(mask,np.round(shifted).astype(np.int32),255)
            roi=layer[top:bottom,left:right]
            visible=(mask>0)&(patch[:,:,3]>0.03)
            roi[visible]=patch[visible]
        body=self.body(t)
        transform=np.array([[self.scale,0,body[0]-self.center[0]*self.scale],
                            [0,self.scale,body[1]-self.center[1]*self.scale]],dtype=np.float32)
        torso=cv2.warpAffine(self.body_image,transform,(W,H),flags=cv2.INTER_LINEAR)
        layer=torso+layer*(1-torso[:,:,3:4])
        frame=np.asarray(background,dtype=np.float32).copy()/255
        # Quiet contact shadows; only ordinary alpha compositing, no source editing.
        shadow=np.zeros((H,W),dtype=np.float32)
        for record in audit.values():
            x,y=record['sole']
            cv2.ellipse(shadow,(round(x),round(y)+1),(23,4),0,0,360,0.16,-1)
        shadow=cv2.GaussianBlur(shadow,(11,11),3)
        frame*=1-shadow[:,:,None]
        frame=layer[:,:,:3]+frame*(1-layer[:,:,3:4])
        result=np.clip(frame*255,0,255).astype(np.uint8)
        if markers:
            for leg,record in audit.items():
                if record['planted']:
                    cv2.circle(result,tuple(round(v) for v in record['sole']),5,(112,244,198),-1)
        return result,audit

def main():
    OUT.mkdir(exist_ok=True)
    setting=np.asarray(Image.open(ROOT/'assets/setting.png').convert('RGB').resize((W,H),Image.Resampling.LANCZOS))
    rig=TextureRig();records=[]
    def fixed():
        for i in range(240):
            frame,audit=rig.render(i/FPS,setting)
            records.append({'frame':i,'t':i/FPS,'feet':audit})
            yield frame
    encode(OUT/'grounded.mp4',fixed())
    encode(OUT/'control.mp4',(rig.render(i/FPS,setting,sliding=True)[0] for i in range(240)))
    save_json(OUT/'timeline.json',records)
    print('Two 240-frame control clips rendered; measure encoded shoe texture separately.')

if __name__=='__main__':main()
