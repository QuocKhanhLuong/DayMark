import {daysHandler} from '../../../lib/handlers';
import {getAuth} from '../../../lib/auth';
import {readDays} from '../../../lib/db';
export const runtime='nodejs';
export const dynamic='force-dynamic';
export const GET=(request:Request)=>daysHandler({ownerId:process.env.OWNER_USER_ID,origin:process.env.APP_ORIGIN,getSession:headers=>getAuth().api.getSession({headers}),readDays})(request);
