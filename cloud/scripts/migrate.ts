import {getMigrations} from 'better-auth/db/migration';
import {writeFile,readFile} from 'node:fs/promises';
import {getPool} from '../lib/db';
import {authOptions} from '../lib/auth-options';
async function main(){
  const origin=process.env.APP_ORIGIN,secret=process.env.BETTER_AUTH_SECRET;
  if(!origin||!secret)throw new Error('Missing migration configuration.');
  const pool=getPool();
  const plan=await getMigrations({...authOptions(origin,secret),database:pool});
  if(plan.unsafeChanges.length||plan.schemaProblems.length)throw new Error('Unsafe migration refused.');
  const sql=await plan.compileMigrations();
  if(sql.trim())await writeFile(new URL('../db/001-auth.sql',import.meta.url),sql+'\n');
  await plan.runMigrations();
  await pool.query(await readFile(new URL('../db/002-activity.sql',import.meta.url),'utf8'));
  await pool.end();
  console.log('Authentication and aggregate schema ready.');
}
main().catch(()=>{console.error('Migration failed. Configuration and database errors were redacted.');process.exitCode=1;});
