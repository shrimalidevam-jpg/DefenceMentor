import { FormEvent, useEffect, useRef, useState } from 'react'
import { ArrowRight, ArrowUpRight, BookOpen, BrainCircuit, CalendarDays, Check, ChevronDown, ChevronRight, GraduationCap, LayoutDashboard, Loader2, LogOut, Menu, MessageSquare, Settings2, ShieldCheck, Sparkles, UserRound, X } from 'lucide-react'
import { api, Chapter, Concept, Exam, Profile, Subject, Topic, User } from './services/api'
import ChatPanel from './ChatPanel'
import DiagnosticPanel from './DiagnosticPanel'
import AssessmentPanel from './AssessmentPanel'
import StudyPlannerPanel from './StudyPlannerPanel'
import SSBGuidancePanel from './SSBGuidancePanel'
import { closeWithMotion } from './motion'
import './ssb-guidance.css'

const TOKEN = 'nda_access_token'
type AuthMode = 'login' | 'register'

export default function App() {
  const [token, setToken] = useState(localStorage.getItem(TOKEN))
  const [user, setUser] = useState<User | null>(null)
  const [profile, setProfile] = useState<Profile | null>(null)
  const [ready, setReady] = useState(!token)
  const [online, setOnline] = useState<boolean | null>(null)
  useEffect(() => {
    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    if (reduceMotion || !('IntersectionObserver' in window)) return

    const selectors = [
      '.hero-copy', '.hero-facts > p', '.auth-card', '.auth-card form', '.welcome', '.tutor', '.profile-card',
      '.curriculum-column', '.curriculum-detail', '.chat-message', '.diagnostic-question',
      '.assessment-summary > div', '.study-plan-task', '.ssb-tip', '.vocab-card',
    ].join(',')
    const reveal = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (!entry.isIntersecting) return
        ;(entry.target as HTMLElement).dataset.motionReveal = 'visible'
        reveal.unobserve(entry.target)
      })
    }, { threshold: 0.12, rootMargin: '0px 0px -6% 0px' })
    const observed = new WeakSet<Element>()

    const observeElement = (element: Element) => {
      if (!(element instanceof HTMLElement) || element.dataset.motionReveal === 'visible' || observed.has(element)) return
      observed.add(element)
      if (!element.dataset.motionReveal) element.dataset.motionReveal = 'pending'
      reveal.observe(element)
    }
    const observeTree = (root: ParentNode) => {
      if (root instanceof Element && root.matches(selectors)) observeElement(root)
      root.querySelectorAll(selectors).forEach(observeElement)
    }
    observeTree(document)

    const mutations = new MutationObserver(records => {
      records.forEach(record => record.addedNodes.forEach(node => {
        if (node instanceof Element) observeTree(node)
      }))
    })
    mutations.observe(document.body, { childList: true, subtree: true })

    const hero = document.querySelector<HTMLElement>('.hero')
    let frame = 0
    const moveHero = (event: PointerEvent) => {
      if (!hero || event.pointerType === 'touch') return
      cancelAnimationFrame(frame)
      frame = requestAnimationFrame(() => {
        const bounds = hero.getBoundingClientRect()
        const x = ((event.clientX - bounds.left) / bounds.width - 0.5) * 8
        const y = ((event.clientY - bounds.top) / bounds.height - 0.5) * 8
        hero.style.setProperty('--hero-shift-x', `${x.toFixed(1)}px`)
        hero.style.setProperty('--hero-shift-y', `${y.toFixed(1)}px`)
      })
    }
    const resetHero = () => {
      if (!hero) return
      hero.style.setProperty('--hero-shift-x', '0px')
      hero.style.setProperty('--hero-shift-y', '0px')
    }
    hero?.addEventListener('pointermove', moveHero, { passive: true })
    hero?.addEventListener('pointerleave', resetHero)

    return () => {
      mutations.disconnect()
      reveal.disconnect()
      hero?.removeEventListener('pointermove', moveHero)
      hero?.removeEventListener('pointerleave', resetHero)
      cancelAnimationFrame(frame)
    }
  }, [])
  const checkHealth = async () => { try { await api.health(); setOnline(true) } catch { setOnline(false) } }
  useEffect(() => { void checkHealth() }, [])
  useEffect(() => {
    if (!token) return
    Promise.all([api.me(token), api.profile(token)]).then(([nextUser, nextProfile]) => { setUser(nextUser); setProfile(nextProfile) }).catch(() => { localStorage.removeItem(TOKEN); setToken(null); setUser(null); setProfile(null) }).finally(() => setReady(true))
  }, [token])
  const signIn = (accessToken: string, nextUser: User, nextProfile: Profile) => { localStorage.setItem(TOKEN, accessToken); setToken(accessToken); setUser(nextUser); setProfile(nextProfile) }
  const signOut = () => { localStorage.removeItem(TOKEN); setToken(null); setUser(null); setProfile(null) }
  if (!ready) return <div className="loading"><Loader2 className="spin" /> Opening your workspace...</div>
  if (!token || !user || !profile) return <Auth online={online} checkHealth={checkHealth} signIn={signIn} />
  return <Workspace user={user} profile={profile} token={token} setProfile={setProfile} signOut={signOut} />
}

export function Auth({ online, checkHealth, signIn }: { online: boolean | null; checkHealth: () => Promise<void>; signIn: (token: string, user: User, profile: Profile) => void }) {
  const [mode, setMode] = useState<AuthMode>('login')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [registeredEmail, setRegisteredEmail] = useState('')
  const [academicStream, setAcademicStream] = useState<'Science' | 'Commerce' | 'Arts' | ''>('')
  const [studentPhoto, setStudentPhoto] = useState('')
  const [parentPhoto, setParentPhoto] = useState('')
  const googleButton = useRef<HTMLDivElement>(null)
  const signInRef = useRef(signIn)
  signInRef.current = signIn

  const readPhoto = (file: File | undefined, setPhoto: (value: string) => void) => {
    if (!file) {
      setPhoto('')
      return
    }
    if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type) || file.size > 2 * 1024 * 1024) {
      setError('Choose a JPEG, PNG, or WebP photo smaller than 2 MB.')
      setPhoto('')
      return
    }
    const reader = new FileReader()
    reader.onload = () => setPhoto(typeof reader.result === 'string' ? reader.result : '')
    reader.onerror = () => setError('Unable to read the selected photo. Please choose it again.')
    reader.readAsDataURL(file)
  }

  useEffect(() => {
    const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID
    if (!clientId || mode !== 'login' || !googleButton.current) return

    const render = () => {
      if (!window.google || !googleButton.current) return
      googleButton.current.replaceChildren()
      window.google.accounts.id.initialize({
        client_id: clientId,
        callback: async ({ credential }) => {
          setBusy(true)
          setError('')
          setSuccess('')
          try {
            const session = await api.googleLogin(credential)
            const [nextUser, nextProfile] = await Promise.all([api.me(session.access_token), api.profile(session.access_token)])
            signInRef.current(session.access_token, nextUser, nextProfile)
          } catch (cause) {
            setError(cause instanceof Error ? cause.message : 'Google sign-in failed. Please try again.')
          } finally {
            setBusy(false)
          }
        },
      })
      window.google.accounts.id.renderButton(googleButton.current, { theme: 'outline', size: 'large', width: 320, text: 'signin_with', shape: 'rectangular' })
    }

    if (window.google) {
      render()
      return
    }
    const script = document.querySelector<HTMLScriptElement>('script[data-google-identity]') ?? document.createElement('script')
    if (!script.src) {
      script.src = 'https://accounts.google.com/gsi/client'
      script.async = true
      script.defer = true
      script.dataset.googleIdentity = 'true'
      script.onload = render
      document.head.appendChild(script)
    } else {
      script.addEventListener('load', render, { once: true })
    }
    return () => script.removeEventListener('load', render)
  }, [mode])

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const formElement = event.currentTarget
    const form = new FormData(formElement)
    const email = String(form.get('email')).trim().toLowerCase()
    const password = String(form.get('password'))
    const name = String(form.get('name')).trim()
    setBusy(true)
    setError('')
    setSuccess('')

    try {
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) throw new Error('Enter a valid email address.')
      if (mode === 'register') {
        if (name.length < 2 || name.length > 150) throw new Error('Full name must be between 2 and 150 characters.')
        if (password.length < 8 || password.length > 72) throw new Error('Password must be between 8 and 72 characters.')
        if (password !== String(form.get('confirm'))) throw new Error('Passwords do not match.')
        if (!studentPhoto || !parentPhoto) throw new Error('Select a photo for the student and parent or guardian.')
        if (form.get('guardianConsent') !== 'on') throw new Error('Parent or legal guardian consent is required.')
        await api.register({
          full_name: name,
          email,
          password,
          exam_target: String(form.get('examTarget')),
          current_level: String(form.get('level')) || undefined,
          academic_stream: academicStream as 'Science' | 'Commerce' | 'Arts',
          science_group: academicStream === 'Science' ? String(form.get('science_group')) as 'A' | 'B' : undefined,
          student_phone: String(form.get('studentPhone')).trim() || undefined,
          parent_phone: String(form.get('parentPhone')).trim(),
          student_photo_data: studentPhoto,
          parent_photo_data: parentPhoto,
          guardian_report_consent: true,
        })
        formElement.reset()
        setAcademicStream('')
        setStudentPhoto('')
        setParentPhoto('')
        setRegisteredEmail(email)
        setMode('login')
        setSuccess('Account created. Sign in with your new email and password.')
        return
      }

      const session = await api.login(email, password)
      const [nextUser, nextProfile] = await Promise.all([api.me(session.access_token), api.profile(session.access_token)])
      signIn(session.access_token, nextUser, nextProfile)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Unable to continue.')
    } finally {
      setBusy(false)
    }
  }

  const changeMode = () => {
    setMode(mode === 'login' ? 'register' : 'login')
    setAcademicStream('')
    setStudentPhoto('')
    setParentPhoto('')
    setError('')
    setSuccess('')
  }

  const registrationFields = mode === 'register' && <>
    <label>Full name<input name="name" autoComplete="name" required minLength={2} maxLength={150} placeholder="Your full name" /></label>
    <label>Student photo
      <input type="file" accept="image/jpeg,image/png,image/webp" capture="user" required onChange={event => readPhoto(event.target.files?.[0], setStudentPhoto)} />
      <small>JPEG, PNG, or WebP; maximum 2 MB. Used only as a profile photo, not for face recognition.</small>
      {studentPhoto && <img className="registration-photo-preview" src={studentPhoto} alt="Student profile photo preview" />}
    </label>
    <label>Parent or guardian photo
      <input type="file" accept="image/jpeg,image/png,image/webp" capture="user" required onChange={event => readPhoto(event.target.files?.[0], setParentPhoto)} />
      <small>JPEG, PNG, or WebP; maximum 2 MB. Used only as a profile photo, not for face recognition.</small>
      {parentPhoto && <img className="registration-photo-preview" src={parentPhoto} alt="Parent or guardian profile photo preview" />}
    </label>
    <div className="row">
      <label>Student phone (optional)
        <input name="studentPhone" type="tel" inputMode="tel" pattern="^\+[1-9][0-9]{7,14}$" placeholder="+919876543210" />
        <small>Include country code if the student has a phone.</small>
      </label>
      <label>Parent WhatsApp number (required)
        <input name="parentPhone" type="tel" inputMode="tel" pattern="^\+[1-9][0-9]{7,14}$" placeholder="+919876543210" required />
        <small>Use international format, including + and country code.</small>
      </label>
    </div>
    <label>Which stream are you studying?
      <select name="academic_stream" value={academicStream} onChange={event => setAcademicStream(event.target.value as 'Science' | 'Commerce' | 'Arts' | '')} required>
        <option value="">Choose your stream</option><option value="Science">Science</option><option value="Commerce">Commerce</option><option value="Arts">Arts</option>
      </select>
    </label>
    {academicStream === 'Science' && <label>Choose your Science group<select name="science_group" defaultValue="" required><option value="" disabled>Select Group A or B</option><option value="A">Group A</option><option value="B">Group B</option></select></label>}
    <div className="row">
      <label>Target exam<select name="examTarget" defaultValue="NDA"><option>NDA</option><option>NDA I 2027</option><option>NDA II 2027</option></select></label>
      <label>Level<select name="level"><option value="">Select level</option><option>Beginner</option><option>Intermediate</option><option>Advanced</option></select></label>
    </div>
    <label className="guardian-consent">
      <span><input type="checkbox" name="guardianConsent" required /> I am the student's parent or legal guardian. I consent to storing these profile photos and receiving weekly and monthly NDA progress reports by WhatsApp at the number above.</span>
    </label>
  </>

  return (
    <main className="auth">
      <section className="hero">
        <div className="brand"><Mark /> NDA Chatbot</div>
        <div className="hero-copy"><span className="eyebrow"><Sparkles /> INTELLIGENT PREPARATION</span><h1>Study with a<br /><i>clearer direction.</i></h1><p>A focused, personal space for NDA preparation. Your account and learning profile are ready for the journey ahead.</p></div>
        <div className="hero-facts"><p><ShieldCheck /><span><b>Secure by design</b>Protected account and data</span></p><p><BrainCircuit /><span><b>Built to adapt</b>Ready for personalised learning</span></p></div>
      </section>
      <section className="auth-panel"><div className="auth-card">
        <div className="mobile-brand"><Mark /> NDA Chatbot</div>
        <span className="connection-label"><i className={online ? 'good' : ''} />{online === null ? 'Checking system...' : online ? 'System online' : 'Service unavailable'}</span>
        <h2>{mode === 'login' ? 'Welcome back' : 'Create your account'}</h2>
        <p className="intro">{mode === 'login' ? 'Continue your NDA preparation.' : 'Build your personalised preparation profile.'}</p>
        {success && <p className="form-success" role="status">{success}</p>}
        <form key={mode} onSubmit={submit}>
          {registrationFields}
          <label>Email address<input name="email" type="email" autoComplete="email" required maxLength={320} defaultValue={registeredEmail} placeholder="you@example.com" /></label>
          <label>Password<input name="password" type="password" autoComplete={mode === 'register' ? 'new-password' : 'current-password'} required minLength={mode === 'register' ? 8 : 1} maxLength={72} placeholder="Password" /></label>
          {mode === 'register' && <label>Confirm password<input name="confirm" type="password" autoComplete="new-password" required minLength={8} maxLength={72} placeholder="Confirm password" /></label>}
          {error && <p className="error" role="alert">{error}</p>}
          <button className="primary" disabled={busy || online === false}>{busy ? <Loader2 className="spin" /> : <>{mode === 'login' ? 'Sign in' : 'Create account'} <ArrowRight /></>}</button>
        </form>
        <button className="switch" onClick={changeMode}>{mode === 'login' ? 'Create a new account' : 'Already have an account? Sign in'}</button>
        {mode === 'login' && import.meta.env.VITE_GOOGLE_CLIENT_ID && <><div className="auth-divider"><span>or continue with</span></div><div className="google-signin" ref={googleButton} /></>}
        {online === false && <button className="retry" onClick={() => void checkHealth()}>Retry connection</button>}
      </div></section>
    </main>
  )
}

function Workspace({ user, profile, token, setProfile, signOut }: { user: User; profile: Profile; token: string; setProfile: (profile: Profile) => void; signOut: () => void }) {
  const [menu, setMenu] = useState(false)
  const [settings, setSettings] = useState(false)
  const [settingsTab, setSettingsTab] = useState<'profile' | 'settings'>('profile')
  const [accountMenuOpen, setAccountMenuOpen] = useState(false)
  const accountMenuRef = useRef<HTMLDivElement>(null)
  const [curriculum, setCurriculum] = useState(false)
  const [chatOpen, setChatOpen] = useState(false)
  const [assessmentOpen, setAssessmentOpen] = useState(false)
  const [studyPlannerOpen, setStudyPlannerOpen] = useState(false)
  const [ssbGuidanceOpen, setSsbGuidanceOpen] = useState(false)
  const [assessmentExam, setAssessmentExam] = useState<Exam | null>(null)
  const [currentTime, setCurrentTime] = useState(() => new Date())
  const initials = user.full_name.split(' ').map(part => part[0]).slice(0, 2).join('').toUpperCase()
  const closeMenu = () => setMenu(false)
  const openSettings = (tab: 'profile' | 'settings') => {
    setSettingsTab(tab)
    setSettings(true)
    setAccountMenuOpen(false)
  }
  useEffect(() => { api.exams().then(exams => setAssessmentExam(exams[0] || null)).catch(() => setAssessmentExam(null)) }, [])
  useEffect(() => {
    const timer = window.setInterval(() => setCurrentTime(new Date()), 60_000)
    return () => window.clearInterval(timer)
  }, [])
  useEffect(() => {
    if (!accountMenuOpen) return
    const dismiss = (event: PointerEvent) => {
      if (event.target instanceof Node && !accountMenuRef.current?.contains(event.target)) setAccountMenuOpen(false)
    }
    const dismissOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setAccountMenuOpen(false)
    }
    document.addEventListener('pointerdown', dismiss)
    document.addEventListener('keydown', dismissOnEscape)
    return () => {
      document.removeEventListener('pointerdown', dismiss)
      document.removeEventListener('keydown', dismissOnEscape)
    }
  }, [accountMenuOpen])

  return <div className="shell">
    <aside className={menu ? 'side open' : 'side'}>
      <div className="side-brand"><div className="brand"><Mark /> NDA Chatbot</div><button className="close" onClick={closeMenu} title="Close menu"><X /></button></div>
      <nav><small>WORKSPACE</small><button className="nav-action active"><LayoutDashboard /> Overview</button><button className="nav-action" onClick={() => { setStudyPlannerOpen(true); closeMenu() }}><CalendarDays /> Study planner</button><button className="nav-action" onClick={() => { setChatOpen(true); closeMenu() }}><MessageSquare /> Conversations</button><button className="nav-action" onClick={() => { setSsbGuidanceOpen(true); closeMenu() }}><ShieldCheck /> SSB Guidance</button><button className="nav-action" disabled={!assessmentExam} onClick={() => { setAssessmentOpen(true); closeMenu() }} title="Open adaptive assessment"><GraduationCap /> Assessments</button></nav>
      <div className="side-bottom">
        <div className="account-menu-anchor" ref={accountMenuRef}>
          {accountMenuOpen && <div className="account-menu" role="menu" aria-label="Account menu">
            <div className="account-menu-identity">
              <Avatar text={initials} />
              <span><b>{user.full_name}</b><small>Free</small></span>
              <ChevronRight className="account-menu-chevron" />
            </div>
            <div className="account-menu-divider" />
            <button className="account-menu-item" role="menuitem" onClick={() => openSettings('profile')}>
              <UserRound /><span>Profile</span>
            </button>
            <button className="account-menu-item" role="menuitem" onClick={() => openSettings('settings')}>
              <Settings2 /><span>Settings</span>
            </button>
            <div className="account-menu-divider account-menu-secondary-divider" />
            <button className="account-menu-item account-menu-logout" role="menuitem" onClick={signOut}>
              <LogOut /><span>Log out</span>
            </button>
          </div>}
          <button className="account account-trigger" aria-haspopup="menu" aria-expanded={accountMenuOpen} onClick={() => setAccountMenuOpen(open => !open)}>
            <Avatar text={initials} /><span><b>{user.full_name}</b><small>Free</small></span>
          </button>
        </div>
      </div>
    </aside>
    <div className="overlay" onClick={closeMenu} />
    <main className="workspace">
      <section className="content dashboard-content">
        <button className="dashboard-mobile-menu" onClick={() => setMenu(true)} title="Open menu"><Menu /></button>
        <div className="dashboard-heading">
          <div>
            <span className="eyebrow"><Sparkles /> YOUR PERSONAL NDA COMMAND CENTER</span>
            <h1>Don't dream. Take action and make it reality.</h1>
            <p>Hello, {user.full_name.split(' ')[0]}. What will you work on today?</p>
          </div>
          <div className="dashboard-date"><CalendarDays /><span>{currentTime.toLocaleDateString(undefined, { weekday: 'long', month: 'long', day: 'numeric' })}</span></div>
        </div>
        <section className="dashboard-hero">
          <div className="dashboard-hero-copy">
            <span className="dashboard-kicker"><span /> READY WHEN YOU ARE</span>
            <h2>Never give up.</h2>
            <h3>Make your next session<br />count.</h3>
            <p>Ask a question, get a clear explanation, and keep moving toward your goal.</p>
            <button className="dashboard-primary" onClick={() => setChatOpen(true)}>Talk to your learning assistant <ArrowRight /></button>
            <div className="dashboard-goal">
              <span>Exam goal</span>
              <b>{profile.exam_target}</b>
              <i />
              <small>{profile.current_level || 'Preparation in progress'}</small>
            </div>
          </div>
        </section>
        <section className="dashboard-next-steps" aria-labelledby="next-steps-heading">
          <div className="dashboard-section-heading">
            <div><span className="dashboard-section-label">YOUR WORKSPACE</span><h2 id="next-steps-heading">Choose your next step</h2></div>
            <span>Built around your NDA preparation</span>
          </div>
          <div className="dashboard-action-grid">
            <button className="dashboard-action-card action-chat" onClick={() => setChatOpen(true)}>
              <span className="action-icon"><MessageSquare /></span><span className="action-number">01 / ASK</span>
              <b>Learn with AI</b><small>Get clear answers and work through tricky concepts.</small><span className="action-link">Start a conversation <ArrowUpRight /></span>
            </button>
            <button className="dashboard-action-card action-plan" onClick={() => setStudyPlannerOpen(true)}>
              <span className="action-icon"><CalendarDays /></span><span className="action-number">02 / PLAN</span>
              <b>Plan your study</b><small>Turn your preparation into a focused daily routine.</small><span className="action-link">Open study planner <ArrowUpRight /></span>
            </button>
            <button className="dashboard-action-card action-curriculum" onClick={() => setCurriculum(true)}>
              <span className="action-icon"><BookOpen /></span><span className="action-number">03 / EXPLORE</span>
              <b>Browse curriculum</b><small>Find a subject or topic to start learning today.</small><span className="action-link">Explore subjects <ArrowUpRight /></span>
            </button>
            <button className="dashboard-action-card action-ssb" onClick={() => setSsbGuidanceOpen(true)}>
              <span className="action-icon"><ShieldCheck /></span><span className="action-number">04 / DEVELOP</span>
              <b>SSB Guidance</b><small>Build one OLQ each day and ask your SSB coach for advice.</small><span className="action-link">Open SSB guidance <ArrowUpRight /></span>
            </button>
          </div>
        </section>
      </section>
    </main>
    {settings && <Settings user={user} profile={profile} token={token} initials={initials} initialTab={settingsTab} close={() => closeWithMotion('.settings', () => setSettings(false))} saved={setProfile} deleted={signOut} />}
    {curriculum && <CurriculumBrowser token={token} profile={profile} close={() => closeWithMotion('.curriculum-browser', () => setCurriculum(false))} />}
    {chatOpen && <ChatPanel token={token} close={() => closeWithMotion('.chat-panel', () => setChatOpen(false))} />}
    {assessmentOpen && assessmentExam && <AssessmentPanel token={token} exam={assessmentExam} close={() => closeWithMotion('.assessment-panel', () => setAssessmentOpen(false))} />}
    {studyPlannerOpen && <StudyPlannerPanel token={token} close={() => closeWithMotion('.study-planner', () => setStudyPlannerOpen(false))} openCurriculum={() => closeWithMotion('.study-planner', () => { setStudyPlannerOpen(false); setCurriculum(true) })} />}
    {ssbGuidanceOpen && <SSBGuidancePanel token={token} close={() => closeWithMotion('.ssb-guidance-panel', () => setSsbGuidanceOpen(false))} />}
  </div>
}

function CurriculumBrowser({ token, profile, close }: { token: string; profile: Profile; close: () => void }) {
  const [exams, setExams] = useState<Exam[]>([]); const [subjects, setSubjects] = useState<Subject[]>([]); const [chapters, setChapters] = useState<Chapter[]>([]); const [topics, setTopics] = useState<Topic[]>([]); const [concepts, setConcepts] = useState<Concept[]>([]); const [selectedConcept, setSelectedConcept] = useState<Concept | null>(null); const [diagnostic, setDiagnostic] = useState(false); const [error, setError] = useState(''); const [busy, setBusy] = useState(true)
  useEffect(() => { api.exams().then(setExams).catch(cause => setError(cause instanceof Error ? cause.message : 'Unable to load curriculum.')).finally(() => setBusy(false)) }, [])
  const loadSubjects = async (exam: Exam) => { setBusy(true); setError(''); try { setSubjects(await api.subjects(exam.id)); setChapters([]); setTopics([]); setConcepts([]); setSelectedConcept(null) } catch (cause) { setError(cause instanceof Error ? cause.message : 'Unable to load subjects.') } finally { setBusy(false) } }
  const loadChapters = async (subject: Subject) => { setBusy(true); try { setChapters(await api.chapters(subject.id)); setTopics([]); setConcepts([]); setSelectedConcept(null) } catch (cause) { setError(cause instanceof Error ? cause.message : 'Unable to load chapters.') } finally { setBusy(false) } }
  const loadTopics = async (chapter: Chapter) => { setBusy(true); try { setTopics(await api.topics(chapter.id)); setConcepts([]); setSelectedConcept(null) } catch (cause) { setError(cause instanceof Error ? cause.message : 'Unable to load topics.') } finally { setBusy(false) } }
  const loadConcepts = async (topic: Topic) => { setBusy(true); try { setConcepts(await api.concepts(topic.id)); setSelectedConcept(null) } catch (cause) { setError(cause instanceof Error ? cause.message : 'Unable to load concepts.') } finally { setBusy(false) } }
  const selectConcept = (concept: Concept) => { setSelectedConcept(concept); setError('') }
  return <div className="settings-overlay"><section className="settings curriculum-browser"><header><div><span className="eyebrow">PHASE 4 CURRICULUM</span><h2>Choose a topic</h2><p>{profile.exam_target} curriculum hierarchy</p></div><button onClick={close} title="Close curriculum"><X /></button></header>{busy && <p className="loading-inline"><Loader2 className="spin" /> Loading curriculum...</p>}{error && <p className="error">{error}</p>}<div className="curriculum-grid"><CurriculumList title="Exam" items={exams} label={item => `${item.name} (${item.code})`} onSelect={loadSubjects} /><CurriculumList title="Subject" items={subjects} label={item => item.name} onSelect={loadChapters} /><CurriculumList title="Chapter" items={chapters} label={item => item.name} onSelect={loadTopics} /><CurriculumList title="Topic" items={topics} label={item => item.name} onSelect={loadConcepts} /><CurriculumList title="Concept" items={concepts} selected={selectedConcept} label={item => item.name} onSelect={selectConcept} /></div>{selectedConcept && <div className="curriculum-detail"><b>{selectedConcept.name}</b><p>{selectedConcept.description || 'No description has been added yet.'}</p><button className="diagnostic-start" onClick={() => setDiagnostic(true)}>Start diagnostic <ArrowRight /></button></div>}</section>{diagnostic && selectedConcept && <DiagnosticPanel token={token} concept={selectedConcept} close={() => closeWithMotion('.diagnostic-panel', () => setDiagnostic(false))} />}</div>
}

function CurriculumList<T extends { id: string }>({ title, items, selected, label, onSelect }: { title: string; items: T[]; selected?: T | null; label: (item: T) => string; onSelect: (item: T) => void }) { return <div className="curriculum-column"><small>{title}</small>{items.length === 0 ? <p className="muted">Select the previous level</p> : items.map(item => <button className={selected?.id === item.id ? 'selected' : ''} key={item.id} onClick={() => void onSelect(item)}>{label(item)}<ChevronDown /></button>)}</div> }

function Settings({ user, profile, token, initials, initialTab, close, saved, deleted }: { user: User; profile: Profile; token: string; initials: string; initialTab: 'profile' | 'settings'; close: () => void; saved: (profile: Profile) => void; deleted: () => void }) {
  const [tab, setTab] = useState<'profile' | 'settings'>(initialTab)
  const [academicStream, setAcademicStream] = useState<'Science' | 'Commerce' | 'Arts' | ''>(profile.academic_stream || '')
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState('')
  const [deleteOpen, setDeleteOpen] = useState(false)
  const [deleteBusy, setDeleteBusy] = useState(false)
  const [deleteError, setDeleteError] = useState('')

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); setBusy(true); const form = new FormData(event.currentTarget)
    try {
      const nextProfile = await api.updateProfile(token, {
        exam_target: String(form.get('target')),
        current_level: String(form.get('level')) || null,
        target_exam_date: String(form.get('date')) || null,
        learning_preferences: String(form.get('preferences')) || null,
        academic_stream: academicStream || null,
        science_group: academicStream === 'Science' ? String(form.get('science_group') || '') as 'A' | 'B' : null,
        student_phone: String(form.get('studentPhone')).trim() || null,
        guardian_report_consent: form.get('guardianConsent') === 'on',
      })
      saved(nextProfile)
      setMsg('Profile saved successfully.')
    } catch (cause) {
      setMsg(cause instanceof Error ? cause.message : 'Unable to save.')
    } finally {
      setBusy(false)
    }
  }

  const deleteAccount = async () => {
    setDeleteBusy(true)
    setDeleteError('')
    try {
      await api.deleteAccount(token)
      deleted()
    } catch (cause) {
      setDeleteError(cause instanceof Error ? cause.message : 'Unable to delete this account.')
      setDeleteBusy(false)
    }
  }

  return <div className="settings-overlay"><section className="settings"><header><div><span className="eyebrow">YOUR ACCOUNT</span><h2>Profile</h2></div><button onClick={close} title="Close profile"><X /></button></header><div className="settings-tabs" role="tablist" aria-label="Profile and settings tabs"><button className={tab === 'profile' ? 'selected' : ''} role="tab" aria-selected={tab === 'profile'} onClick={() => setTab('profile')}>Profile</button><button className={tab === 'settings' ? 'selected' : ''} role="tab" aria-selected={tab === 'settings'} onClick={() => setTab('settings')}>Settings</button></div>
      {tab === 'profile' ? <>
        <div className="identity"><Avatar text={initials} /><div><b>{user.full_name}</b><p>{user.email}</p><small>{user.role === 'admin' ? 'Administrator' : 'Student account'}</small></div></div>
        <div className="profile-summary">
          <div><small>Exam target</small><b>{profile.exam_target}</b></div>
          <div><small>Current level</small><b>{profile.current_level || 'Not set'}</b></div>
          <div><small>Academic stream</small><b>{profile.academic_stream ? `${profile.academic_stream}${profile.science_group ? ` · Group ${profile.science_group}` : ''}` : 'Not set'}</b></div>
          <div><small>Target exam date</small><b>{profile.target_exam_date ? new Date(profile.target_exam_date).toLocaleDateString() : 'Not set'}</b></div>
        </div>
        <div className="profile-pref"><small>Learning preferences</small><p>{profile.learning_preferences || 'No preferences saved yet.'}</p></div>
        <div className="profile-pref"><small>Parent WhatsApp</small><p>{profile.parent_phone || 'Not set'} · progress reports {profile.guardian_report_consent_at ? 'enabled' : 'disabled'}</p></div>
      </> : <>
        <form onSubmit={submit}><label>Exam target<select name="target" defaultValue={profile.exam_target}><option>NDA</option><option>NDA I 2027</option><option>NDA II 2027</option></select></label><label>Academic stream<select name="academic_stream" value={academicStream} onChange={event => setAcademicStream(event.target.value as 'Science' | 'Commerce' | 'Arts' | '')} required><option value="">Choose your stream</option><option value="Science">Science</option><option value="Commerce">Commerce</option><option value="Arts">Arts</option></select></label>{academicStream === 'Science' && <label>Science group<select name="science_group" defaultValue={profile.science_group || ''} required><option value="" disabled>Choose Group A or B</option><option value="A">Group A</option><option value="B">Group B</option></select></label>}<label>Current preparation level<select name="level" defaultValue={profile.current_level || ''}><option value="">Choose a level</option><option>Beginner</option><option>Intermediate</option><option>Advanced</option></select></label><label>Target exam date<input name="date" type="date" defaultValue={profile.target_exam_date || ''} /></label><label>Student phone (optional)<input name="studentPhone" type="tel" inputMode="tel" pattern="^\+[1-9][0-9]{7,14}$" defaultValue={profile.student_phone || ''} placeholder="+919876543210" /></label><label>How do you prefer to learn?<textarea name="preferences" defaultValue={profile.learning_preferences || ''} placeholder="For example: short explanations, more practice questions..." /></label><label className="guardian-consent"><span><input type="checkbox" name="guardianConsent" defaultChecked={Boolean(profile.guardian_report_consent_at)} /> Parent/legal guardian consent for weekly and monthly WhatsApp progress reports at {profile.parent_phone || 'the registered parent number'}.</span></label>{msg && <p className={msg.includes('success') ? 'success-msg' : 'error'}>{msg}</p>}<button className="primary" disabled={busy}>{busy ? <Loader2 className="spin" /> : <><Check /> Save changes</>}</button></form>
        <section className="danger-zone"><div><b>Delete account</b><p>Permanently remove your account, study history, and saved learning data.</p></div><button type="button" onClick={() => { setDeleteError(''); setDeleteOpen(true) }}>Delete my account</button></section>
      </>}
      {deleteOpen && <div className="delete-account-backdrop" role="presentation" onMouseDown={event => { if (event.target === event.currentTarget && !deleteBusy) setDeleteOpen(false) }}><section className="delete-account-dialog" role="alertdialog" aria-modal="true" aria-labelledby="delete-account-title" aria-describedby="delete-account-description"><span className="delete-account-icon"><X /></span><h3 id="delete-account-title">Delete your account?</h3><p id="delete-account-description">This permanently deletes your profile, conversations, study plans, and learning history. You will be signed out immediately.</p>{deleteError && <p className="delete-account-error" role="alert">{deleteError}</p>}<div className="delete-account-actions"><button type="button" className="cancel-delete" onClick={() => setDeleteOpen(false)} disabled={deleteBusy}>Cancel</button><button type="button" className="confirm-delete" onClick={() => void deleteAccount()} disabled={deleteBusy}>{deleteBusy ? <><Loader2 className="spin" /> Deleting…</> : 'Delete account permanently'}</button></div></section></div>}
    </section></div>
}

function Mark() { return <span className="mark"><img src="/nda-emblem.png" alt="" /></span> }
function Avatar({ text }: { text: string }) { return <span className="avatar">{text}</span> }
