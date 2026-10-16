import {CATEGORIES,TIME_ZONE,todayAt,validDate,type Day,type Seconds} from './model';
export const MAX_BYTES=128*1024;
export const MAX_DAYS=366;
export type SyncPayload={schemaVersion:1;timeZone:typeof TIME_ZONE;days:Day[]};
export class InputError extends Error {}
function record(value:unknown):value is Record<string,unknown>{return typeof value==='object'&&value!==null&&!Array.isArray(value);}
function exact(value:Record<string,unknown>,keys:readonly string[]){return Object.keys(value).length===keys.length&&keys.every(k=>Object.hasOwn(value,k));}
export function validatePayload(input:unknown,now=new Date()):SyncPayload{
  if(!record(input)||!exact(input,['schemaVersion','timeZone','days'])||input.schemaVersion!==1||input.timeZone!==TIME_ZONE||!Array.isArray(input.days)||input.days.length<1||input.days.length>MAX_DAYS)throw new InputError('Invalid aggregate payload.');
  const seen=new Set<string>(),today=todayAt(now);
  const days:Day[]=input.days.map(value=>{
    if(!record(value)||!exact(value,['date','status','seconds'])||!validDate(value.date)||value.date>today||seen.has(value.date)||!['missing','partial','complete'].includes(value.status as string))throw new InputError('Invalid day.');
    seen.add(value.date);
    if(value.status==='missing'){
      if(value.seconds!==null)throw new InputError('Missing days require null seconds.');
      return {date:value.date,status:'missing',seconds:null};
    }
    if(!record(value.seconds)||!exact(value.seconds,CATEGORIES))throw new InputError('Only category durations are accepted.');
    const seconds={} as Seconds;
    for(const c of CATEGORIES){
      const n=value.seconds[c];
      if(typeof n!=='number'||!Number.isFinite(n)||n<0||n>86400)throw new InputError('Invalid category duration.');
      seconds[c]=n;
    }
    if(CATEGORIES.reduce((sum,c)=>sum+seconds[c],0)>86400)throw new InputError('Daily total exceeds a day.');
    return {date:value.date,status:value.status as 'partial'|'complete',seconds};
  });
  return {schemaVersion:1,timeZone:TIME_ZONE,days};
}
export async function readJson(request:Request):Promise<unknown>{
  if(request.headers.get('content-type')?.split(';')[0].trim()!=='application/json')throw new InputError('Expected JSON.');
  const length=request.headers.get('content-length');
  if(length&&(!/^\d+$/.test(length)||Number(length)>MAX_BYTES))throw new InputError('Payload too large.');
  if(!request.body)throw new InputError('Empty payload.');
  const reader=request.body.getReader();const chunks:Uint8Array[]=[];let size=0;
  try{
    while(true){const {value,done}=await reader.read();if(done)break;size+=value.byteLength;if(size>MAX_BYTES){await reader.cancel();throw new InputError('Payload too large.');}chunks.push(value);}
    const bytes=new Uint8Array(size);let offset=0;for(const chunk of chunks){bytes.set(chunk,offset);offset+=chunk.byteLength;}
    return JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(bytes));
  }catch(error){if(error instanceof InputError)throw error;throw new InputError('Invalid JSON.');}
  finally{reader.releaseLock();}
}
