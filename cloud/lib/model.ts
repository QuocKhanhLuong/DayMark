export const TIME_ZONE = 'Asia/Ho_Chi_Minh';
export const CATEGORIES = ['coding','github','chatgpt','orca','reading','other'] as const;
export type Category = typeof CATEGORIES[number];
export const CATEGORY_LABELS: Record<Category,string> = {coding:'Coding',github:'GitHub',chatgpt:'ChatGPT',orca:'Orca',reading:'Reading',other:'Other'};
export type Seconds = Record<Category,number>;
export type Day = {date:string;status:'missing'|'partial'|'complete';seconds:Seconds|null;syncedAt?:string};
export type DashboardData = {schemaVersion:1;timeZone:typeof TIME_ZONE;year:number;today:string;days:Day[];lastSyncAt:string|null};
export function todayAt(now=new Date()) {
  const parts=new Intl.DateTimeFormat('en-CA',{timeZone:TIME_ZONE,year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(now);
  return ['year','month','day'].map(k=>parts.find(p=>p.type===k)!.value).join('-');
}
export function validDate(value:unknown): value is string {
  if(typeof value!=='string'||!/^\d{4}-\d{2}-\d{2}$/.test(value))return false;
  const d=new Date(value+'T00:00:00Z');
  return Number.isFinite(d.getTime())&&d.toISOString().slice(0,10)===value&&value>='2000-01-01'&&value<='2100-12-31';
}
export function daysOfYear(year:number) {
  const out:string[]=[];
  for(let d=new Date(Date.UTC(year,0,1,12));d.getUTCFullYear()===year;d.setUTCDate(d.getUTCDate()+1))out.push(d.toISOString().slice(0,10));
  return out;
}
export function totalSeconds(day:Day,categories:readonly Category[]=CATEGORIES):number|null {
  if(day.status==='missing'||day.seconds===null)return null;
  return categories.reduce((s,c)=>s+day.seconds![c],0);
}
export function formatDuration(seconds:number) {
  if(seconds===0)return '0m';
  if(seconds<60)return '<1m';
  const m=Math.floor(seconds/60),h=Math.floor(m/60);
  return h?`${h}h${m%60?` ${m%60}m`:''}`:`${m}m`;
}
export function periodSummary(days:Day[],from:string,to:string,categories:readonly Category[]=CATEGORIES) {
  const byDate=new Map(days.map(d=>[d.date,d]));
  let knownDays=0,missingDays=0,partialDays=0,seconds=0;
  if(from>to)return {knownDays,missingDays,partialDays,seconds:null};
  for(const d=new Date(from+'T12:00:00Z');d.toISOString().slice(0,10)<=to;d.setUTCDate(d.getUTCDate()+1)){
    const day=byDate.get(d.toISOString().slice(0,10));
    const value=day?totalSeconds(day,categories):null;
    if(value===null){missingDays++;continue;}
    knownDays++;seconds+=value;
    if(day?.status==='partial')partialDays++;
  }
  return {knownDays,missingDays,partialDays,seconds:knownDays?seconds:null};
}
