/** User-run offline owner setup. Excluded from deployments; never run by the agent. */
import {betterAuth,type BetterAuthOptions} from 'better-auth';
import {readFile,writeFile} from 'node:fs/promises';
import {authOptions} from '../lib/auth-options';
import {getPool} from '../lib/db';
import {ownerPassword,OwnerInputError} from './owner-input';
async function main(){
  if(!process.stdin.isTTY||!process.stdout.isTTY||process.env.DAYMARK_OWNER_PASSWORD)throw new Error('Owner setup requires user-controlled terminal input.');
  const settings=JSON.parse(await readFile(new URL('../../.runtime/owner-settings.json',import.meta.url),'utf8'));
  const email=settings.email,origin=process.env.APP_ORIGIN,secret=process.env.BETTER_AUTH_SECRET;
  if(typeof email!=='string'||!email.includes('@')||!origin||!secret)throw new Error('Missing owner setup configuration.');
  const pool=getPool();
  const lock=await pool.connect();
  try{
    await lock.query('SELECT pg_advisory_lock(194891247)');
    const existing=await lock.query('SELECT id FROM "user" LIMIT 1');
    if(existing.rowCount)throw new Error('Owner already exists; duplicate enrollment refused.');
    console.log(`Set up your private Daymark account: ${email}`);
    const password=await ownerPassword(email);
    const options:BetterAuthOptions={...authOptions(origin,secret,true),database:pool};
    const result=await betterAuth(options).api.signUpEmail({body:{email,password,name:'Owner'}});
    if(!result.user.id)throw new Error('Enrollment not confirmed.');
    await writeFile(new URL('../../.runtime/owner-id.json',import.meta.url),JSON.stringify({ownerId:result.user.id})+'\n',{mode:0o600});
    console.log('Owner account created. Your password was not saved or printed.');
  }finally{
    await lock.query('SELECT pg_advisory_unlock(194891247)');
    lock.release();
    await pool.end();
  }
}
main().catch(error=>{
  console.error(error instanceof OwnerInputError?error.message:'Owner setup was not completed. No password or upstream error details were logged.');
  process.exitCode=1;
});
