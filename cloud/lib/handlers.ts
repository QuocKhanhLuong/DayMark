import {createHash,timingSafeEqual} from 'node:crypto';
import {TIME_ZONE,todayAt,type DashboardData,type Day} from './model';
import {InputError,readJson,validatePayload} from './validation';
export type Session={user:{id:string}}|null;
export class AccessError extends Error{constructor(public status:number){super('Access denied.');}}
export function ownerFrom(session:Session,ownerId:string|undefined){
  if(!ownerId)throw new AccessError(503);
  if(!session?.user?.id)throw new AccessError(401);
  if(session.user.id!==ownerId)throw new AccessError(403);
  return ownerId;
}
export function json(data:unknown,status=200){return Response.json(data,{status,headers:{'Cache-Control':'private, no-store, max-age=0','Vary':'Cookie','X-Content-Type-Options':'nosniff'}});}
export function errorResponse(error:unknown){
  if(error instanceof AccessError)return json({error:error.status===503?'Owner setup is incomplete.':'Unauthorized.'},error.status);
  if(error instanceof InputError)return json({error:error.message},400);
  return json({error:'This request could not be completed.'},503);
}
export function sameOrigin(request:Request,origin:string|undefined){
  if(!origin)throw new AccessError(503);
  if(request.headers.get('sec-fetch-site')==='cross-site'||(request.headers.has('origin')&&request.headers.get('origin')!==origin))throw new AccessError(403);
}
export function verifySyncToken(authorization:string|null,expected:string|undefined){
  if(!expected||! /^[a-f0-9]{64}$/.test(expected))throw new AccessError(503);
  const match=authorization?.match(/^Bearer ([A-Za-z0-9_-]{32,128})$/);
  if(!match)throw new AccessError(401);
  const actual=createHash('sha256').update(match[1]).digest();
  if(!timingSafeEqual(actual,Buffer.from(expected,'hex')))throw new AccessError(401);
}
export function daysHandler(deps:{ownerId?:string;origin?:string;getSession:(headers:Headers)=>Promise<Session>;readDays:(ownerId:string,year:number,now:Date)=>Promise<DashboardData>;now?:()=>Date}){
  return async(request:Request)=>{
    try{
      sameOrigin(request,deps.origin);
      const owner=ownerFrom(await deps.getSession(request.headers),deps.ownerId);
      const now=deps.now?.()??new Date();
      const params=new URL(request.url).searchParams;
      if([...params.keys()].some(key=>key!=='year')||params.getAll('year').length>1)throw new InputError('Only one year is accepted.');
      const value=params.get('year')??todayAt(now).slice(0,4);
      if(!/^\d{4}$/.test(value)||Number(value)<2000||Number(value)>2100)throw new InputError('Invalid year.');
      return json(await deps.readDays(owner,Number(value),now));
    }catch(error){return errorResponse(error);}
  };
}
export function syncHandler(deps:{ownerId?:string;origin?:string;tokenHash?:string;writeDays:(ownerId:string,days:Day[],now:Date)=>Promise<void>;now?:()=>Date}){
  return async(request:Request)=>{
    try{
      sameOrigin(request,deps.origin);
      if(!deps.ownerId)throw new AccessError(503);
      verifySyncToken(request.headers.get('authorization'),deps.tokenHash);
      if(new URL(request.url).search)throw new InputError('No query parameters are accepted.');
      const now=deps.now?.()??new Date();
      const payload=validatePayload(await readJson(request),now);
      await deps.writeDays(deps.ownerId,payload.days,now);
      return json({acceptedDays:payload.days.length,lastSync:now.toISOString()});
    }catch(error){return errorResponse(error);}
  };
}
