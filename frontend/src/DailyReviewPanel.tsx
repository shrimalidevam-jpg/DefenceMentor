import { useEffect, useState } from 'react'
import { ArrowRight, Check, CircleCheck, Loader2, RotateCcw, X } from 'lucide-react'
import { api, DailyReview } from './services/api'
import './daily-review.css'
import './daily-review-realtime.css'

export default function DailyReviewPanel({ token, planDate, close }: { token: string; planDate: string; close: () => void }) {
  const [review, setReview] = useState<DailyReview | null>(null)
  const [selected, setSelected] = useState('')
  const [busy, setBusy] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    api.startStudyReview(token, planDate)
      .then(setReview)
      .catch(cause => setError(cause instanceof Error ? cause.message : 'Unable to start this revision exam.'))
      .finally(() => setBusy(false))
  }, [token, planDate])

  const startRetake = async () => {
    setBusy(true); setError('')
    try { setReview(await api.startStudyReview(token, planDate, true)); setSelected('') }
    catch (cause) { setError(cause instanceof Error ? cause.message : 'Unable to start a new attempt.') }
    finally { setBusy(false) }
  }

  const syncExam = async () => {
    setBusy(true); setError('')
    try { setReview(await api.startStudyReview(token, planDate)); setSelected('') }
    catch (cause) { setError(cause instanceof Error ? cause.message : 'Unable to reconnect to this exam.') }
    finally { setBusy(false) }
  }

  const submitAnswer = async () => {
    if (!review?.question || !selected) return
    setSubmitting(true)
    setError('')
    try {
      const answer = await api.answerDailyReview(token, review.id, review.question.id, selected)
      setReview(current => current ? {
        ...current,
        status: answer.completed ? 'completed' : current.status,
        answered_count: answer.answered_count,
        correct_answers: answer.correct_answers,
        score_marks: answer.score_marks,
        score: answer.score,
        question: answer.next_question,
      } : current)
      setSelected('')
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'Unable to submit this answer.') }
    finally { setSubmitting(false) }
  }

  const question = review?.question
  const completed = review?.status === 'completed'

  return <div className="daily-review-overlay" role="presentation" onMouseDown={event => { if (event.target === event.currentTarget) close() }}>
    <section className="daily-review-panel" role="dialog" aria-modal="true" aria-labelledby="daily-review-title">
      <header><div><span>15-MARK REVISION EXAM</span><h2 id="daily-review-title">{new Date(`${planDate}T00:00:00`).toLocaleDateString(undefined, { weekday: 'long', month: 'long', day: 'numeric' })}</h2><p>15 questions · 1 mark each · From the subjects in your plan</p></div><button onClick={close} title="Close revision test"><X /></button></header>
      {busy && <div className="daily-review-state"><Loader2 className="spin" /> Preparing your questions...</div>}
      {error && !review && <div className="daily-review-error"><p>{error}</p><button onClick={() => void syncExam()}>Try again <RotateCcw /></button><button onClick={close}>Close</button></div>}
      {!busy && completed && <div className="daily-review-result"><CircleCheck /><span>Exam complete · Attempt {review.attempt_no}</span><strong>{review.score_marks}/{review.max_marks}</strong><p>{review.correct_answers} of {review.question_count} correct · {Math.round(review.score || 0)}%</p>{error && <p className="daily-review-inline-error">{error}</p>}<button onClick={() => void startRetake()} disabled={busy}>Retake 15-mark exam <RotateCcw /></button><button onClick={close}>Done <Check /></button></div>}
      {!busy && !completed && question && <>
        <div className="daily-review-meta"><span>Question {question.question_number} of 15</span><span>{question.difficulty}</span><span>{review?.answered_count || 0}/15 answered</span></div>
        <div className="daily-review-progress"><span style={{ width: `${((question.question_number - 1) / question.total_questions) * 100}%` }} /></div>
        <h3 className="daily-review-question">{question.prompt}</h3>
        <div className="daily-review-options">{question.options.map(option => <button className={selected === option.id ? 'selected' : ''} disabled={submitting} key={option.id} onClick={() => setSelected(option.id)}>{option.text}{selected === option.id && <Check />}</button>)}</div>
        {error && <div className="daily-review-reconnect"><p className="daily-review-inline-error">{error}</p><button onClick={() => void syncExam()}>Sync exam status <RotateCcw /></button></div>}
        <button className="daily-review-submit" disabled={!selected || submitting} onClick={() => void submitAnswer()}>{submitting ? <Loader2 className="spin" /> : <>Save answer &amp; continue <ArrowRight /></>}</button>
      </>}
      {!busy && !completed && !question && review && <div className="daily-review-result"><RotateCcw /><span>Exam question unavailable</span><p>Your saved attempt is intact. Reconnect to load the current question.</p><button onClick={() => void syncExam()}>Reload exam <RotateCcw /></button><button onClick={close}>Close</button></div>}
    </section>
  </div>
}
