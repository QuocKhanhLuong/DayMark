'use client';
import {useState} from 'react';
export default function SignOut(){
  const [busy,setBusy]=useState(false);const [error,setError]=useState('');
  async function signOut(){setBusy(true);setError('');try{const r=await fetch('/api/auth/sign-out',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}',credentials:'same-origin'});if(!r.ok)throw new Error();window.location.assign('/login');}catch{setBusy(false);setError('Sign-out failed. Try again.');}}
  return <span><button type="button" disabled={busy} onClick={()=>void signOut()}>{busy?'Signing out…':'Sign out'}</button>{error?<span role="alert">{error}</span>:null}</span>;
}
