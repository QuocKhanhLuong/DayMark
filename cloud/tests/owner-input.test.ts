import test from 'node:test';
import assert from 'node:assert/strict';
import {ownerPassword,OwnerInputError,readHidden} from '../scripts/owner-input';
// Synthetic input only: these are not user credentials.
test('owner must enter twice and explicitly submit before enrollment receives a password',async()=>{
  const prompts:string[]=[];const synthetic='synthetic-user-input-ONLY-123';
  const result=await ownerPassword('synthetic@example.test',async prompt=>{prompts.push(prompt);return synthetic;},async prompt=>{prompts.push(prompt);return 'CREATE';});
  assert.equal(result,synthetic);assert.equal(prompts.length,3);
  assert.match(prompts[1],/Confirm/);assert.match(prompts[2],/CREATE/);
});
test('invalid lengths and mismatch report only safe reasons and allow retry before submission',async()=>{
  const valid='synthetic-first-password';
  const values=['short','x'.repeat(129),valid,'synthetic-other-password',valid,valid];
  const messages:string[]=[];let submissions=0;
  const result=await ownerPassword('synthetic@example.test',async()=>{
    assert.ok(values.length,'Unexpected additional secret prompt');return values.shift()!;
  },async()=>{submissions++;assert.equal(values.length,0);return 'CREATE';},message=>messages.push(message));
  assert.equal(result,valid);assert.equal(submissions,1);assert.equal(messages.length,3);
  assert.match(messages[0],/14–128/);assert.match(messages[1],/14–128/);assert.match(messages[2],/do not match/);
  assert.ok(messages.every(message=>!message.includes(valid)&&!message.includes('synthetic-other-password')&&!message.includes('short')));
});
test('cancelled input and cancelled submission do not return a credential',async()=>{
  await assert.rejects(()=>ownerPassword('synthetic@example.test',async()=>{throw new OwnerInputError('Setup cancelled.');}),OwnerInputError);
  await assert.rejects(()=>ownerPassword('synthetic@example.test',async()=> 'synthetic-first-password',async()=> 'CANCEL'),/No account was submitted/);
});
test('noninteractive password input is rejected before touching stdin',async()=>{
  if(!process.stdin.isTTY)await assert.rejects(()=>readHidden(''),/interactive terminal/);
});
