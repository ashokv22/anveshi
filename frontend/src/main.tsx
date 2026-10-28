import React, { useState } from 'react';
import { createRoot } from 'react-dom/client';
import './style.css';

type Event = {
  event_id: string;
  timestamp: string;
  service: string;
  level?: string;
  message: string;
  correlation_type: 'direct' | 'discovered';
  depth: number;
  parent_event_id: string | null;
  matched_identifier_key: string;
  matched_identifier_value: string;
};
type Result = {
  identifier_type: string;
  identifier_value: string;
  summary: string;
  events: Event[];
  timeline: Event[];
  findings: {
    event_id: string;
    service: string;
    timestamp: string;
    severity: string;
    evidence: string[];
  }[];
  status: 'no_events' | 'failures_detected' | 'no_failures_detected' | 'incomplete';
  effective_time_window: {
    start: string | null;
    end: string | null;
    duration_minutes: number;
  };
  limitations: string[];
  truncated: boolean;
  correlation_statistics: {
    direct_count: number;
    discovered_count: number;
    total_count: number;
    depth_reached: number;
    max_depth: number;
    max_events: number;
  };
};

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

  const chronologicalEvents = result?.timeline ?? [];
  const participatingServices = [...new Set(result?.events.map(event => event.service) ?? [])].sort();

  return <main><header><span className="eyebrow">APPLICATION INTELLIGENCE ENGINE</span><h1>ANVESHI <span className="version">v0.1</span></h1><p>Investigate applications by identifier, not by guessing which dashboard to open.</p></header>
    <section className="panel"><h2>New investigation</h2><form onSubmit={investigate}><label htmlFor="identifier">Transaction ID</label><div className="search"><input id="identifier" value={identifier} onChange={e => setIdentifier(e.target.value)} required/><button disabled={loading}>{loading ? 'Investigating...' : 'Investigate'}</button></div></form></section>
    {error && <p role="alert" className="error">{error}</p>}
    {result && <section className="panel"><h2>Results</h2><p className="identifier-result">{result.identifier_type} = <strong>{result.identifier_value}</strong></p><span className={`status ${result.status}`}>{result.status.replaceAll('_', ' ')}</span><p className="summary">{result.summary}</p>
      <p className="window">Effective window: {result.effective_time_window.start ? `${new Date(result.effective_time_window.start).toLocaleString()} – ${new Date(result.effective_time_window.end!).toLocaleString()}` : 'Unavailable (no direct match or reference timestamp)'} · {result.effective_time_window.duration_minutes} minutes</p>
      <div className="stats"><div><strong>{result.correlation_statistics.total_count}</strong><span>Correlated events</span></div><div><strong>{participatingServices.length}</strong><span>Services</span></div><div><strong>{result.correlation_statistics.depth_reached}/{result.correlation_statistics.max_depth}</strong><span>Depth reached</span></div></div>
      <p className="services"><strong>Participating services:</strong> {participatingServices.length ? participatingServices.join(', ') : 'None'}</p>
      {result.truncated && <p role="alert" className="warning">Evidence is incomplete: the event limit was reached.</p>}
      <h3>Failure findings ({result.findings.length})</h3>
      {result.findings.length ? <ul className="findings">{result.findings.map(finding => <li key={finding.event_id}><strong>{finding.severity} · {finding.service}</strong> · <code>{finding.event_id}</code><ul>{finding.evidence.map(evidence => <li key={evidence}>{evidence}</li>)}</ul></li>)}</ul> : <p>No configured failure indicators were found. Root cause remains unknown.</p>}
      <h3>Chronological timeline</h3>
      <div className="events">{chronologicalEvents.map(event => <article key={event.event_id}>
        <time>{new Date(event.timestamp).toLocaleString()}</time><div className="event-heading"><strong>{event.service}</strong><span className={`correlation ${event.correlation_type}`}>{event.correlation_type} · depth {event.depth}</span><span className="level">{event.level ?? 'UNKNOWN'}</span></div>
        <p>{event.message}</p><p className="evidence">Matched {event.matched_identifier_key} = {event.matched_identifier_value}{event.parent_event_id && <> · discovered from <code>{event.parent_event_id}</code></>}</p>
      </article>)}</div><h3>Limitations</h3><ul>{result.limitations.map(item => <li key={item}>{item}</li>)}</ul></section>}
    <footer>ANVESHI v0.1 · Synthetic source · Deterministic identifier correlation</footer></main>;
}

createRoot(document.getElementById('root')!).render(<React.StrictMode><App /></React.StrictMode>);
