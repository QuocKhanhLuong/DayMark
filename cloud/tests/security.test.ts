import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {daysHandler,syncHandler,ownerFrom,verifySyncToken} from '../lib/handlers';
import {validatePayload,readJson,MAX_BYTES} from '../lib/validation';
import {CATEGORIES,TIME_ZONE,todayAt,totalSeconds,periodSummary,daysOfYear,type Day} from '../lib/model';
const origin='https://synthetic.example';
const now=new Date('2026-10-16T17:30:00Z'); // Vietnam Oct 17.
const token='synthetic-test-only-token-value-123456789';
const hash=createHash('sha256').update(token).digest('hex');
const seconds=Object.fromEntries(CATEGORIES.map(c=>[c,c==='coding'?60:0]));
const payload=()=>({schemaVersion:1,timeZone:TIME_ZONE,days:[{date:'2026-10-16',status:'partial',seconds:{...seconds}}]});
const request=(body:unknown=payload(),auth:string|null='Bearer '+token)=>new Request(origin+'/api/sync',{method:'POST',headers:{'content-type':'application/json',...(auth?{authorization:auth}:{})},body:JSON.stringify(body)});

test('owner authorization fails closed for unset, unauthenticated, and different accounts',()=>{
  assert.throws(()=>ownerFrom(null,undefined));assert.throws(()=>ownerFrom(null,'owner'));
  assert.throws(()=>ownerFrom({user:{id:'other'}},'owner'));
  assert.equal(ownerFrom({user:{id:'owner'}},'owner'),'owner');
});
test('read API checks real session owner before any database access',async()=>{
  for(const [session,status] of [[null,401],[{user:{id:'other'}},403]] as const){
    let reads=0;
    const handler=daysHandler({ownerId:'owner',origin,getSession:async()=>session,readDays:async()=>{reads++;throw Error('must not read');}});
    const result=await handler(new Request(origin+'/api/days?year=2026'));
    assert.equal(result.status,status);assert.equal(reads,0);assert.equal(result.headers.get('cache-control'),'private, no-store, max-age=0');
  }
});
test('owner read is scoped to configured ID, with no owner selector accepted',async()=>{
  const handler=daysHandler({ownerId:'owner',origin,now:()=>now,getSession:async()=>({user:{id:'owner'}}),readDays:async(id,year)=>{assert.equal(id,'owner');assert.equal(year,2026);return {schemaVersion:1,timeZone:TIME_ZONE,year,today:'2026-10-17',days:[],lastSyncAt:null};}});
  assert.equal((await handler(new Request(origin+'/api/days?year=2026'))).status,200);
  assert.equal((await handler(new Request(origin+'/api/days?year=2026&owner=other'))).status,400);
  assert.equal((await handler(new Request(origin+'/api/days?year=2026&year=2025'))).status,400);
});
test('unauthenticated, wrong token and cookie-only writes never reach storage',async()=>{
  let writes=0;const handler=syncHandler({origin,ownerId:'owner',tokenHash:hash,writeDays:async()=>{writes++;}});
  assert.equal((await handler(request(payload(),null))).status,401);
  assert.equal((await handler(request(payload(),'Bearer '+'wrong'.repeat(10)))).status,401);
  assert.equal(writes,0);
  assert.throws(()=>verifySyncToken('Bearer '+token,undefined));
});
test('write token cannot be used to read activity',async()=>{
  let reads=0;const handler=daysHandler({ownerId:'owner',origin,getSession:async()=>null,readDays:async()=>{reads++;throw Error();}});
  assert.equal((await handler(new Request(origin+'/api/days',{headers:{authorization:'Bearer '+token}}))).status,401);assert.equal(reads,0);
});
test('valid sync writes exact owner and returns server-generated receipt',async()=>{
  const handler=syncHandler({origin,ownerId:'owner',tokenHash:hash,now:()=>now,writeDays:async(id,days,time)=>{assert.equal(id,'owner');assert.deepEqual(days,payload().days);assert.equal(time,now);}});
  const result=await handler(request());assert.equal(result.status,200);assert.deepEqual(await result.json(),{acceptedDays:1,lastSync:now.toISOString()});
});
test('every schema level rejects extra raw data fields',()=>{
  const cases=[{...payload(),url:'private'}, {...payload(),days:[{...payload().days[0],title:'private'}]}, {...payload(),days:[{...payload().days[0],seconds:{...seconds,url:10}}]}];
  for(const value of cases)assert.throws(()=>validatePayload(value,now));
});
test('dates, duplicate dates, timezone and numeric conservation are validated',()=>{
  const base=payload();
  for(const change of [
    {...base,timeZone:'UTC'}, {...base,schemaVersion:2}, {...base,days:[]},
    {...base,days:Array(367).fill(base.days[0])}, {...base,days:[base.days[0],base.days[0]]},
    ...['2026-02-30','2026-10-18','20261016','1999-12-31'].map(date=>({...base,days:[{...base.days[0],date}]})),
    ...[-1,NaN,Infinity,true,86401].map(coding=>({...base,days:[{...base.days[0],seconds:{...seconds,coding}}]})),
    {...base,days:[{...base.days[0],seconds:{...seconds,coding:86400,reading:1}}]}
  ])assert.throws(()=>validatePayload(change,now));
  assert.equal(todayAt(now),'2026-10-17');
  assert.equal(validatePayload({...base,days:[{...base.days[0],date:'2024-02-29'}]},now).days[0].date,'2024-02-29');
});
test('missing, observed zero and partial remain distinct',()=>{
  const missing={date:'2026-10-16',status:'missing',seconds:null} as Day;
  const zero={date:'2026-10-15',status:'complete',seconds:Object.fromEntries(CATEGORIES.map(c=>[c,0]))} as Day;
  assert.equal(totalSeconds(missing),null);assert.equal(totalSeconds(missing,[]),null);assert.equal(totalSeconds(zero),0);
  const p=validatePayload({schemaVersion:1,timeZone:TIME_ZONE,days:[missing,zero]},now);
  assert.deepEqual(p.days,[missing,zero]);
  assert.throws(()=>validatePayload({...payload(),days:[{...missing,seconds}]},now));
  assert.throws(()=>validatePayload({...payload(),days:[{...zero,seconds:null}]},now));
});
test('cross-year weeks use adjacent dates exactly once',()=>{
  const days=[{date:'2025-12-31',status:'partial',seconds},{date:'2026-01-01',status:'complete',seconds}] as Day[];
  const result=periodSummary(days,'2025-12-29','2026-01-04');
  assert.equal(result.seconds,120);assert.equal(result.knownDays,2);assert.equal(result.missingDays,5);assert.equal(result.partialDays,1);
  assert.equal(daysOfYear(2024).length,366);
});
test('bounded body parser rejects oversize streams and malformed JSON',async()=>{
  const large=new Request(origin,{method:'POST',headers:{'content-type':'application/json'},body:'x'.repeat(MAX_BYTES+1)});
  await assert.rejects(()=>readJson(large));
  await assert.rejects(()=>readJson(new Request(origin,{method:'POST',headers:{'content-type':'application/json'},body:'{"bad"'})));
});
test('cross-site reads and writes are rejected before database access',async()=>{
  let writes=0;const handler=syncHandler({origin,ownerId:'owner',tokenHash:hash,writeDays:async()=>{writes++;}});
  const r=request();r.headers.set('origin','https://attacker.example');
  assert.equal((await handler(r)).status,403);assert.equal(writes,0);
});
test('storage errors redact credentials, private strings and payloads',async()=>{
  const handler=syncHandler({origin,ownerId:'owner',tokenHash:hash,writeDays:async()=>{throw new Error('postgres://SECRET PRIVATE-TITLE');}});
  const result=await handler(request());assert.equal(result.status,503);assert.doesNotMatch(await result.text(),/SECRET|TITLE|postgres/);
});
