import {stdin,stdout} from 'node:process';
import {createInterface} from 'node:readline/promises';

/** Only fixed, non-sensitive messages may cross the setup error boundary. */
export class OwnerInputError extends Error {}

/** Read directly from the owner's terminal without echoing their password. */
export function readHidden(prompt:string):Promise<string>{
  if(!stdin.isTTY||!stdout.isTTY)return Promise.reject(new OwnerInputError('A private interactive terminal is required.'));
  stdout.write(prompt);
  const previousRaw=stdin.isRaw;
  stdin.setRawMode(true);
  stdin.resume();
  return new Promise((resolve,reject)=>{
    let value='';
    const finish=(error?:Error)=>{
      stdin.off('data',onData);
      stdin.setRawMode(previousRaw);
      stdin.pause();
      stdout.write('\n');
      if(error)reject(error);else resolve(value);
      value='';
    };
    const onData=(chunk:Buffer)=>{
      for(const character of chunk.toString('utf8')){
        if(character==='\u0003'){finish(new OwnerInputError('Setup cancelled.'));return;}
        if(character==='\r'||character==='\n'){finish();return;}
        if(character==='\u007f'||character==='\b')value=Array.from(value).slice(0,-1).join('');
        else if(character>=' '){value+=character;if(value.length>1024){finish(new OwnerInputError('Input exceeded the terminal limit. Restart setup and use 14–128 characters.'));return;}}
      }
    };
    stdin.on('data',onData);
  });
}

export async function readConfirmation(prompt:string){
  const terminal=createInterface({input:stdin,output:stdout});
  try{return await terminal.question(prompt);}finally{terminal.close();}
}

export async function ownerPassword(email:string,readSecret=readHidden,readLine=readConfirmation,report=(message:string)=>console.log(message)){
  for(;;){
    const first=await readSecret('Choose password (14–128 characters; typing is hidden): ');
    if(first.length<14||first.length>128){
      report('Password must contain 14–128 characters. Please try again (Ctrl+C cancels).');
      continue;
    }
    const second=await readSecret('Confirm password (typing is hidden): ');
    if(first!==second){
      report('Passwords do not match. Please enter both again (Ctrl+C cancels).');
      continue;
    }
    const confirmation=await readLine(`Type CREATE to submit the owner account for ${email}: `);
    if(confirmation!=='CREATE')throw new OwnerInputError('Setup cancelled. No account was submitted.');
    return first;
  }
}
