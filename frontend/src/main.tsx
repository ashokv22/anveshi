import React, { useState } from 'react';
import { createRoot } from 'react-dom/client';
import './style.css';

type Event = { event_id: string; timestamp: string; service: string; level?: string; message: string };
type Result = { summary: string; events: Event[]; limitations: string[] };

function App() {
  const [identifier, setIdentifier] = useState('txn-123');
  const [result, setResult] = useState<Result | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function investigate(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true); setError(''); setResult(null);
    try {
      const response = await fetch('/api/v1/investigations', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ identifier_type: 'transaction_id', identifier_value: identifier }) });
      if (!response.ok) throw new Error(`Investigation failed: HTTP ${response.status}`);
      setResult(await response.json() as Result);
    } catch (err) { setError(err instanceof Error ? err.message : 'Unknown error'); }
    finally { setLoading(false); }
  }

  return <main><header><span className="eyebrow">APPLICATION INTELLIGENCE ENGINE</span><h1>ANVESHI <span className="version">v0.1</span></h1><p>Investigate applications by identifier, not by guessing which dashboard to open.</p></header>
    <section className="panel"><h2>New investigation</h2><form onSubmit={investigate}><label htmlFor="identifier">Transaction ID</label><div className="search"><input id="identifier" value={identifier} onChange={e => setIdentifier(e.target.value)} required/><button disabled={loading}>{loading ? 'Investigating...' : 'Investigate'}</button></div></form></section>
    {error && <p role="alert" className="error">{error}</p>}
    {result && <section className="panel"><h2>Results</h2><p>{result.summary}</p><div className="events">{result.events.map(event => <article key={event.event_id}><time>{new Date(event.timestamp).toLocaleString()}</time><strong>{event.service}</strong><span className="level">{event.level ?? 'UNKNOWN'}</span><p>{event.message}</p></article>)}</div><h3>Limitations</h3><ul>{result.limitations.map(item => <li key={item}>{item}</li>)}</ul></section>}
    <footer>Day 1 skeleton · Synthetic source only · No correlation yet</footer></main>;
}

createRoot(document.getElementById('root')!).render(<React.StrictMode><App /></React.StrictMode>);
