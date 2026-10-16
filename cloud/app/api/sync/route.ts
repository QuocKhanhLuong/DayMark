import {syncHandler} from '../../../lib/handlers';
import {writeDays} from '../../../lib/db';
export const runtime='nodejs';
export const dynamic='force-dynamic';
export const POST=(request:Request)=>syncHandler({ownerId:process.env.OWNER_USER_ID,origin:process.env.APP_ORIGIN,tokenHash:process.env.SYNC_TOKEN_SHA256,writeDays})(request);
