import {Pool} from 'pg';
import {attachDatabasePool} from '@vercel/functions';
import {CATEGORIES,TIME_ZONE,todayAt,type DashboardData,type Day,type Seconds} from './model';
let pool:Pool|undefined;
export function getPool(){
  if(!pool){
    if(!process.env.DATABASE_URL)throw new Error('Database configuration is missing.');
    pool=new Pool({connectionString:process.env.DATABASE_URL,max:3,idleTimeoutMillis:10000,connectionTimeoutMillis:10000});
    pool.on('error',()=>{});
    if(process.env.VERCEL)attachDatabasePool(pool);
  }
  return pool;
}
export async function readDays(ownerId:string,year:number,now:Date):Promise<DashboardData>{
  const db=getPool();
  const start=new Date(Date.UTC(year,0,-6)).toISOString().slice(0,10);
  const end=new Date(Date.UTC(year+1,0,8)).toISOString().slice(0,10);
  const [records,lastSync]=await Promise.all([
    db.query('SELECT day::text, status, coding_seconds, github_seconds, chatgpt_seconds, orca_seconds, reading_seconds, other_seconds, synced_at FROM daymark_daily WHERE owner_id=$1 AND day >= $2::date AND day < $3::date ORDER BY day',[ownerId,start,end]),
    db.query('SELECT max(synced_at) AS last_sync FROM daymark_daily WHERE owner_id=$1',[ownerId])
  ]);
  const days:Day[]=records.rows.map(row=>{
    const seconds=row.status==='missing'?null:Object.fromEntries(CATEGORIES.map(c=>[c,Number(row[c+'_seconds'])])) as Seconds;
    return {date:row.day,status:row.status,seconds,syncedAt:new Date(row.synced_at).toISOString()};
  });
  return {schemaVersion:1,timeZone:TIME_ZONE,year,today:todayAt(now),days,lastSyncAt:lastSync.rows[0]?.last_sync?new Date(lastSync.rows[0].last_sync).toISOString():null};
}
export async function writeDays(ownerId:string,days:Day[],now:Date){
  const db=await getPool().connect();
  try{
    await db.query('BEGIN');
    const values:unknown[]=[];
    const rows=days.map(day=>{
      const row=[ownerId,day.date,day.status,...CATEGORIES.map(c=>day.seconds?.[c]??null),now.toISOString()];
      const start=values.length;values.push(...row);
      return '('+row.map((_,i)=>'$'+(start+i+1)).join(',')+')';
    });
    await db.query(`INSERT INTO daymark_daily (owner_id,day,status,coding_seconds,github_seconds,chatgpt_seconds,orca_seconds,reading_seconds,other_seconds,synced_at) VALUES ${rows.join(',')} ON CONFLICT (owner_id,day) DO UPDATE SET status=excluded.status,coding_seconds=excluded.coding_seconds,github_seconds=excluded.github_seconds,chatgpt_seconds=excluded.chatgpt_seconds,orca_seconds=excluded.orca_seconds,reading_seconds=excluded.reading_seconds,other_seconds=excluded.other_seconds,synced_at=excluded.synced_at`,values);
    await db.query('COMMIT');
  }catch{await db.query('ROLLBACK');throw new Error('Aggregate storage failed.');}
  finally{db.release();}
}
