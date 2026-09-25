import { useEffect, useState, type FormEvent } from 'react'
import { ArrowUpRight, BookOpen, Check, ChevronDown, CircleHelp, Clock3, FileText, LoaderCircle, LogOut, Moon, Plus, Search, Sparkles, Sun } from 'lucide-react'

type Run = { id: string; question: string; status: string; created_at: string; report?: { title: string; summary: string; sections: { heading: string; body: string }[]; sources: string[]; demo: boolean } }

const examples = ['What is changing in urban heat adaptation?', 'How are small teams using open source AI?', 'What makes a research finding trustworthy?']

export default function App() {
  const [question, setQuestion] = useState('')
  const [runs, setRuns] = useState<Run[]>([])
  const [selected, setSelected] = useState<Run | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [token, setToken] = useState(() => localStorage.getItem('fieldnotes-token') ?? '')
  const [accountEmail, setAccountEmail] = useState('')
  const [authMode, setAuthMode] = useState<'login' | 'register'>('login')
  const [authEmail, setAuthEmail] = useState('')
  const [authPassword, setAuthPassword] = useState('')
  const [authError, setAuthError] = useState('')
  const [authBusy, setAuthBusy] = useState(false)
  const [theme, setTheme] = useState<'light' | 'dark'>(() => localStorage.getItem('fieldnotes-theme') === 'dark' ? 'dark' : 'light')

  useEffect(() => {
    document.documentElement.dataset.theme = theme
    localStorage.setItem('fieldnotes-theme', theme)
  }, [theme])

  useEffect(() => {
    function onShortcut(event: KeyboardEvent) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault()
        setSelected(null); setQuestion(''); setError('')
      }
    }
    window.addEventListener('keydown', onShortcut)
    return () => window.removeEventListener('keydown', onShortcut)
  }, [])

  async function refresh(accessToken = token) {
    try {
      const response = await fetch('/api/runs', { headers: { Authorization: `Bearer ${accessToken}` } })
      if (response.ok) setRuns(await response.json())
    } catch { /* API may not be running yet */ }
  }
  useEffect(() => {
    if (!token) return
    localStorage.setItem('fieldnotes-token', token)
    fetch('/api/auth/me', { headers: { Authorization: `Bearer ${token}` } })
      .then(async response => {
        if (!response.ok) throw new Error('session expired')
        const account = await response.json()
        setAccountEmail(account.email)
        await refresh(token)
      })
      .catch(() => { localStorage.removeItem('fieldnotes-token'); setToken('') })
  }, [token])

  async function authenticate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setAuthBusy(true); setAuthError('')
    try {
      const response = await fetch(`/api/auth/${authMode === 'register' ? 'register' : 'login'}`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: authEmail, password: authPassword }),
      })
      const result = await response.json()
      if (!response.ok) throw new Error(result.detail ?? 'Could not sign in.')
      localStorage.setItem('fieldnotes-token', result.access_token)
      setAccountEmail(result.email); setToken(result.access_token); setAuthPassword('')
    } catch (e) { setAuthError(e instanceof Error ? e.message : 'Could not reach the API.') }
    finally { setAuthBusy(false) }
  }

  function logout() {
    localStorage.removeItem('fieldnotes-token'); setToken(''); setRuns([]); setSelected(null); setAccountEmail('')
    setAuthMode('login'); setAuthEmail(''); setAuthPassword(''); setAuthError('')
  }

  async function submit(value = question) {
    if (!value.trim() || busy) return
    setBusy(true); setError(''); setQuestion(value)
    try {
      const response = await fetch('/api/runs', { method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` }, body: JSON.stringify({ question: value }) })
      if (!response.ok) throw new Error((await response.json()).detail ?? 'Could not start the research run.')
      const run = await response.json() as Run
      setSelected(run); await refresh()
    } catch (e) { setError(e instanceof Error ? e.message : 'Could not reach the API. Start the FastAPI backend and try again.') }
    finally { setBusy(false) }
  }

  const report = selected?.report
  if (!token) return <main className="auth-page"><a className="brand auth-brand" href="#"><span className="brand-mark"><BookOpen size={17}/></span><span>fieldnotes<span className="brand-dot">.</span></span></a><section className="auth-card"><div className="eyebrow"><span className="eyebrow-icon"><Sparkles size={13}/></span> YOUR AI RESEARCH ASSISTANT</div><h1>{authMode === 'login' ? 'Welcome back.' : 'Start your research desk.'}</h1><p className="auth-intro">{authMode === 'login' ? 'Sign in to continue to your saved briefings.' : 'Create an account to save and revisit your research.'}</p><form onSubmit={authenticate} className="auth-form"><label>Email address<input type="email" autoComplete="email" required value={authEmail} onChange={e => setAuthEmail(e.target.value)} placeholder="you@example.com"/></label><label>Password<input type="password" autoComplete={authMode === 'login' ? 'current-password' : 'new-password'} minLength={10} required value={authPassword} onChange={e => setAuthPassword(e.target.value)} placeholder="At least 10 characters"/></label>{authError && <div className="error-box">{authError}</div>}<button className="submit-button auth-submit" disabled={authBusy}>{authBusy ? <><LoaderCircle className="spin" size={16}/> Please wait</> : authMode === 'login' ? 'Sign in' : 'Create account'}<ArrowUpRight size={15}/></button></form><p className="auth-switch">{authMode === 'login' ? 'New to Fieldnotes?' : 'Already have an account?'} <button onClick={() => { setAuthMode(authMode === 'login' ? 'register' : 'login'); setAuthError('') }}>{authMode === 'login' ? 'Create an account' : 'Sign in'}</button></p></section><p className="auth-footnote">Your research desk, ready when you are.</p></main>
  return <div className="shell">
    <aside className="sidebar">
      <a className="brand" href="#"><span className="brand-mark"><BookOpen size={17}/></span><span>fieldnotes<span className="brand-dot">.</span></span></a>
      <div className="workspace"><span className="avatar">R</span><span><b>Research desk</b><small>Personal workspace</small></span><ChevronDown size={15}/></div>
      <div className="side-label">WORKSPACE</div>
      <button className="nav-item active" onClick={() => { setSelected(null); setQuestion(''); setError('') }}><Plus size={16}/> New chat <span className="shortcut">⌘ K</span></button>
      <button className="nav-item" onClick={() => { void refresh(); setSelected(null) }}><FileText size={16}/> All briefings</button>
      <div className="side-label recent-label">RECENT</div>
      <div className="recent-list">{runs.length ? runs.slice(0, 7).map(run => <button className={`recent-item ${selected?.id === run.id ? 'selected' : ''}`} key={run.id} onClick={() => setSelected(run)}><span className="recent-dot"/>{run.question}</button>) : <p className="empty-recent">Your briefings will appear here.</p>}</div>
      <div className="sidebar-bottom"><button className="nav-item"><CircleHelp size={16}/> Help & feedback</button><div className="profile"><span className="profile-avatar">{(accountEmail[0] ?? 'U').toUpperCase()}</span><span><b>{accountEmail || 'Your account'}</b><small>Signed in</small></span></div><button className="nav-item signout-button" onClick={logout}><LogOut size={16}/> Sign out</button></div>
    </aside>

    <main className="main">
      <header className="topbar"><div className="breadcrumb">Workspace <span>/</span> <b>{selected ? 'Briefing' : 'New briefing'}</b></div><div className="top-actions"><span className="status-pill"><span/> System ready</span><button className="icon-button" aria-label="Search"><Search size={17}/></button><button className="theme-toggle" onClick={() => setTheme(theme === 'light' ? 'dark' : 'light')} aria-label={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`} aria-pressed={theme === 'dark'} title={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`}>{theme === 'light' ? <Moon size={16}/> : <Sun size={16}/>}</button><span className="top-avatar">A</span></div></header>
      {!selected ? <section className="welcome">
        <div className="eyebrow"><span className="eyebrow-icon"><Sparkles size={13}/></span> YOUR AI RESEARCH ASSISTANT</div>
        <h1>Curiosity, meet<br/><em>clarity.</em></h1>
        <p className="intro">Turn a big question into a thoughtful, well-structured research briefing. Start with what you’re curious about.</p>
        <div className="composer"><textarea value={question} onChange={e => setQuestion(e.target.value)} onKeyDown={e => { if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) void submit() }} placeholder="Ask anything you’d like to understand…" rows={3}/><div className="composer-bottom"><span><span className="key">↵</span> to add a new line <span className="divider">·</span> <span className="key">⌘ ↵</span> to research</span><button className="submit-button" disabled={busy || !question.trim()} onClick={() => void submit()}>{busy ? <><LoaderCircle className="spin" size={16}/> Researching</> : <><Sparkles size={15}/> Start research <ArrowUpRight size={15}/></>}</button></div></div>
        {error && <div className="error-box">{error}</div>}
        <div className="suggestions-label">NOT SURE WHERE TO START? TRY ONE OF THESE</div>
        <div className="suggestions">{examples.map((example, i) => <button key={example} onClick={() => { setQuestion(example); void submit(example) }}><span className={`suggestion-icon icon-${i}`}><Sparkles size={14}/></span>{example}<ArrowUpRight className="suggestion-arrow" size={14}/></button>)}</div>
        <div className="privacy-note"><span className="privacy-dot"/> Thoughtful research takes a moment. Your briefings stay yours.</div>
      </section> : <section className="report-view">
        <button className="back-link" onClick={() => setSelected(null)}>← All briefings</button>
        {report ? <><div className="eyebrow"><span className="eyebrow-icon"><FileText size={13}/></span> RESEARCH BRIEFING {report.demo && <span className="demo-tag">STARTER PREVIEW</span>}</div><h1 className="report-title">{report.title}</h1><div className="report-meta"><span><Clock3 size={14}/> Just now</span><span className="meta-separator">·</span><span>{report.demo ? 'Preview workflow' : 'Research complete'}</span></div>{report.demo && <div className="demo-callout">This is a workflow preview. Real source discovery and AI synthesis will be connected next.</div>}<article className="report-card"><h2>Executive summary</h2><p>{report.summary}</p>{report.sections.map((section, i) => <div className="report-section" key={i}><h2>{section.heading}</h2><p>{section.body}</p></div>)}<div className="sources-block"><h2>Sources</h2>{report.sources.length ? report.sources.map((source, i) => <a href={source} target="_blank" rel="noreferrer" key={source}>Source {i + 1} <ArrowUpRight size={13}/></a>) : <p className="no-sources">No web sources were gathered in this preview.</p>}</div></article><div className="saved-note"><Check size={14}/> Saved to your research desk</div></> : <div className="loading-report"><LoaderCircle className="spin"/> Loading briefing…</div>}
      </section>}
      <footer className="footer"><span>Made for the questions worth asking.</span><span>Built with care <span className="heart">♥</span></span></footer>
    </main>
  </div>
}
