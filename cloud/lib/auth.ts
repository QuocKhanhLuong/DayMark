import {betterAuth,type BetterAuthOptions} from 'better-auth';
import {getPool} from './db';
import {authOptions} from './auth-options';
let auth:ReturnType<typeof betterAuth>|undefined;
export function getAuth(){
  if(!auth){
    const origin=process.env.APP_ORIGIN,secret=process.env.BETTER_AUTH_SECRET;
    if(!origin||!secret)throw new Error('Authentication setup is incomplete.');
    const options:BetterAuthOptions={...authOptions(origin,secret),database:getPool()};
    auth=betterAuth(options);
  }
  return auth!;
}
