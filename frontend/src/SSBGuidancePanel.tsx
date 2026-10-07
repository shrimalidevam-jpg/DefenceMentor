import { FormEvent, useEffect, useRef, useState } from 'react'
import { ArrowUp, BookOpenCheck, CheckCircle2, Loader2, MessageCircle, ShieldCheck, Sparkles, X } from 'lucide-react'
import { api, ApiError, DailySSBGuidance, SSBGuidanceMessage } from './services/api'

const OLQS = [
  ['Effective Intelligence', 'Find practical solutions to unfamiliar situations.'],
  ['Reasoning Ability', 'Think logically, weigh evidence and explain your decisions.'],
  ['Organising Ability', 'Plan people, time and resources toward a clear objective.'],
  ['Power of Expression', 'Communicate ideas clearly, calmly and with confidence.'],
  ['Social Adaptability', 'Adjust respectfully to different people and situations.'],
  ['Cooperation', 'Work constructively with others and contribute to shared goals.'],
  ['Sense of Responsibility', 'Take ownership of duties and follow through reliably.'],
  ['Initiative', 'Notice what needs doing and take thoughtful first steps.'],
  ['Self-Confidence', 'Trust your preparation while staying open to feedback.'],
  ['Speed of Decision', 'Make timely decisions after considering the relevant facts.'],
  ['Ability to Influence the Group', 'Help a group move forward through sound ideas and example.'],
  ['Liveliness', 'Bring positive energy and engage actively with people and tasks.'],
  ['Determination', 'Stay focused and persistent when work becomes difficult.'],
  ['Courage', 'Face challenges honestly and act despite reasonable apprehension.'],
  ['Stamina', 'Maintain steady effort and resilience over sustained demands.'],
] as const

export default function SSBGuidancePanel({ token, close }: { token: string; close: () => void }) {
  const [guidance, setGuidance] = useState<DailySSBGuidance | null>(null)
  const [guidanceError, setGuidanceError] = useState('')
  const [chatVisible, setChatVisible] = useState(false)
  const [secondsLeft, setSecondsLeft] = useState(10)
  const [messages, setMessages] = useState<SSBGuidanceMessage[]>([])
  const [draft, setDraft] = useState('')
  const [busy, setBusy] = useState(false)
  const [chatError, setChatError] = useState('')
  const messagesEnd = useRef<HTMLDivElement>(null)

  useEffect(() => {
    let active = true
    api.todaySSBGuidance(token)
      .then(result => { if (active) setGuidance(result) })
      .catch(cause => { if (active) setGuidanceError(cause instanceof Error ? cause.message : 'Unable to load today’s SSB guidance.') })
    api.ssbGuidanceChat(token)
      .then(result => { if (active) setMessages(result.messages) })
      .catch(cause => { if (active) setChatError(cause instanceof Error ? cause.message : 'Unable to load your SSB chat.') })
    return () => { active = false }
  }, [token])

  useEffect(() => {
    const timer = window.setInterval(() => {
      setSecondsLeft(current => {
        if (current <= 1) {
          window.clearInterval(timer)
          return 0
        }
        return current - 1
      })
    }, 1000)
    return () => window.clearInterval(timer)
  }, [])

  useEffect(() => {
    if (secondsLeft === 0) setChatVisible(true)
  }, [secondsLeft])

  useEffect(() => {
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') close()
    }
    window.addEventListener('keydown', closeOnEscape)
    return () => window.removeEventListener('keydown', closeOnEscape)
  }, [close])

  useEffect(() => {
    messagesEnd.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [messages, chatVisible])

  const send = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const content = draft.trim()
    if (!content || busy) return
    setBusy(true)
    setChatError('')
    try {
      const saved = await api.sendSSBGuidanceMessage(token, content)
      setMessages(current => [...current, ...saved])
      setDraft('')
    } catch (cause) {
      setChatError(cause instanceof ApiError ? cause.message : cause instanceof Error ? cause.message : 'Unable to send your message.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="ssb-overlay" role="presentation">
      <section className="ssb-guidance-panel" role="dialog" aria-modal="true" aria-labelledby="ssb-title">
        <header className="ssb-header">
          <div className="ssb-brand"><span><ShieldCheck /></span><div><small>YOUR NDA WORKSPACE</small><h2 id="ssb-title">SSB Guidance</h2></div></div>
          <button type="button" className="ssb-close" onClick={close} aria-label="Close SSB guidance"><X /></button>
        </header>

        <div className={`ssb-layout${chatVisible ? ' chat-visible' : ''}`}>
          <main className="ssb-learning">
            <section className="ssb-intro">
              <span className="ssb-eyebrow"><Sparkles /> BUILD REAL OFFICER-LIKE QUALITIES</span>
              <h1>Know the 15 OLQs</h1>
              <p>Use these qualities as a guide for genuine growth. They are not a scorecard or a guarantee of selection—focus on practising them honestly in daily life.</p>
            </section>

            <section className="ssb-olq-grid" aria-label="The 15 Officer Like Qualities">
              {OLQS.map(([name, description], index) => (
                <article className="ssb-olq-card" key={name}>
                  <span className="ssb-olq-number">{String(index + 1).padStart(2, '0')}</span>
                  <div><h3>{name}</h3><p>{description}</p></div>
                </article>
              ))}
            </section>

            <section className="ssb-daily-card" aria-live="polite">
              <div className="ssb-daily-heading"><span><Sparkles /></span><div><small>YOUR ONE GUIDANCE FOR TODAY</small><h2>{guidance?.title || 'Today’s SSB guidance'}</h2></div></div>
              {guidance ? <>
                <p>{guidance.guidance}</p>
                <div className="ssb-action"><CheckCircle2 /><span><b>Try this today</b>{guidance.action}</span></div>
                <p className="ssb-reflection"><b>Reflect:</b> {guidance.reflection_question}</p>
                <small className="ssb-date">Daily coaching · {new Date(`${guidance.guidance_date}T12:00:00`).toLocaleDateString(undefined, { dateStyle: 'long' })}</small>
              </> : guidanceError ? <p className="ssb-error" role="alert">{guidanceError}</p> : <p className="ssb-loading"><Loader2 className="ssb-spin" /> Preparing your daily guidance…</p>}
            </section>
          </main>

          <aside className={`ssb-chat${chatVisible ? ' is-visible' : ''}`} aria-hidden={!chatVisible}>
            {chatVisible ? <>
              <header className="ssb-chat-header"><span><MessageCircle /></span><div><b>Ask your SSB coach</b><small>SSB and personality-development support</small></div></header>
              <div className="ssb-chat-messages" aria-live="polite">
                <article className="ssb-chat-message assistant"><small>SSB COACH</small><p>First, please read these 15 OLQs above. Think about one quality you already practise and one you want to develop. Then ask me anything about SSB or personality development.</p></article>
                {messages.map(message => <article className={`ssb-chat-message ${message.role}`} key={message.id}><small>{message.role === 'user' ? 'YOU' : 'SSB COACH'}</small><p>{message.content}</p></article>)}
                {chatError && <p className="ssb-error" role="alert">{chatError}</p>}
                <div ref={messagesEnd} />
              </div>
              <form className="ssb-chat-form" onSubmit={event => void send(event)}>
                <label className="ssb-sr-only" htmlFor="ssb-chat-input">Ask a question about SSB</label>
                <textarea id="ssb-chat-input" value={draft} onChange={event => setDraft(event.target.value)} placeholder="Ask about SSB or personality development…" maxLength={4000} rows={2} />
                <button type="submit" disabled={busy || !draft.trim()} aria-label="Send SSB question">{busy ? <Loader2 className="ssb-spin" /> : <ArrowUp />}</button>
              </form>
              <small className="ssb-chat-note">Your SSB conversation is saved privately to your account.</small>
            </> : (
              <div className="ssb-chat-countdown"><span><BookOpenCheck /></span><h2>Start with the OLQs</h2><p>Read through the 15 qualities and consider how you can demonstrate them genuinely.</p><div className="ssb-countdown-track"><i style={{ width: `${((10 - secondsLeft) / 10) * 100}%` }} /></div><small>SSB chat opens in <b>{secondsLeft}</b> seconds</small></div>
            )}
          </aside>
        </div>
      </section>
    </div>
  )
}
