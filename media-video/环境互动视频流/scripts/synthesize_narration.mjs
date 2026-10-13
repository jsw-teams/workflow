// Execute the user-selected project's Microsoft REST speech bridge locally.
// Upstream MIT source remains in vendor; no credentials or returned tokens are logged.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';
let worker;
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const plan=JSON.parse(fs.readFileSync(path.join(root,'narration_plan.json'),'utf8'));
const manifestFile=path.join(root,'assets/narration_manifest.json');
const previous=new Map((fs.existsSync(manifestFile)?JSON.parse(fs.readFileSync(manifestFile,'utf8')):[]).map(x=>[x.id,x]));
const checkOnly=process.argv.includes('--check-cache');
fs.mkdirSync(path.join(root,'logs'),{recursive:true});
const records=[];
for(const line of plan){
  const body={input:line.text,voice:line.voice,speed:line.speed??1.0,pitch:line.pitch??'0',style:line.style??'general',volume:line.volume??'0'};
  try{
    const target=path.join(root,line.file);
    if(fs.existsSync(target) && fs.statSync(target).size>256){
      const buffer=fs.readFileSync(target);
      const prior=previous.get(line.id);
      const matches=prior && Object.keys(body).every(k=>prior.request?.[k]===body[k]) && prior.sha256===crypto.createHash('sha256').update(buffer).digest('hex');
      const duration=Number(execFileSync('ffprobe',['-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1',target],{encoding:'utf8'}).trim());
      if(matches && duration<=line.end-line.start){records.push({...line,duration,sha256:crypto.createHash('sha256').update(buffer).digest('hex'),provider:'wangwangit/tts Microsoft REST bridge, executed locally',request:body});console.log(JSON.stringify({id:line.id,duration,cached:true}));continue;}
    }
    if(checkOnly){console.log(JSON.stringify({id:line.id,cached:false,needs_synthesis:true}));continue;}
    worker??=(await import('../vendor/wangwangit-tts/index.js')).default;
    const request=new Request('http://localhost/v1/audio/speech',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    const response=await worker.fetch(request,{},{});
    if(!response.ok || !response.headers.get('content-type')?.includes('audio')){
      const error=await response.text();
      const status=/\b(?:40[01349]|50[0234])\b/.exec(error)?.[0];
      console.log(JSON.stringify({id:line.id,bridge_status:response.status,upstream_status:status||null,status:'failed'}));
      fs.writeFileSync(path.join(root,'logs/wangwangit_local_bridge_status.json'),JSON.stringify({status:'failed',bridge_status:response.status,upstream_status:status||null},null,2));
      process.exitCode=1;break;
    }
    const buffer=Buffer.from(await response.arrayBuffer());
    if(buffer.length<256)throw new Error('empty audio');
    fs.writeFileSync(target,buffer);
    const duration=Number(execFileSync('ffprobe',['-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1',target],{encoding:'utf8'}).trim());
    if(duration>line.end-line.start)throw new Error('clip exceeds scene slot');
    records.push({...line,duration,sha256:crypto.createHash('sha256').update(buffer).digest('hex'),provider:'wangwangit/tts Microsoft REST bridge, executed locally',request:body});
    console.log(JSON.stringify({id:line.id,duration,bytes:buffer.length}));
  }catch(error){
    console.log(JSON.stringify({id:line.id,status:'failed',error_type:error.name}));process.exitCode=1;break;
  }
}
if(!checkOnly && records.length===plan.length){
  fs.writeFileSync(path.join(root,'assets/narration_manifest.json'),JSON.stringify(records,null,2));
  fs.writeFileSync(path.join(root,'logs/narration_status.json'),JSON.stringify({status:'complete',provider:'wangwangit/tts local Microsoft REST bridge',line_count:records.length},null,2));
}
