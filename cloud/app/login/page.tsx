'use client';
import {useState,type FormEvent} from 'react';
export default function Login(){
  const [busy,setBusy]=useState(false);const [error,setError]=useState('');
  async function submit(event:FormEvent<HTMLFormElement>){
    event.preventDefault();setBusy(true);setError('');
    const data=new FormData(event.currentTarget);
    try{
      const response=await fetch('/api/auth/sign-in/email',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},body:JSON.stringify({email:data.get('email'),password:data.get('password'),rememberMe:false})});
      if(!response.ok)throw new Error(response.status===429?'Please wait a minute before trying again.':'Sign-in failed. Check your email and password.');
      window.location.assign('/');
    }catch(cause){setError(cause instanceof Error?cause.message:'Sign-in is unavailable.');setBusy(false);}
  }
  return <main className="login-shell"><a className="brand" href="/">daymark</a><p className="eyebrow">YOUR PRIVATE ACTIVITY JOURNAL</p><h1>Welcome back.</h1><p>Sign in to see your days take shape.</p><form onSubmit={event=>void submit(event)}><label htmlFor="email">Email</label><input id="email" name="email" type="email" autoComplete="username" required disabled={busy}/><label htmlFor="password">Password</label><input id="password" name="password" type="password" autoComplete="current-password" required disabled={busy}/><button type="submit" disabled={busy}>{busy?'Signing in…':'Sign in'}</button>{error?<p className="error-banner" role="alert">{error}</p>:null}</form><p className="login-note">This journal belongs to one owner. Registration is closed.</p></main>;
}
