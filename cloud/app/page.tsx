import {headers} from 'next/headers';
import {redirect} from 'next/navigation';
import Dashboard from '../components/Dashboard';
import {getAuth} from '../lib/auth';
import {ownerFrom} from '../lib/handlers';
import {readDays} from '../lib/db';
import {todayAt} from '../lib/model';
export const dynamic='force-dynamic';
export default async function Page(){
  if(!process.env.OWNER_USER_ID||!process.env.DATABASE_URL||!process.env.BETTER_AUTH_SECRET||!process.env.APP_ORIGIN)return <main className="login-shell"><h1>Daymark</h1><p>Private dashboard setup is in progress.</p></main>;
  let session;
  try{session=await getAuth().api.getSession({headers:await headers()});}catch{return <main className="login-shell"><h1>Daymark</h1><p>Sign-in is temporarily unavailable. Please try again shortly.</p></main>;}
  if(!session)redirect('/login');
  try{ownerFrom(session,process.env.OWNER_USER_ID);}catch{return <main className="login-shell"><h1>Private dashboard</h1><p>This account does not have access.</p><a href="/login">Return to sign in</a></main>;}
  try{
    const now=new Date();const initial=await readDays(process.env.OWNER_USER_ID,Number(todayAt(now).slice(0,4)),now);
    return <Dashboard initial={initial}/>;
  }catch{return <main className="login-shell"><h1>Daymark</h1><p>Activity is temporarily unavailable. No missing totals have been filled in.</p><a href="/">Try again</a></main>;}
}
