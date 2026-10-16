import type {BetterAuthOptions} from 'better-auth';
export function authOptions(origin:string,secret:string,bootstrap=false):BetterAuthOptions{
  if(secret.length<32)throw new Error('Authentication secret is missing.');
  const parsed=new URL(origin);
  if(parsed.origin!==origin||!(parsed.protocol==='https:'||(parsed.protocol==='http:'&&parsed.hostname==='127.0.0.1')))throw new Error('Invalid app origin.');
  return {
    appName:'Daymark',baseURL:origin,secret,
    trustedOrigins:[origin],
    emailAndPassword:{enabled:true,disableSignUp:!bootstrap,autoSignIn:false,minPasswordLength:14,maxPasswordLength:128},
    user:{changeEmail:{enabled:false},deleteUser:{enabled:false}},
    account:{accountLinking:{enabled:false}},
    session:{expiresIn:12*60*60,updateAge:60*60,cookieCache:{enabled:false}},
    rateLimit:{enabled:true,storage:'database',window:60,max:30,customRules:{'/sign-in/email':{window:60,max:5}}},
    advanced:{ipAddress:{disableIpTracking:true}},
    logger:{disabled:true},
    telemetry:{enabled:false},
    databaseHooks:{
      user:{create:{before:async()=>bootstrap?undefined:false}},
      session:{create:{before:async(data)=>({data:{...data,ipAddress:null,userAgent:null}})}}
    }
  };
}
