import { useCallback, useEffect, useState } from 'react'
import { ArrowRight, Check, ChevronRight, Clock3, Loader2, Sparkles, TrendingDown, TrendingUp, Trophy, X } from 'lucide-react'
import { api, AssessmentAttempt, AssessmentHistory, AssessmentReport, Exam } from './services/api'
import './assessment.css'

export default function AssessmentPanel({ token, exam, close }: { token: string; exam: Exam; close: () => void }) {
  const [attempt, setAttempt] = useState<AssessmentAttempt | null>(null)
  const [report, setReport] = useState<AssessmentReport | null>(null)
  const [history, setHistory] = useState<AssessmentHistory | null>(null)
  const [scheduleType, setScheduleType] = useState<'weekly' | 'monthly'>('weekly')
  const [selected, setSelected] = useState('')
  const [busy, setBusy] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [launching, setLaunching] = useState(false)
  const [error, setError] = useState('')
  const [skipDialog, setSkipDialog] = useState<{ type: 'confirm' } | { type: 'error'; message: string } | null>(null)
  const [now, setNow] = useState(Date.now())
  const [clockBaseline, setClockBaseline] = useState(Date.now())
  const [expiredRefreshKey, setExpiredRefreshKey] = useState('')
  const resetClock = useCallback(() => {
    const timestamp = Date.now()
    setClockBaseline(timestamp)
    setNow(timestamp)
  }, [])

  useEffect(() => {
    let cancelled = false
    api.assessmentHistory(token, exam.id)
      .then(async nextHistory => {
        if (cancelled) return
        setHistory(nextHistory)
        const activeAttempt = nextHistory.history.find(item => item.status === 'in_progress')
        if (activeAttempt) {
          const resumed = await api.assessment(token, activeAttempt.id)
          if (cancelled) return
          setAttempt(resumed)
          resetClock()
          if (resumed.status === 'completed') {
            const [completedReport, updatedHistory] = await Promise.all([
              api.assessmentReport(token, resumed.id),
              api.assessmentHistory(token, exam.id),
            ])
            if (cancelled) return
            setReport(completedReport)
            setHistory(updatedHistory)
          }
        }
      })
      .catch(cause => {
        if (!cancelled) setError(cause instanceof Error ? cause.message : 'Unable to load mock-test history.')
      })
      .finally(() => {
        if (!cancelled) setBusy(false)
      })
    return () => { cancelled = true }
  }, [token, exam.id, resetClock])

  useEffect(() => {
    if (attempt?.status !== 'in_progress') return
    const timer = window.setInterval(() => setNow(Date.now()), 1000)
    return () => window.clearInterval(timer)
  }, [attempt?.id, attempt?.status])

  const secondsLeft = attempt
    ? Math.max(0, attempt.section_time_limit_seconds - attempt.section_elapsed_seconds - Math.floor((now - clockBaseline) / 1000))
    : 0
  const displayTime = (seconds: number) => `${Math.floor(seconds / 3600).toString().padStart(2, '0')}:${Math.floor((seconds % 3600) / 60).toString().padStart(2, '0')}:${(seconds % 60).toString().padStart(2, '0')}`

  const start = async () => {
    setBusy(true)
    setLaunching(true)
    setError('')
    try {
      const next = await api.startAssessment(token, exam.id, scheduleType)
      setAttempt(next)
      resetClock()
      setExpiredRefreshKey('')
      setSelected('')
    }
    catch (cause) { setError(cause instanceof Error ? cause.message : 'Unable to start this mock test.') }
    finally { setBusy(false); setLaunching(false) }
  }

  const reloadReport = async () => {
    if (!attempt) return
    setBusy(true)
    setError('')
    try {
      const [nextReport, nextHistory] = await Promise.all([
        api.assessmentReport(token, attempt.id),
        api.assessmentHistory(token, exam.id),
      ])
      setReport(nextReport)
      setHistory(nextHistory)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Unable to load the completed mock report.')
    } finally {
      setBusy(false)
    }
  }

  const startAnotherMock = async () => {
    setBusy(true)
    setError('')
    setReport(null)
    setAttempt(null)
    setSelected('')
    try {
      setHistory(await api.assessmentHistory(token, exam.id))
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Unable to refresh mock-test history.')
    } finally {
      setBusy(false)
    }
  }

  const submit = async () => {
    if (!attempt || !attempt.question) return
    setSubmitting(true)
    setError('')
    try {
      const next = await api.submitAssessment(token, attempt.id, attempt.question.id, selected || null)
      setAttempt(next)
      if (next.status === 'completed') {
        const [nextReport, nextHistory] = await Promise.all([
          api.assessmentReport(token, attempt.id),
          api.assessmentHistory(token, exam.id),
        ])
        setReport(nextReport)
        setHistory(nextHistory)
      } else {
        setAttempt(next)
      }
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'Unable to submit answer.') }
    finally { setSubmitting(false) }
  }

  const abandon = async () => {
    if (!attempt || attempt.status !== 'in_progress') return
    setSkipDialog(null)
    setBusy(true)
    setSubmitting(true)
    setError('')
    try {
      await api.abandonAssessment(token, attempt.id)
      setAttempt(null)
      setReport(null)
      setSelected('')
      setHistory(await api.assessmentHistory(token, exam.id))
    } catch (cause) {
      setSkipDialog({
        type: 'error',
        message: cause instanceof Error ? cause.message : 'Unable to skip this mock exam.',
      })
    } finally {
      setBusy(false)
      setSubmitting(false)
    }
  }

  const navigate = async (targetQuestionNumber: number) => {
    if (!attempt?.question) return
    setSubmitting(true)
    setError('')
    try {
      const next = await api.navigateAssessment(
        token,
        attempt.id,
        attempt.question.id,
        selected || null,
        targetQuestionNumber,
      )
      setAttempt(next)
      setSelected(next.question?.selected_option_id ?? '')
      resetClock()
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Unable to move to that question.')
    } finally {
      setSubmitting(false)
    }
  }

  const finishMathematics = async () => {
    if (!attempt?.question) return
    setSubmitting(true)
    setError('')
    try {
      const next = await api.finishAssessmentSection(
        token,
        attempt.id,
        attempt.question.id,
        selected || null,
      )
      setAttempt(next)
      setSelected(next.question?.selected_option_id ?? '')
      setExpiredRefreshKey('')
      resetClock()
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Unable to finish Mathematics.')
    } finally {
      setSubmitting(false)
    }
  }

  const startGat = async () => {
    if (!attempt) return
    setSubmitting(true)
    setError('')
    try {
      const next = await api.startGatSection(token, attempt.id)
      setAttempt(next)
      setSelected(next.question?.selected_option_id ?? '')
      setExpiredRefreshKey('')
      resetClock()
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Unable to start General Ability.')
    } finally {
      setSubmitting(false)
    }
  }

  const question = attempt?.question
  const metricList = (metrics: Record<string, { accuracy: number; correct_answers: number; total_questions: number }>) => Object.entries(metrics)
  useEffect(() => {
    setSelected(question?.selected_option_id ?? '')
  }, [question?.id, question?.selected_option_id])

  useEffect(() => {
    const attemptId = attempt?.id
    const attemptStatus = attempt?.status
    const refreshKey = `${attemptId}:${attempt?.current_round}`
    if (!attemptId || attemptStatus !== 'in_progress' || secondsLeft > 0 || expiredRefreshKey === refreshKey) return
    setExpiredRefreshKey(refreshKey)
    let cancelled = false
    api.assessment(token, attemptId)
      .then(async next => {
        if (cancelled) return
        setAttempt(next)
        resetClock()
        setSelected('')
        if (next.status === 'completed') {
          const [nextReport, nextHistory] = await Promise.all([
            api.assessmentReport(token, attemptId),
            api.assessmentHistory(token, exam.id),
          ])
          if (!cancelled) {
            setReport(nextReport)
            setHistory(nextHistory)
          }
        }
      })
      .catch(cause => {
        if (!cancelled) setError(cause instanceof Error ? cause.message : 'Unable to refresh the timed section.')
      })
    return () => { cancelled = true }
  }, [attempt?.id, attempt?.status, attempt?.current_round, exam.id, expiredRefreshKey, resetClock, secondsLeft, token])

  return <div className="assessment-overlay"><section className="assessment-panel">
    <header><div><span className="eyebrow">NDA MOCK EXAMINATION</span><h2>{exam.name}</h2><p>Timed Mathematics and General Ability sections with NDA-style negative marking.</p></div><button onClick={close} title="Close assessment"><X /></button></header>
    {busy && <p className="assessment-loading"><Loader2 className="spin" /> {launching ? 'Preparing your mock and generating questions if needed...' : attempt ? 'Preparing your assessment...' : 'Loading mock-test history...'}</p>}
    {error && <p className="error">{error}</p>}

    {!busy && !attempt && !report && <div className="mock-dashboard">
      <div className="mock-cadence-label">MOCK TEST CADENCE</div>
      <div className="mock-cadence">
        <button className={scheduleType === 'weekly' ? 'selected' : ''} onClick={() => setScheduleType('weekly')}><span>Weekly mock</span><small>25 Mathematics + 25 GAT · 15 minutes per section</small></button>
        <button className={scheduleType === 'monthly' ? 'selected' : ''} onClick={() => setScheduleType('monthly')}><span>Full-length NDA mock</span><small>120 Mathematics + 150 GAT · 2.5 hours per section</small></button>
      </div>
      <div className="mock-start-row"><span><Clock3 /> Two timed sections · one-third negative marking</span><button onClick={() => void start()}>Start {scheduleType} mock <ArrowRight /></button></div>
      <p className="assessment-ai-note">Questions are randomized from the published bank. When it runs short, new four-option questions are AI-generated and labeled; question generation requires an enabled AI provider.</p>
      {history && <>
        <div className="mock-trend-head"><div><small>RECENT PERFORMANCE</small><b>{history.average_score === null ? 'No completed mocks yet' : `${Math.round(history.average_score)}% average`}</b></div>{history.improvement_points !== null && <span className={history.improvement_points >= 0 ? 'trend-positive' : 'trend-negative'}>{history.improvement_points >= 0 ? <TrendingUp /> : <TrendingDown />}{history.improvement_points > 0 ? '+' : ''}{history.improvement_points} pts</span>}</div>
        {history.history.length > 0 && <div className="mock-history">{history.history.slice(0, 6).map(item => <div className="mock-history-row" key={item.id}><span className={`mock-kind ${item.schedule_type}`}>{item.schedule_type}</span><span>{new Date(item.started_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}</span><div className="mock-history-bar"><i style={{ width: `${item.score ?? 0}%` }} /></div><b>{item.score === null ? item.status.replace('_', ' ') : `${Math.round(item.score)}%`}</b></div>)}</div>}
        <div className="mock-recommendations"><small>WHAT TO IMPROVE</small>{history.recommendations.map((item, index) => <p key={`${item}-${index}`}><ChevronRight />{item}</p>)}</div>
      </>}
    </div>}

    {!busy && report && <div className="assessment-report"><Trophy /><h3>Mock complete</h3><strong>{Math.round(report.score)}%</strong><p>{report.correct_answers} of {report.total_questions} correct answers</p><p className="assessment-net-score">{report.net_marks} / {report.maximum_marks} net marks after penalties</p><div className="assessment-summary"><div><small>Average response</small><b>{Math.round(report.average_response_time_seconds)}s</b></div><div><small>Round performance</small>{Object.entries(report.round_performance).map(([round, accuracy]) => <span key={round}>{round}: {Math.round(accuracy)}%</span>)}</div><div><small>Difficulty performance</small>{metricList(report.difficulty_performance).map(([difficulty, metric]) => <span key={difficulty}>{difficulty}: {Math.round(metric.accuracy)}%</span>)}</div><div><small>Subject performance</small>{metricList(report.subject_performance).map(([subject, metric]) => <span key={subject}>{subject}: {Math.round(metric.accuracy)}%</span>)}</div><div><small>Recommended next steps</small>{report.recommendations.length ? report.recommendations.map((item, index) => <span key={`${item}-${index}`}>{item}</span>) : <span>Keep progressing with mixed practice.</span>}</div></div>{history && <div className="mock-updated-trend"><small>UPDATED MOCK AVERAGE</small><b>{history.average_score === null ? 'No completed mocks yet' : `${Math.round(history.average_score)}%`}</b>{history.improvement_points !== null && <span>{history.improvement_points >= 0 ? '+' : ''}{history.improvement_points} points versus previous mocks</span>}</div>}<div className="assessment-report-actions"><button onClick={() => void startAnotherMock()}><ArrowRight /> Take another mock</button><button onClick={close}>Close report <Check /></button></div></div>}

    {!busy && !report && attempt?.status === 'completed' && <div className="assessment-report"><Trophy /><h3>Mock complete</h3><p>Your completed mock report is not available right now.</p><button onClick={() => void reloadReport()}>Retry loading report <ArrowRight /></button></div>}

    {!busy && !report && attempt?.current_round === 'GAT_PENDING' && <div className="assessment-report assessment-section-gate"><Clock3 /><h3>Mathematics section complete</h3><p>Take a break if you need one. Your GAT section will start only when you choose to begin it.</p><p className="assessment-net-score">Complete both sections today by {attempt.same_day_deadline ? new Date(attempt.same_day_deadline).toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' }) : 'today'}.</p><button disabled={submitting} onClick={() => void startGat()}>{submitting ? <Loader2 className="spin" /> : <>Start GAT now <ArrowRight /></>}</button></div>}

    {!busy && !report && question && <><div className="assessment-meta"><span>Section: <b>{question.round_name === 'MATH' ? 'Mathematics' : 'General Ability Test'}</b></span><span>Question {question.question_number} of {question.total_questions}</span><span>{question.difficulty}</span><span className={secondsLeft < 300 ? 'assessment-timer urgent' : 'assessment-timer'}><Clock3 /> {displayTime(secondsLeft)}</span></div>{question.is_ai_generated && <span className="assessment-generated-badge"><Sparkles /> AI-generated practice question</span>}<h3 className="assessment-question">{question.prompt}</h3><div className="assessment-options">{question.options.map(option => <button className={selected === option.id ? 'selected' : ''} disabled={submitting || secondsLeft === 0} key={option.id} onClick={() => setSelected(option.id)}>{option.text}{selected === option.id && <Check />}</button>)}</div><div className="assessment-navigation"><button disabled={question.question_number <= 1 || submitting || secondsLeft === 0} onClick={() => void navigate(question.question_number - 1)}><ArrowRight className="assessment-previous-icon" /> Previous</button>{question.question_number < question.total_questions ? <button disabled={submitting || secondsLeft === 0} onClick={() => void navigate(question.question_number + 1)}>{submitting ? <Loader2 className="spin" /> : <>Next <ArrowRight /></>}</button> : question.round_name === 'MATH' ? <button disabled={submitting || secondsLeft === 0} onClick={() => void finishMathematics()}>{submitting ? <Loader2 className="spin" /> : <>Finish Mathematics <ArrowRight /></>}</button> : <button disabled={submitting || secondsLeft === 0} onClick={() => void submit()}>{submitting ? <Loader2 className="spin" /> : <>Submit exam <Check /></>}</button>}</div><p className="assessment-save-hint">Your selected answer is saved when you move between questions. You can change it before final submission.</p></>}
    {!busy && !report && attempt?.status === 'in_progress' && <div className="assessment-report-actions"><button disabled={submitting} onClick={() => setSkipDialog({ type: 'confirm' })}>Skip exam</button></div>}
  </section>
  {skipDialog && <div className="assessment-dialog-backdrop">
    <section className="assessment-dialog" role="alertdialog" aria-modal="true" aria-labelledby="assessment-dialog-title" aria-describedby="assessment-dialog-message">
      <div className="assessment-dialog-icon"><X /></div>
      <h3 id="assessment-dialog-title">{skipDialog.type === 'confirm' ? 'Skip this mock exam?' : 'Could not skip exam'}</h3>
      <p id="assessment-dialog-message">{skipDialog.type === 'confirm' ? 'Your attempt will be cancelled. No score or report will be created.' : skipDialog.message}</p>
      <div className="assessment-dialog-actions">
        {skipDialog.type === 'confirm'
          ? <>
            <button className="assessment-dialog-secondary" disabled={submitting} onClick={() => setSkipDialog(null)}>Keep exam</button>
            <button className="assessment-dialog-danger" disabled={submitting} onClick={() => void abandon()}>{submitting ? <Loader2 className="spin" /> : 'Yes, skip exam'}</button>
          </>
          : <button onClick={() => setSkipDialog(null)}>Close</button>}
      </div>
    </section>
  </div>}
  </div>
}
