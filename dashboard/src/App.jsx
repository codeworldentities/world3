import React, { useState, useEffect, useRef, useCallback } from 'react';
import { io } from 'socket.io-client';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { drawAvatar } from './avatarGenerator';
import { EntityProfileCard } from './EntityProfileCard';

const API = '';
const socket = io(API, {
  transports: ['polling'],
  upgrade: false,
  reconnection: true,
  reconnectionAttempts: Infinity,
  reconnectionDelay: 1000,
  reconnectionDelayMax: 5000,
  timeout: 20000,
});

const TYPE_INFO = {
  Developer:   { icon: '\u{1F4BB}', color: '#58a6ff' },
  Bug:         { icon: '\u{1F41B}', color: '#f85149' },
  Refactorer:  { icon: '\u{1F527}', color: '#d29922' },
  'AI Copilot':{ icon: '\u{1F916}', color: '#bc8cff' },
  Senior:      { icon: '\u{2B50}',  color: '#ffd700' },
  Intern:      { icon: '\u{1F331}', color: '#3fb950' },
  'Web Scout': { icon: '\u{1F310}', color: '#7ee7ff' },
  Judge:       { icon: '\u{2696}',  color: '#888' },
  Teacher:     { icon: '\u{1F4D6}', color: '#f778ba' },
};

function typeInfo(t) { return TYPE_INFO[t] || { icon: '\u{2753}', color: '#888' }; }
function energyColor(e) { return e > 0.6 ? '#3fb950' : e > 0.3 ? '#d29922' : '#f85149'; }
function qualityColor(q) { return q >= 0.8 ? '#3fb950' : q >= 0.5 ? '#d29922' : '#f85149'; }

/* Mini avatar component for entity list */
function MiniAvatar({ entityId, typeColor, size = 32 }) {
  const ref = useRef(null);
  useEffect(() => {
    const c = ref.current;
    if (!c) return;
    c.width = size;
    c.height = size;
    const ctx = c.getContext('2d');
    ctx.clearRect(0, 0, size, size);
    drawAvatar(ctx, size / 2, size / 2, size, entityId, typeColor);
  }, [entityId, typeColor, size]);
  return <canvas ref={ref} width={size} height={size} style={{ width: size, height: size, borderRadius: '50%', flexShrink: 0 }} />;
}

async function fetchJson(url) {
  try { const r = await fetch(url); return r.ok ? await r.json() : null; }
  catch { return null; }
}

export default function App() {
  const canvasRef = useRef(null);
  const [status, setStatus] = useState({});
  const [entities, setEntities] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [detail, setDetail] = useState(null);
  const [tab, setTab] = useState('entities');
  const [paused, setPaused] = useState(false);
  const [speed, setSpeed] = useState(1);
  const [events, setEvents] = useState([]);
  const [settlements, setSettlements] = useState([]);
  const [code, setCode] = useState([]);
  const [popHistory, setPopHistory] = useState([]);
  const [completedProjects, setCompletedProjects] = useState([]);
  const [chatMessages, setChatMessages] = useState([]);
  const [chatInput, setChatInput] = useState('');
  const [chatLoading, setChatLoading] = useState(false);
  const chatEndRef = useRef(null);
  const [socketConnected, setSocketConnected] = useState(socket.connected);
  const [projectFiles, setProjectFiles] = useState(null);
  const [viewingFile, setViewingFile] = useState(null);
  const [editorFile, setEditorFile] = useState(null);
  const [editorContent, setEditorContent] = useState('');
  const [ghToken, setGhToken] = useState('');
  const [ghStatus, setGhStatus] = useState(null);
  const [ghMsg, setGhMsg] = useState('');
  const [reqName, setReqName] = useState('');
  const [reqDesc, setReqDesc] = useState('');
  const [reqStack, setReqStack] = useState([]);
  const [reqFiles, setReqFiles] = useState(30);
  const [reqMsg, setReqMsg] = useState('');
  const [queue, setQueue] = useState([]);
  const [souls, setSouls] = useState([]);
  const [soulsLoading, setSoulsLoading] = useState(false);
  const [portals, setPortals] = useState([]);
  const [llmProviders, setLlmProviders] = useState([]);
  const [llmConfig, setLlmConfig] = useState({});
  const [llmMsg, setLlmMsg] = useState('');
  const [llmTesting, setLlmTesting] = useState(false);
  const [llmTestResult, setLlmTestResult] = useState(null);

  /* --- Data fetching --- */
  const fetchStatus = useCallback(async () => {
    const d = await fetchJson('/api/status');
    if (d) { setStatus(d); setPaused(!!d.paused); if (d.speed) setSpeed(d.speed); }
  }, []);
  const fetchEntities = useCallback(async () => {
    const d = await fetchJson('/api/entities?limit=500');
    if (d?.entities) setEntities(d.entities);
  }, []);
  const fetchEntity = useCallback(async (id) => {
    const d = await fetchJson(`/api/entity/${id}`);
    if (d && !d.error) setDetail(d);
  }, []);
  const fetchSettlements = useCallback(async () => {
    const d = await fetchJson('/api/settlements');
    if (d?.settlements) setSettlements(d.settlements);
  }, []);
  const fetchEvents = useCallback(async () => {
    const d = await fetchJson('/api/events?limit=40');
    if (d?.events) setEvents(d.events);
  }, []);
  const fetchPopulation = useCallback(async () => {
    const d = await fetchJson('/api/population');
    if (d?.total) {
      setPopHistory((d.total || []).map((_, i) => ({
        tick: i, total: d.total[i] || 0,
        developer: (d.developer || [])[i] || 0,
        bug: (d.bug || [])[i] || 0,
        refactorer: (d.refactorer || [])[i] || 0,
        copilot: (d.copilot || [])[i] || 0,
        senior: (d.senior || [])[i] || 0,
        intern: (d.intern || [])[i] || 0,
      })));
    }
  }, []);
  const fetchCode = useCallback(async () => {
    const d = await fetchJson('/api/code');
    if (d?.snippets) setCode(d.snippets);
  }, []);
  const fetchCompletedProjects = useCallback(async () => {
    const d = await fetchJson('/api/completed-projects');
    if (d?.projects) setCompletedProjects(d.projects);
  }, []);
  const fetchSouls = useCallback(async () => {
    setSoulsLoading(true);
    const d = await fetchJson('/api/souls');
    if (d?.souls) setSouls(d.souls);
    setSoulsLoading(false);
  }, []);
  const fetchProjectFiles = useCallback(async (id) => {
    const d = await fetchJson(`/api/project/${id}/files`);
    if (d) setProjectFiles(d);
  }, []);
  const fetchPortals = useCallback(async () => {
    const d = await fetchJson('/api/portals');
    if (d?.portals) setPortals(d.portals);
  }, []);
  const fetchGhStatus = useCallback(async () => {
    const d = await fetchJson('/api/github/status');
    if (d) setGhStatus(d);
  }, []);
  const fetchQueue = useCallback(async () => {
    const d = await fetchJson('/api/project/queue');
    if (d?.queue) setQueue(d.queue);
  }, []);
  const fetchLlmConfig = useCallback(async () => {
    const d = await fetchJson('/api/llm/config');
    if (d) {
      if (d.config) setLlmConfig(d.config);
      if (d.providers) setLlmProviders(d.providers);
    }
  }, []);
  const saveLlmConfig = useCallback(async (changes) => {
    setLlmMsg('');
    try {
      const r = await fetch('/api/llm/config', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(changes) });
      const d = await r.json();
      if (d.ok !== false && d.config) { setLlmConfig(d.config); setLlmMsg('Saved'); }
      else setLlmMsg(d.error || 'Error');
    } catch { setLlmMsg('Connection error'); }
  }, []);
  const testLlm = useCallback(async () => {
    setLlmTesting(true); setLlmTestResult(null);
    try {
      const r = await fetch('/api/llm/test', { method: 'POST' });
      const d = await r.json();
      setLlmTestResult(d);
    } catch { setLlmTestResult({ ok: false, error: 'Connection error' }); }
    setLlmTesting(false);
  }, []);

  /* Polling */
  useEffect(() => {
    fetchStatus(); fetchEntities(); fetchEvents(); fetchPortals(); fetchGhStatus(); fetchQueue(); fetchLlmConfig();
    const iv = setInterval(() => { fetchStatus(); fetchEntities(); fetchEvents(); }, 2000);
    const slow = setInterval(() => { fetchSettlements(); fetchPopulation(); fetchCode(); fetchCompletedProjects(); fetchPortals(); }, 5000);
    socket.on('world_tick', (d) => { if (d) { setPaused(d.paused); setSpeed(d.speed); } });
    socket.on('events', (d) => { if (d) setEvents(prev => [...d, ...prev].slice(0, 60)); });
    socket.on('connect', () => setSocketConnected(true));
    socket.on('disconnect', () => setSocketConnected(false));
    return () => { clearInterval(iv); clearInterval(slow); socket.off('world_tick'); socket.off('events'); socket.off('connect'); socket.off('disconnect'); };
  }, [fetchStatus, fetchEntities, fetchEvents, fetchSettlements, fetchPopulation, fetchCode, fetchCompletedProjects, fetchPortals]);

  /* selected entity */
  useEffect(() => {
    if (!selectedId) { setDetail(null); return; }
    fetchEntity(selectedId);
  }, [selectedId, fetchEntity]);

  /* Canvas drawing */
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const container = canvas.parentElement;
    if (!container) return;
    canvas.width = container.clientWidth;
    canvas.height = container.clientHeight;
    const ctx = canvas.getContext('2d');
    const W = canvas.width, H = canvas.height;

    // Use actual world dimensions from status API
    const worldW = status.world_width || 6000;
    const worldH = status.world_height || 4000;

    ctx.fillStyle = '#0a0e14';
    ctx.fillRect(0, 0, W, H);

    // Subtle dot grid
    const dotSpacing = 50;
    ctx.fillStyle = 'rgba(48, 54, 61, 0.35)';
    for (let gx = dotSpacing; gx < W; gx += dotSpacing) {
      for (let gy = dotSpacing; gy < H; gy += dotSpacing) {
        ctx.fillRect(gx, gy, 1, 1);
      }
    }

    // Portals
    portals.forEach((p) => {
      if (p.x == null || p.y == null) return;
      const px = (p.x / worldW) * W;
      const py = (p.y / worldH) * H;
      ctx.save();
      ctx.globalAlpha = 0.6;
      // Glow
      const grd = ctx.createRadialGradient(px, py, 0, px, py, 20);
      grd.addColorStop(0, '#bc8cff');
      grd.addColorStop(1, 'transparent');
      ctx.fillStyle = grd;
      ctx.fillRect(px - 20, py - 20, 40, 40);
      // Diamond
      ctx.globalAlpha = 0.9;
      ctx.fillStyle = '#bc8cff';
      ctx.beginPath();
      ctx.moveTo(px, py - 8);
      ctx.lineTo(px + 6, py);
      ctx.lineTo(px, py + 8);
      ctx.lineTo(px - 6, py);
      ctx.closePath();
      ctx.fill();
      ctx.restore();
      // Label
      if (p.name || p.platform) {
        ctx.fillStyle = '#8b949e';
        ctx.font = '9px monospace';
        ctx.textAlign = 'center';
        ctx.fillText(p.name || p.platform || '', px, py + 16);
      }
    });

    // Entities
    entities.forEach((e) => {
      if (!e.alive) return;
      const x = (e.x / worldW) * W;
      const y = (e.y / worldH) * H;
      const info = typeInfo(e.type);
      const r = 5;
      const c = info.color;
      // Expand 3-digit hex to 6-digit for alpha append
      const hex6 = c.length === 4 ? '#' + c[1]+c[1]+c[2]+c[2]+c[3]+c[3] : c;
      // Glow
      ctx.save();
      const glow = ctx.createRadialGradient(x, y, 0, x, y, r * 3);
      glow.addColorStop(0, hex6 + '40');
      glow.addColorStop(1, 'transparent');
      ctx.fillStyle = glow;
      ctx.fillRect(x - r * 3, y - r * 3, r * 6, r * 6);
      // Dot
      ctx.beginPath();
      ctx.arc(x, y, r, 0, Math.PI * 2);
      ctx.fillStyle = c;
      ctx.globalAlpha = 0.9;
      ctx.fill();
      // Inner highlight
      ctx.beginPath();
      ctx.arc(x - 1, y - 1, r * 0.4, 0, Math.PI * 2);
      ctx.fillStyle = 'rgba(255,255,255,0.4)';
      ctx.fill();
      ctx.restore();
      if (e.id === selectedId) {
        ctx.strokeStyle = '#ffd700';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(x, y, r + 4, 0, Math.PI * 2);
        ctx.stroke();
      }
    });
  }, [entities, portals, selectedId, status]);

  const handleCanvasClick = (e) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const cx = e.clientX - rect.left;
    const cy = e.clientY - rect.top;
    const worldW = status.world_width || 6000;
    const worldH = status.world_height || 4000;
    let nearest = null, minDist = 25;
    entities.forEach((ent) => {
      if (!ent.alive) return;
      const ex = (ent.x / worldW) * canvas.width;
      const ey = (ent.y / worldH) * canvas.height;
      const dist = Math.sqrt((cx - ex) ** 2 + (cy - ey) ** 2);
      if (dist < minDist) { minDist = dist; nearest = ent.id; }
    });
    if (nearest) setSelectedId(nearest);
  };

  /* Controls */
  const togglePause = async () => {
    const d = await fetchJson('/api/control');
    const newPaused = !(d?.paused ?? paused);
    await fetch('/api/control', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ paused: newPaused }) });
    setPaused(newPaused);
  };
  const changeSpeed = async (s) => {
    await fetch('/api/control', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ speed: s }) });
    setSpeed(s);
  };
  const doReset = async () => {
    if (!window.confirm('Reset world?')) return;
    await fetch('/api/reset', { method: 'POST' });
    fetchStatus(); fetchEntities();
  };

  /* Chat */
  const sendChat = async () => {
    if (!chatInput.trim() || !selectedId) return;
    const msg = chatInput.trim();
    setChatInput('');
    setChatMessages(prev => [...prev, { role: 'user', text: msg }]);
    setChatLoading(true);
    try {
      const res = await fetch('/api/chat', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ entity_id: selectedId, message: msg }) });
      const d = await res.json();
      setChatMessages(prev => [...prev, { role: 'assistant', text: d.response || d.error || 'No response' }]);
    } catch { setChatMessages(prev => [...prev, { role: 'assistant', text: 'Connection error' }]); }
    setChatLoading(false);
  };

  const S = status || {};
  const aliveEntities = entities.filter(e => e.alive);

  return (
    <div className="app">
      {/* ===== HEADER ===== */}
      <div className="header">
        <div className="brand">
          <div className="brand-mark" />
          <div className="brand-title">
            <span className="name"><b>CODE</b> WORLD</span>
            <span className="ver">v3.0</span>
          </div>
        </div>

        <div className="stats-bar">
          <div className="stat"><span className="dot" style={{ background: '#58a6ff' }} /> Tick: <span className="val">{S.tick || 0}</span></div>
          <div className="stat">{'\u{1F4BB}'} <span className="val">{S.entities || 0}</span></div>
          <div className="stat">{'\u{1F3D7}'} <span className="val">{S.settlements || 0}</span></div>
          <div className="stat">{'\u{1F4BB}'} <span className="val">{S.total_code_generated || 0}</span></div>
          <div className="stat">{'\u{1F41B}'}{'\u{2192}'}{'\u{1F527}'} <span className="val">{S.total_bug_reports || 0}</span></div>
          <div className="stat">{'\u{1F4DA}'} <span className="val">{S.knowledge_discovered || 0}</span></div>
          {S.brain && <div className="stat" title="LLM connected">{'\u{1F9E0}'} <span className="val" style={{ color: S.brain.connected ? '#3fb950' : '#f85149' }}>{S.brain.connected ? '\u{25CF}' : '\u{25CB}'}</span></div>}
          {S.github && <div className="stat" title={`GitHub: ${S.github?.user || '\u{2014}'}`}>{'\u{1F419}'} <span className="val" style={{ color: S.github.enabled ? '#3fb950' : '#f85149' }}>{S.github.enabled ? '\u{25CF}' : '\u{25CB}'}</span> {S.github.queue_size > 0 && <span style={{ fontSize: 10, color: '#d29922' }}>({S.github.queue_size})</span>}</div>}
        </div>

        <div className="controls">
          {paused
            ? <button className="ctrl-start" onClick={togglePause} title="Start">{'\u{25B6}'} Start</button>
            : <button className="ctrl-pause" onClick={togglePause} title="Pause">{'\u{23F8}'} Pause</button>
          }
          <button className="ctrl-reset" onClick={doReset} title="Restart">{'\u{1F504}'} Reset</button>
          <span className="speed-sep">|</span>
          {[1, 2, 4, 8, 16].map(s => (
            <button key={s} onClick={() => changeSpeed(s)} className={`speed-btn ${speed === s ? 'active' : ''}`}>{s}x</button>
          ))}
          <span className={`sim-status ${paused ? 'paused' : 'running'}`}>
            {paused ? '\u{23F9} Stopped' : '\u{25CF} Running'}
          </span>
        </div>
      </div>

      {/* ===== MAIN ===== */}
      <div className="main">
        {/* SIDEBAR */}
        <div className="sidebar">
          <div className="tab-bar">
            <button className={tab === 'entities' ? 'active' : ''} onClick={() => setTab('entities')}><span className="tab-ico">{'\u{1F465}'}</span><span className="tab-lbl">Entities</span></button>
            <button className={tab === 'projects' ? 'active' : ''} onClick={() => setTab('projects')}><span className="tab-ico">{'\u{1F680}'}</span><span className="tab-lbl">Projects</span></button>
            <button className={tab === 'code' ? 'active' : ''} onClick={() => setTab('code')}><span className="tab-ico">{'\u{1F4DD}'}</span><span className="tab-lbl">Code</span></button>
            <button className={tab === 'files' ? 'active' : ''} onClick={() => setTab('files')}><span className="tab-ico">{'\u{1F4C1}'}</span><span className="tab-lbl">Files</span></button>
            <button className={tab === 'editor' ? 'active' : ''} onClick={() => setTab('editor')}><span className="tab-ico">{'\u{270F}'}</span><span className="tab-lbl">Editor</span></button>
            <button className={tab === 'chat' ? 'active' : ''} onClick={() => setTab('chat')}><span className="tab-ico">{'\u{1F4AC}'}</span><span className="tab-lbl">Chat</span></button>
            <button className={tab === 'souls' ? 'active' : ''} onClick={() => { setTab('souls'); if (souls.length === 0) fetchSouls(); }}><span className="tab-ico">{'\u{1F56F}'}</span><span className="tab-lbl">Souls</span></button>
            <button className={tab === 'settings' ? 'active' : ''} onClick={() => setTab('settings')}><span className="tab-ico">{'\u{2699}'}</span><span className="tab-lbl">Settings</span></button>
          </div>
          <div className="panel">
            {/* === ENTITIES TAB === */}
            {tab === 'entities' && !detail && aliveEntities.slice(0, 100).map(e => {
              const info = typeInfo(e.type);
              return (
                <div key={e.id} className={`entity-item ${e.id === selectedId ? 'selected' : ''}`} onClick={() => setSelectedId(e.id)}>
                  <MiniAvatar entityId={e.id} typeColor={info.color} size={32} />
                  <div className="entity-info">
                    <div className="entity-name">#{e.id} {e.dev_name || e.type}</div>
                    <div className="entity-meta">{e.role} {'\u{00B7}'} {e.commits || 0} commits</div>
                  </div>
                  <div className="energy-bar">
                    <div className="energy-fill" style={{ width: `${Math.min(100, e.energy * 100)}%`, background: energyColor(e.energy) }} />
                  </div>
                </div>
              );
            })}
            {tab === 'entities' && detail && (
              <div className="detail-panel">
                <button style={{ fontSize: 11, marginBottom: 8, cursor: 'pointer', background: 'none', border: '1px solid var(--border)', color: 'var(--text2)', borderRadius: 4, padding: '2px 8px' }} onClick={() => { setSelectedId(null); setDetail(null); }}>{'\u{2190}'} Back</button>
                <EntityProfileCard entity={detail} typeInfo={typeInfo(detail.type)} onClose={() => setSelectedId(null)} />
                {detail.found_bug_in != null && <div style={{ fontSize: 11, marginTop: 6 }}>{'\u{1F41B}'} Found Bug in Snippet #{detail.found_bug_in}</div>}
                {detail.reported_to_dev != null && <div style={{ fontSize: 11, color: '#3fb950' }}>{'\u{2192}'} Reported to Dev #{detail.reported_to_dev}</div>}
                {detail.memories?.length > 0 && (
                  <div className="detail-section" style={{ marginTop: 12 }}>
                    <h4>Memory</h4>
                    {detail.memories.slice(-8).reverse().map((m, i) => (
                      <div key={i} className="memory-item">
                        <span style={{ color: 'var(--accent)' }}>{m.tick}</span> {m.event} {m.other_id != null ? `\u{2192} #${m.other_id}` : ''}
                      </div>
                    ))}
                  </div>
                )}
                <div style={{ display: 'flex', gap: 6, marginTop: 10 }}>
                  <button style={{ flex: 1, padding: '6px', background: '#1f6feb22', border: '1px solid var(--accent)', color: 'var(--accent)', borderRadius: 6, cursor: 'pointer', fontSize: 11 }} onClick={async () => { await fetch(`/api/bless/${detail.id}`, { method: 'POST' }); fetchEntity(detail.id); }}>{'\u{26A1}'} Boost</button>
                  <button style={{ flex: 1, padding: '6px', background: '#f8514915', border: '1px solid var(--red)', color: 'var(--red)', borderRadius: 6, cursor: 'pointer', fontSize: 11 }} onClick={async () => { await fetch(`/api/smite/${detail.id}`, { method: 'POST' }); setSelectedId(null); setDetail(null); }}>{'\u{1F480}'} rm -rf</button>
                </div>
              </div>
            )}

            {/* === PROJECTS TAB === */}
            {tab === 'projects' && (<>
              {S.active_project ? (
                <div className="sett-card" style={{ border: '1px solid var(--accent)', background: 'var(--bg)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
                    <span style={{ width: 10, height: 10, borderRadius: '50%', background: 'var(--green)', display: 'inline-block', animation: 'pulse 1.5s infinite' }} />
                    <h5 style={{ margin: 0, color: 'var(--accent)', fontSize: 14 }}>{'\u{1F680}'} {S.active_project.name}</h5>
                    <span style={{ fontSize: 10, padding: '1px 6px', borderRadius: 8, fontWeight: 600, background: S.active_project.phase === 'architecture' ? '#1f6feb33' : S.active_project.phase === 'development' ? '#23863633' : '#3fb95033', color: S.active_project.phase === 'architecture' ? 'var(--accent)' : S.active_project.phase === 'development' ? 'var(--green)' : 'var(--yellow)' }}>{S.active_project.phase}</span>
                  </div>
                  <div className="sett-meta">{'\u{1F465}'} {S.active_project.population} devs {'\u{00B7}'} {'\u{1F4BB}'} {S.active_project.commits} commits {'\u{00B7}'} {'\u{1F41B}'} {S.active_project.bugs} bugs</div>
                  {S.active_project.phase === 'architecture' && S.active_project.file_structure?.length > 0 && (
                    <div style={{ marginTop: 8, padding: 8, background: '#1f6feb15', border: '1px solid #1f6feb33', borderRadius: 6 }}>
                      <div style={{ fontSize: 11, color: 'var(--accent)', fontWeight: 600, marginBottom: 6, display: 'flex', alignItems: 'center', gap: 4 }}>
                        {'\u{1F4D0}'} Planning Architecture
                        {S.active_project.team_meetings > 0 && <span style={{ fontSize: 9, color: 'var(--text2)', fontWeight: 400 }}>({S.active_project.team_meetings} meetings)</span>}
                      </div>
                      <div style={{ maxHeight: 180, overflowY: 'auto', fontSize: 10 }}>
                        {(() => {
                          const struct = S.active_project.file_structure.filter(f => f !== 'README.md' && f !== '.gitignore');
                          const dirs = {};
                          struct.forEach(f => {
                            const parts = f.split('/');
                            const dir = parts.length > 1 ? parts.slice(0, -1).join('/') : '.';
                            if (!dirs[dir]) dirs[dir] = [];
                            if (!f.endsWith('/')) dirs[dir].push(parts[parts.length - 1]);
                          });
                          return Object.entries(dirs).map(([dir, files]) => (
                            <div key={dir} style={{ marginBottom: 4 }}>
                              <div style={{ color: 'var(--yellow)', fontWeight: 600 }}>{'\u{1F4C1}'} {dir}/</div>
                              {files.map((f, i) => (
                                <div key={i} style={{ paddingLeft: 12, color: 'var(--text2)', lineHeight: 1.6 }}>{'\u{1F4C4}'} {f}</div>
                              ))}
                            </div>
                          ));
                        })()}
                      </div>
                    </div>
                  )}
                  {S.active_project.phase !== 'architecture' && <>
                  <div style={{ marginTop: 6, background: '#21262d', borderRadius: 4, overflow: 'hidden', height: 6 }}>
                    <div style={{ height: '100%', width: `${S.active_project.progress}%`, background: 'var(--accent)', borderRadius: 4, transition: 'width .5s' }} />
                  </div>
                  <div style={{ fontSize: 10, color: 'var(--text2)', marginTop: 2 }}>{S.active_project.progress}% ({S.active_project.files}/{S.active_project.max_files} files)</div>
                  </>}
                  {S.active_project.tech_stack?.length > 0 && <div style={{ marginTop: 4 }}>{S.active_project.tech_stack.map((t, i) => <span key={i} className="tech-badge">{t}</span>)}</div>}
                </div>
              ) : <div style={{ color: 'var(--text2)', fontSize: 12, padding: 8 }}>Project is being created...</div>}
              {completedProjects.length > 0 && (<>
                <div style={{ fontSize: 12, color: 'var(--text2)', marginTop: 16, marginBottom: 6, borderTop: '1px solid #21262d', paddingTop: 8 }}>{'\u{2705}'} Completed ({completedProjects.length})</div>
                {completedProjects.slice().reverse().map((p, i) => (
                  <div key={i} className="sett-card" style={{ opacity: 0.85 }}>
                    <h5 style={{ margin: 0, marginBottom: 2 }}>{p.name}</h5>
                    <div className="sett-meta">{'\u{1F4C4}'} {p.files_count} files {'\u{00B7}'} {'\u{1F4BB}'} {p.total_commits} commits {'\u{00B7}'} {'\u{1F41B}'} {p.bug_count} bugs</div>
                    {p.tech_stack?.length > 0 && <div style={{ marginTop: 3 }}>{p.tech_stack.map((t, j) => <span key={j} className="tech-badge">{t}</span>)}</div>}
                    {p.github_url && <a href={p.github_url} target="_blank" rel="noopener noreferrer" style={{ display: 'inline-flex', alignItems: 'center', gap: 4, marginTop: 6, padding: '4px 10px', background: '#238636', color: '#fff', borderRadius: 6, fontSize: 11, textDecoration: 'none', fontWeight: 600 }}>{'\u{1F419}'} GitHub {'\u{2192}'}</a>}
                  </div>
                ))}
              </>)}
            </>)}

            {/* === CODE TAB === */}
            {tab === 'code' && (<>
              <div style={{ fontSize: 11, color: 'var(--text2)', marginBottom: 8 }}>Total: {code.length} snippets</div>
              {code.map(s => (
                <div key={s.id} className={`snippet-card ${s.has_bugs ? 'buggy' : ''}`} onClick={() => { setEditorFile(s); setEditorContent(s.content || ''); setTab('editor'); }}>
                  <span className="lang">{s.language}</span>
                  <span className="quality" style={{ color: qualityColor(s.quality) }}>{(s.quality * 100).toFixed(0)}%</span>
                  <div className="desc">{s.description}</div>
                  <div style={{ fontSize: 10, color: 'var(--text2)', marginTop: 2 }}>
                    Dev #{s.author_id} {'\u{00B7}'} {s.lines} lines {'\u{00B7}'} {s.filename}
                    {s.has_bugs && <span style={{ color: 'var(--red)', marginLeft: 6 }}>{'\u{1F41B}'} BUG</span>}
                    {s.reviewed && <span style={{ color: 'var(--green)', marginLeft: 6 }}>{'\u{2714}'}</span>}
                  </div>
                </div>
              ))}
            </>)}

            {/* === FILES TAB === */}
            {tab === 'files' && (
              <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
                {!projectFiles && S.active_project && (
                  <div style={{ cursor: 'pointer' }} onClick={() => fetchProjectFiles(S.active_project.id)}>
                    <div style={{ fontSize: 11, color: 'var(--text2)', marginBottom: 4 }}>{'\u{1F4C2}'} Active Project Files</div>
                    <div className="sett-card" style={{ border: '1px solid var(--accent)' }}>
                      <h5>{'\u{1F4DD}'} {S.active_project.name}</h5>
                      <div className="sett-meta">{S.active_project.files} files {'\u{00B7}'} {S.active_project.commits} commits</div>
                    </div>
                  </div>
                )}
                {!projectFiles && !S.active_project && <div style={{ color: 'var(--text2)', fontSize: 12, padding: 8 }}>Project not started yet...</div>}
                {projectFiles && !viewingFile && (<>
                  <button style={{ fontSize: 11, marginBottom: 8, cursor: 'pointer', background: 'none', border: '1px solid var(--border)', color: 'var(--text2)', borderRadius: 4, padding: '2px 8px' }} onClick={() => setProjectFiles(null)}>{'\u{2190}'} Back</button>
                  {Object.entries(projectFiles.tree || {}).map(([dir, files]) => (
                    <div key={dir} style={{ marginBottom: 6 }}>
                      <div style={{ fontSize: 11, color: 'var(--yellow)', fontWeight: 600, marginBottom: 2 }}>{'\u{1F4C2}'} {dir}/</div>
                      {files.map((f, i) => {
                        const fObj = (projectFiles.files || []).find(x => x.filename === f);
                        return (
                          <div key={i} className="file-item" style={{ fontSize: 11, padding: '3px 8px 3px 16px', cursor: 'pointer', borderLeft: '2px solid transparent', display: 'flex', alignItems: 'center', gap: 4 }} onClick={() => { if (fObj) { setViewingFile(fObj); setEditorFile(fObj); setEditorContent(fObj.content || ''); } }}>
                            <span style={{ color: 'var(--text2)' }}>{'\u{1F4C4}'}</span>
                            <span style={{ flex: 1 }}>{f}</span>
                            {fObj && <span style={{ fontSize: 9, color: qualityColor(fObj.quality) }}>{(fObj.quality * 100).toFixed(0)}%</span>}
                            {fObj?.has_bugs && <span style={{ fontSize: 9, color: 'var(--red)' }}>{'\u{1F41B}'}</span>}
                          </div>
                        );
                      })}
                    </div>
                  ))}
                </>)}
                {viewingFile && (<>
                  <button style={{ fontSize: 11, marginBottom: 8, cursor: 'pointer', background: 'none', border: '1px solid var(--border)', color: 'var(--text2)', borderRadius: 4, padding: '2px 8px' }} onClick={() => setViewingFile(null)}>{'\u{2190}'} Back</button>
                  <div style={{ fontSize: 11, color: 'var(--accent)', fontWeight: 600, marginBottom: 4 }}>{viewingFile.filename}</div>
                  <pre style={{ flex: 1, overflow: 'auto', background: 'var(--bg)', border: '1px solid #21262d', borderRadius: 6, padding: 8, fontSize: 11, lineHeight: 1.5, color: 'var(--text)', fontFamily: 'Consolas, monospace', margin: 0, whiteSpace: 'pre-wrap' }}><code>{viewingFile.content}</code></pre>
                </>)}
              </div>
            )}

            {/* === EDITOR TAB === */}
            {tab === 'editor' && (
              <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
                {editorFile ? (<>
                  <div style={{ marginBottom: 8 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <span style={{ width: 8, height: 8, borderRadius: '50%', background: 'var(--green)', display: 'inline-block' }} />
                      <span style={{ fontSize: 12, color: 'var(--accent)', fontWeight: 600 }}>{editorFile.filename}</span>
                    </div>
                    <div style={{ fontSize: 10, color: 'var(--text2)', marginTop: 2 }}>
                      {editorFile.language} {'\u{00B7}'} Dev #{editorFile.author_id} {'\u{00B7}'} {editorFile.description}
                      <span style={{ marginLeft: 6, color: qualityColor(editorFile.quality) }}>{(editorFile.quality * 100).toFixed(0)}%</span>
                    </div>
                  </div>
                  <div style={{ flex: 1, overflow: 'auto', background: 'var(--bg)', border: '1px solid #21262d', borderRadius: 6, padding: 0, position: 'relative' }}>
                    <div style={{ display: 'flex', fontFamily: 'Consolas, monospace', fontSize: 11, lineHeight: 1.6 }}>
                      <div style={{ padding: '8px 8px 8px 4px', color: '#484f58', textAlign: 'right', borderRight: '1px solid #21262d', userSelect: 'none', minWidth: 30 }}>
                        {(editorContent || '').split('\n').map((_, i) => <div key={i}>{i + 1}</div>)}
                      </div>
                      <pre style={{ flex: 1, padding: 8, margin: 0, color: 'var(--text)', whiteSpace: 'pre-wrap', overflow: 'hidden' }}><code>{editorContent}</code><span style={{ borderRight: '2px solid var(--accent)', animation: 'blink 0.8s step-end infinite' }}>{'\u{00A0}'}</span></pre>
                    </div>
                  </div>
                  <div style={{ fontSize: 10, color: '#484f58', marginTop: 4, textAlign: 'right' }}>Tick {editorFile.tick_created} {'\u{00B7}'} Snippet #{editorFile.id}</div>
                </>) : <div style={{ color: 'var(--text2)', fontSize: 12, padding: 8 }}>No code written yet... Click a snippet in Code tab to view</div>}
              </div>
            )}

            {/* === CHAT TAB === */}
            {tab === 'chat' && (
              <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
                {!selectedId && <div style={{ color: 'var(--text2)', fontSize: 12, padding: 8 }}>Select an entity to chat (click on the map)</div>}
                {selectedId && (<>
                  <div style={{ flex: 1, overflowY: 'auto', marginBottom: 8 }}>
                    {chatMessages.map((m, i) => (
                      <div key={i} style={{ padding: '6px 8px', borderRadius: 6, marginBottom: 4, background: m.role === 'user' ? '#1f6feb33' : 'var(--surface)', borderLeft: m.role === 'user' ? '3px solid var(--accent)' : '3px solid var(--green)', fontSize: 12 }}>{m.text}</div>
                    ))}
                    {chatLoading && <div style={{ fontSize: 11, color: 'var(--text2)' }}>Thinking...</div>}
                    <div ref={chatEndRef} />
                  </div>
                  <div style={{ display: 'flex', gap: 4 }}>
                    <input value={chatInput} onChange={e => setChatInput(e.target.value)} onKeyDown={e => e.key === 'Enter' && sendChat()} placeholder="Ask a question..." style={{ flex: 1, background: 'var(--bg)', border: '1px solid var(--border)', color: 'var(--text)', padding: '6px 8px', borderRadius: 6, fontSize: 12, outline: 'none' }} />
                    <button onClick={sendChat} style={{ background: 'var(--accent)', border: 'none', color: '#0d1117', padding: '6px 12px', borderRadius: 6, cursor: 'pointer', fontSize: 12, fontWeight: 600 }}>{'\u{27A4}'}</button>
                  </div>
                </>)}
              </div>
            )}

            {/* === SOULS TAB === */}
            {tab === 'souls' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, fontSize: 12 }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <div style={{ fontWeight: 600 }}>{'\u{1F56F}'} Souls ({souls.length})</div>
                  <button onClick={fetchSouls} style={{ background: 'var(--surface2)', border: '1px solid var(--border)', color: 'var(--text)', padding: '4px 10px', borderRadius: 6, cursor: 'pointer', fontSize: 11 }}>{soulsLoading ? '\u{2026}' : '\u{21BB}'}</button>
                </div>
                {souls.length === 0 && !soulsLoading && <div style={{ color: 'var(--text2)', padding: 8 }}>No souls yet {'\u{2014}'} souls emerge as the world evolves.</div>}
                {souls.map(s => (
                  <div key={s.id} style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 6, padding: 8 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                      <div style={{ fontWeight: 600, color: 'var(--accent)' }}>{s.name || '?'}</div>
                      <div style={{ fontSize: 10, color: 'var(--text2)' }}>{s.role || '\u{2014}'}</div>
                    </div>
                    <div style={{ fontSize: 10, color: 'var(--text2)', display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                      <span>{'\u{1F9EC}'} gen {s.rebirth_count ?? s.generation ?? 0}</span>
                      <span>{'\u{1F4DC}'} {typeof s.memories === 'number' ? s.memories : (s.memories?.length ?? 0)} memories</span>
                      {(s.entity_id ?? s.current_entity_id) != null && <span>{'\u{2192}'} #{s.entity_id ?? s.current_entity_id}</span>}
                    </div>
                    {(s.profile || s.persona) && <div style={{ fontSize: 11, fontStyle: 'italic', marginTop: 4, color: 'var(--text)' }}>{(p => p.length > 160 ? p.slice(0, 160) + '\u{2026}' : p)(s.profile || s.persona)}</div>}
                  </div>
                ))}
                <div style={{ marginTop: 8, fontSize: 10, color: '#484f58' }}>Socket: <span style={{ color: socketConnected ? 'var(--green)' : 'var(--red)' }}>{socketConnected ? '\u{25CF} connected' : '\u{25CB} disconnected'}</span></div>
              </div>
            )}

            {/* === SETTINGS TAB === */}
            {tab === 'settings' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12, fontSize: 12 }}>
                {/* --- LLM / AI Provider --- */}
                <div style={{ borderBottom: '1px solid var(--border)', paddingBottom: 10 }}>
                  <div style={{ fontWeight: 600, color: 'var(--text)', marginBottom: 6 }}>{'\u{1F9E0}'} AI Provider</div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
                    <span style={{ width: 8, height: 8, borderRadius: '50%', background: S.brain?.connected ? '#3fb950' : '#f85149' }} />
                    <span style={{ color: S.brain?.connected ? '#3fb950' : 'var(--text2)', fontSize: 11 }}>{S.brain?.connected ? `Connected: ${llmConfig.provider || 'unknown'}` : 'Disconnected'}</span>
                  </div>
                  <div style={{ marginBottom: 4 }}>
                    <label style={{ fontSize: 10, color: 'var(--text2)', display: 'block', marginBottom: 2 }}>Provider</label>
                    <select value={llmConfig.provider || 'ollama'} onChange={e => saveLlmConfig({ provider: e.target.value })} style={{ width: '100%', background: 'var(--bg)', border: '1px solid var(--border)', color: 'var(--text)', padding: '5px 8px', borderRadius: 6, fontSize: 11, outline: 'none' }}>
                      {llmProviders.map(p => <option key={p.id} value={p.id}>{p.label}</option>)}
                      {llmProviders.length === 0 && <option value={llmConfig.provider || 'ollama'}>{llmConfig.provider || 'ollama'}</option>}
                    </select>
                  </div>
                  <div style={{ marginBottom: 4 }}>
                    <label style={{ fontSize: 10, color: 'var(--text2)', display: 'block', marginBottom: 2 }}>Model</label>
                    {(() => { const prov = llmProviders.find(p => p.id === llmConfig.provider); return prov?.models?.length > 0 ? (
                      <select value={llmConfig.model || ''} onChange={e => saveLlmConfig({ model: e.target.value })} style={{ width: '100%', background: 'var(--bg)', border: '1px solid var(--border)', color: 'var(--text)', padding: '5px 8px', borderRadius: 6, fontSize: 11, outline: 'none' }}>
                        {prov.models.map(m => <option key={m} value={m}>{m}</option>)}
                      </select>
                    ) : (
                      <input value={llmConfig.model || ''} onChange={e => setLlmConfig(c => ({ ...c, model: e.target.value }))} onBlur={e => saveLlmConfig({ model: e.target.value })} placeholder="model name" style={{ width: '100%', background: 'var(--bg)', border: '1px solid var(--border)', color: 'var(--text)', padding: '5px 8px', borderRadius: 6, fontSize: 11, outline: 'none', fontFamily: 'monospace' }} />
                    ); })()}
                  </div>
                  {(() => { const prov = llmProviders.find(p => p.id === llmConfig.provider); return prov?.requires_key !== false; })() && (
                    <div style={{ marginBottom: 4 }}>
                      <label style={{ fontSize: 10, color: 'var(--text2)', display: 'block', marginBottom: 2 }}>API Key {llmConfig.has_key && <span style={{ color: '#3fb950' }}>({llmConfig.key_preview})</span>}</label>
                      <div style={{ display: 'flex', gap: 4 }}>
                        <input type="password" placeholder={llmConfig.has_key ? 'key is set \u2014 enter new to change' : 'sk-...'} onChange={e => setLlmConfig(c => ({ ...c, _newKey: e.target.value }))} style={{ flex: 1, background: 'var(--bg)', border: '1px solid var(--border)', color: 'var(--text)', padding: '5px 8px', borderRadius: 6, fontSize: 11, outline: 'none', fontFamily: 'monospace' }} />
                        <button onClick={() => { const k = llmConfig._newKey; if (k?.trim()) saveLlmConfig({ api_key: k.trim() }); }} style={{ background: '#238636', border: 'none', color: '#fff', padding: '5px 10px', borderRadius: 6, cursor: 'pointer', fontSize: 11 }}>Set</button>
                      </div>
                    </div>
                  )}
                  <div style={{ marginBottom: 4 }}>
                    <label style={{ fontSize: 10, color: 'var(--text2)', display: 'block', marginBottom: 2 }}>Base URL</label>
                    <input value={llmConfig.base_url || ''} onChange={e => setLlmConfig(c => ({ ...c, base_url: e.target.value }))} onBlur={e => saveLlmConfig({ base_url: e.target.value })} placeholder="https://..." style={{ width: '100%', background: 'var(--bg)', border: '1px solid var(--border)', color: 'var(--text)', padding: '5px 8px', borderRadius: 6, fontSize: 11, outline: 'none', fontFamily: 'monospace' }} />
                  </div>
                  <div style={{ display: 'flex', gap: 8, marginBottom: 6 }}>
                    <div style={{ flex: 1 }}>
                      <label style={{ fontSize: 10, color: 'var(--text2)', display: 'block', marginBottom: 2 }}>Temperature: {llmConfig.temperature ?? 0.7}</label>
                      <input type="range" min={0} max={2} step={0.1} value={llmConfig.temperature ?? 0.7} onChange={e => { const v = parseFloat(e.target.value); setLlmConfig(c => ({ ...c, temperature: v })); }} onMouseUp={e => saveLlmConfig({ temperature: parseFloat(e.target.value) })} style={{ width: '100%' }} />
                    </div>
                    <div style={{ flex: 1 }}>
                      <label style={{ fontSize: 10, color: 'var(--text2)', display: 'block', marginBottom: 2 }}>Max tokens</label>
                      <input type="number" min={50} max={4096} value={llmConfig.max_tokens ?? 200} onChange={e => setLlmConfig(c => ({ ...c, max_tokens: parseInt(e.target.value) || 200 }))} onBlur={e => saveLlmConfig({ max_tokens: parseInt(e.target.value) || 200 })} style={{ width: '100%', background: 'var(--bg)', border: '1px solid var(--border)', color: 'var(--text)', padding: '5px 8px', borderRadius: 6, fontSize: 11, outline: 'none' }} />
                    </div>
                  </div>
                  <button onClick={testLlm} disabled={llmTesting} style={{ width: '100%', background: 'var(--surface2)', border: '1px solid var(--border)', color: 'var(--text)', padding: '5px 10px', borderRadius: 6, cursor: 'pointer', fontSize: 11 }}>{llmTesting ? '\u{23F3} Testing...' : '\u{1F50C} Test Connection'}</button>
                  {llmTestResult && <div style={{ marginTop: 4, fontSize: 11, color: llmTestResult.ok ? '#3fb950' : '#f85149' }}>{llmTestResult.ok ? '\u{2705} Connection OK' : `\u{274C} ${llmTestResult.error || 'Failed'}`}{llmTestResult.model && ` \u{2014} ${llmTestResult.model}`}{llmTestResult.latency && ` (${llmTestResult.latency}ms)`}</div>}
                  {llmMsg && <div style={{ marginTop: 4, fontSize: 11, color: llmMsg.includes('error') || llmMsg.includes('Error') ? 'var(--red)' : 'var(--green)' }}>{llmMsg}</div>}
                </div>
                <div style={{ borderBottom: '1px solid var(--border)', paddingBottom: 10 }}>
                  <div style={{ fontWeight: 600, color: 'var(--text)', marginBottom: 6 }}>{'\u{1F419}'} GitHub configuration</div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
                    <span style={{ width: 8, height: 8, borderRadius: '50%', background: ghStatus?.enabled ? '#3fb950' : '#f85149' }} />
                    <span style={{ color: ghStatus?.enabled ? '#3fb950' : 'var(--text2)', fontSize: 11 }}>{ghStatus?.enabled ? `Connected: ${ghStatus.user}` : 'Disconnected'}</span>
                  </div>
                  <input value={ghToken} onChange={e => setGhToken(e.target.value)} type="password" placeholder="ghp_... Token" style={{ width: '100%', background: 'var(--bg)', border: '1px solid var(--border)', color: 'var(--text)', padding: '6px 8px', borderRadius: 6, fontSize: 11, outline: 'none', marginBottom: 6, fontFamily: 'monospace' }} />
                  <div style={{ display: 'flex', gap: 4 }}>
                    <button onClick={async () => { setGhMsg(''); if (!ghToken.trim()) { setGhMsg('Token is empty'); return; } try { const r = await (await fetch('/api/github/configure', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ token: ghToken.trim() }) })).json(); if (r.ok) { setGhMsg(`Connected: ${r.user}`); setGhStatus({ enabled: true, user: r.user, stats: r.stats }); setGhToken(''); } else setGhMsg(r.error || 'error'); } catch { setGhMsg('Connection error'); } }} style={{ flex: 1, background: '#238636', border: 'none', color: '#fff', padding: '5px 10px', borderRadius: 6, cursor: 'pointer', fontSize: 11 }}>Connect</button>
                    {ghStatus?.enabled && <button onClick={async () => { await fetch('/api/github/disconnect', { method: 'POST' }); setGhStatus({ enabled: false, user: null }); setGhMsg('Disconnected'); }} style={{ background: '#da3633', border: 'none', color: '#fff', padding: '5px 10px', borderRadius: 6, cursor: 'pointer', fontSize: 11 }}>Disconnect</button>}
                  </div>
                  {ghMsg && <div style={{ marginTop: 4, fontSize: 11, color: ghMsg.includes('error') || ghMsg.includes('empty') ? 'var(--red)' : 'var(--green)' }}>{ghMsg}</div>}
                  {ghStatus?.stats && <div style={{ marginTop: 6, fontSize: 10, color: 'var(--text2)' }}>Pushed: {ghStatus.stats.projects_pushed} | Files: {ghStatus.stats.total_files_pushed} | Queue: {ghStatus.stats.queue_size}</div>}
                </div>
                <div>
                  <div style={{ fontWeight: 600, marginBottom: 6 }}>{'\u{1F680}'} Project Request</div>
                  <input value={reqName} onChange={e => setReqName(e.target.value)} placeholder="Project name" style={{ width: '100%', background: 'var(--bg)', border: '1px solid var(--border)', color: 'var(--text)', padding: '6px 8px', borderRadius: 6, fontSize: 11, outline: 'none', marginBottom: 4 }} />
                  <textarea value={reqDesc} onChange={e => setReqDesc(e.target.value)} placeholder="Description (optional)" rows={2} style={{ width: '100%', background: 'var(--bg)', border: '1px solid var(--border)', color: 'var(--text)', padding: '6px 8px', borderRadius: 6, fontSize: 11, outline: 'none', resize: 'vertical', marginBottom: 4 }} />
                  <div style={{ marginBottom: 4 }}>
                    <div style={{ fontSize: 10, color: 'var(--text2)', marginBottom: 2 }}>Tech Stack:</div>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 3 }}>
                      {['Python','JavaScript','Rust','Go','HTML/CSS','SQL'].map(t => (
                        <button key={t} onClick={() => setReqStack(p => p.includes(t) ? p.filter(x => x !== t) : [...p, t])} style={{ padding: '2px 8px', borderRadius: 10, fontSize: 10, cursor: 'pointer', border: '1px solid', background: reqStack.includes(t) ? '#1f6feb33' : 'transparent', borderColor: reqStack.includes(t) ? 'var(--accent)' : 'var(--border)', color: reqStack.includes(t) ? 'var(--accent)' : 'var(--text2)' }}>{t}</button>
                      ))}
                    </div>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
                    <label style={{ fontSize: 10, color: 'var(--text2)' }}>Files:</label>
                    <input type="range" min={10} max={80} value={reqFiles} onChange={e => setReqFiles(+e.target.value)} style={{ flex: 1 }} />
                    <span style={{ fontSize: 11, minWidth: 20 }}>{reqFiles}</span>
                  </div>
                  <button onClick={async () => { setReqMsg(''); if (!reqName.trim()) { setReqMsg('Name is required'); return; } try { const r = await (await fetch('/api/project/request', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name: reqName.trim(), description: reqDesc.trim(), tech_stack: reqStack, max_files: reqFiles }) })).json(); if (r.ok) { setReqMsg(`Queued! (${r.queue_size})`); setReqName(''); setReqDesc(''); setReqStack([]); setReqFiles(30); if (r.queued) setQueue(p => [...p, r.queued]); } else setReqMsg(r.error || 'error'); } catch { setReqMsg('Connection error'); } }} style={{ width: '100%', background: 'var(--accent)', border: 'none', color: '#0d1117', padding: '6px 12px', borderRadius: 6, cursor: 'pointer', fontSize: 11, fontWeight: 600 }}>{'\u{2795}'} Add to Queue</button>
                  {reqMsg && <div style={{ marginTop: 4, fontSize: 11, color: reqMsg.includes('error') || reqMsg.includes('required') ? 'var(--red)' : 'var(--green)' }}>{reqMsg}</div>}
                  {queue.length > 0 && (
                    <div style={{ marginTop: 8 }}>
                      <div style={{ fontSize: 10, color: 'var(--text2)', marginBottom: 3 }}>{'\u{1F4CB}'} Queue ({queue.length}):</div>
                      {queue.map((q, i) => (
                        <div key={i} style={{ padding: '4px 6px', background: 'var(--surface)', borderRadius: 4, marginBottom: 2, fontSize: 10, color: 'var(--text)' }}>
                          <span style={{ color: 'var(--accent)' }}>{q.name}</span>
                          <span style={{ color: 'var(--text2)' }}> {'\u{00B7}'} {q.max_files} files</span>
                          {q.tech_stack?.length > 0 && <span style={{ color: 'var(--text2)' }}> {'\u{00B7}'} {q.tech_stack.join(', ')}</span>}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* ===== CENTER ===== */}
        <div className="center">
          <div className="map-container" onClick={handleCanvasClick}>
            <canvas ref={canvasRef} className="map-canvas" />
          </div>
          <div className="events-panel">
            <div style={{ fontSize: 11, color: 'var(--text2)', marginBottom: 4, fontWeight: 600 }}>{'\u{1F4CB}'} Events</div>
            {events.slice(0, 30).map((ev, i) => <div key={i} className="event-line">{ev}</div>)}
          </div>
        </div>

        {/* ===== RIGHT SIDEBAR ===== */}
        <div className="right-sidebar">
          <div className="stats-grid">
            <div className="stat-box"><div className="num" style={{ color: 'var(--accent)' }}>{S.entities || 0}</div><div className="label">Entities</div></div>
            <div className="stat-box"><div className="num" style={{ color: 'var(--green)' }}>{S.total_code_generated || 0}</div><div className="label">Code</div></div>
            <div className="stat-box"><div className="num" style={{ color: 'var(--red)' }}>{S.total_bug_reports || 0}</div><div className="label">Bug Reports</div></div>
            <div className="stat-box"><div className="num" style={{ color: 'var(--yellow)' }}>{S.settlements || 0}</div><div className="label">Projects</div></div>
          </div>

          {S.type_counts && (
            <div className="chart-box">
              <h4>Species</h4>
              {Object.entries(S.type_counts).map(([t, count]) => {
                const info = typeInfo(t);
                return (
                  <div key={t} style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4, fontSize: 12 }}>
                    <span>{info.icon}</span>
                    <span style={{ flex: 1, color: 'var(--text2)' }}>{t}</span>
                    <span style={{ fontWeight: 600, color: info.color }}>{count}</span>
                  </div>
                );
              })}
            </div>
          )}

          {/* POPULATION CHART */}
          {popHistory.length > 10 && (
            <div className="chart-box">
              <h4>Population</h4>
              <ResponsiveContainer width="100%" height={150}>
                <AreaChart data={popHistory.slice(-200)}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#21262d" />
                  <XAxis dataKey="tick" tick={false} />
                  <YAxis tick={{ fontSize: 10, fill: '#8b949e' }} width={30} />
                  <Tooltip contentStyle={{ background: '#161b22', border: '1px solid #30363d', fontSize: 11 }} />
                  <Area type="monotone" dataKey="developer" stroke="#58a6ff" fill="#58a6ff33" stackId="1" />
                  <Area type="monotone" dataKey="bug" stroke="#f85149" fill="#f8514933" stackId="1" />
                  <Area type="monotone" dataKey="refactorer" stroke="#d29922" fill="#d2992233" stackId="1" />
                  <Area type="monotone" dataKey="senior" stroke="#ffd700" fill="#ffd70033" stackId="1" />
                  <Area type="monotone" dataKey="intern" stroke="#3fb950" fill="#3fb95033" stackId="1" />
                  <Area type="monotone" dataKey="copilot" stroke="#bc8cff" fill="#bc8cff33" stackId="1" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          )}

          {S.role_counts && (
            <div className="chart-box">
              <h4>Roles</h4>
              {Object.entries(S.role_counts).map(([r, count]) => (
                <div key={r} style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 3, fontSize: 12 }}>
                  <span style={{ flex: 1, color: 'var(--text2)' }}>{r}</span>
                  <span style={{ fontWeight: 600 }}>{count}</span>
                </div>
              ))}
            </div>
          )}

          {S.internet && (
            <div className="chart-box">
              <h4>Internet</h4>
              {[
                ['\u{1F310}', 'Portals', S.internet.portals, '#7ee7ff'],
                ['\u{1F6EB}', 'Trips', S.internet.portal_trips, '#bc8cff'],
                ['\u{1F4C4}', 'Reports', S.internet.web_reports, '#3fb950'],
                ['\u{1F4C8}', 'OS Growth', S.internet.open_source_growth, '#d29922'],
              ].map(([ico, lbl, val, col]) => (
                <div key={lbl} style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 3, fontSize: 12 }}>
                  <span>{ico}</span><span style={{ flex: 1, color: 'var(--text2)' }}>{lbl}</span><span style={{ fontWeight: 600, color: col }}>{val}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}