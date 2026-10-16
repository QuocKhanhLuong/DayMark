import {getAuth} from '../../../../lib/auth';
import {json,sameOrigin,errorResponse,AccessError} from '../../../../lib/handlers';
export const runtime='nodejs';
export const dynamic='force-dynamic';
const allowed=new Map([['GET',new Set(['/get-session'])],['POST',new Set(['/sign-in/email','/sign-out'])]]);
async function handle(request:Request){
  try{
    sameOrigin(request,process.env.APP_ORIGIN);
    const path=new URL(request.url).pathname.slice('/api/auth'.length);
    if(!allowed.get(request.method)?.has(path))return json({error:'Not found.'},404);
    if(!process.env.OWNER_USER_ID)throw new AccessError(503);
    return await getAuth().handler(request);
  }catch(error){return errorResponse(error);}
}
export {handle as GET,handle as POST};
