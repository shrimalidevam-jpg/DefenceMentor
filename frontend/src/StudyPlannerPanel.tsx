import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { ArrowRight, BookOpen, CalendarDays, Check, Clock3, History, Loader2, RefreshCw, Settings2, Target, X } from 'lucide-react'
import { api, StudyPlan, StudyPlannerPreferences } from './services/api'
import DailyReviewPanel from './DailyReviewPanel'
import DailyGrowthPanel from './DailyGrowthPanel'
import StudyActivityCalendar from './StudyActivityCalendar'
import { closeWithMotion } from './motion'
import './study-planner.css'
import './study-planner-adaptive.css'

const taskLabels = { learn: 'Learn', revise: 'Review', practice: 'Practice' }
const defaultPreferences: StudyPlannerPreferences = { planner_setup_complete: false, daily_study_minutes: 360, study_start_time: '08:00', focus_session_minutes: 50, break_minutes: 10, study_subjects: [], math_share_percent: 50 }

export default function StudyPlannerPanel({ token, close, openCurriculum }: { token: string; close: () => void; openCurriculum: () => void }) {
  const [plan, setPlan] = useState<StudyPlan | null>(null)
  const [busy, setBusy] = useState(true)
  const [savingId, setSavingId] = useState('')
  const [revisionOpen, setRevisionOpen] = useState(false)
  const [revisionPlanDate, setRevisionPlanDate] = useState('')
  const [growthOpen, setGrowthOpen] = useState(false)
  const [calendarOpen, setCalendarOpen] = useState(false)
  const [dayView, setDayView] = useState<'today' | 'tomorrow'>('today')
  const [tomorrowBusy, setTomorrowBusy] = useState(false)
  const [tomorrowPlan, setTomorrowPlan] = useState<StudyPlan | null>(null)
  const [error, setError] = useState('')
  const [preferences, setPreferences] = useState<StudyPlannerPreferences>(defaultPreferences)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [preferencesBusy, setPreferencesBusy] = useState(false)
  const [selectedSubjects, setSelectedSubjects] = useState<('MATH' | 'GAT')[]>([])

  useEffect(() => {
    api.studyPlannerPreferences(token)
      .then(async savedPreferences => {
        setPreferences(savedPreferences)
        setSelectedSubjects(savedPreferences.study_subjects)
        if (savedPreferences.planner_setup_complete) setPlan(await api.todayStudyPlan(token))
      })
      .catch(cause => setError(cause instanceof Error ? cause.message : 'Unable to load your study plan.'))
      .finally(() => setBusy(false))
  }, [token])

  const toggleTask = async (taskId: string, isCompleted: boolean) => {
    setSavingId(taskId)
    setError('')
    try { setPlan(await api.updateStudyTask(token, taskId, !isCompleted)) }
    catch (cause) { setError(cause instanceof Error ? cause.message : 'Unable to update this task.') }
    finally { setSavingId('') }
  }

  const openTomorrow = async () => {
    setDayView('tomorrow')
    if (tomorrowPlan) return
    setTomorrowBusy(true)
    setError('')
    try { setTomorrowPlan(await api.tomorrowStudyPlan(token)) }
    catch (cause) { setError(cause instanceof Error ? cause.message : 'Unable to build tomorrow’s plan.') }
    finally { setTomorrowBusy(false) }
  }
  const regenerateTomorrow = async () => {
    setTomorrowBusy(true)
    setError('')
    try { setTomorrowPlan(await api.regenerateTomorrowStudyPlan(token)) }
    catch (cause) { setError(cause instanceof Error ? cause.message : 'Unable to refresh tomorrow’s plan.') }
    finally { setTomorrowBusy(false) }
  }
  const savePreferences = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (selectedSubjects.length === 0) { setError('Choose Mathematics, GAT, or both to build your plan.'); return }
    const form = new FormData(event.currentTarget)
    const next: StudyPlannerPreferences = {
      planner_setup_complete: true,
      daily_study_minutes: Number(form.get('daily_study_minutes')),
      study_start_time: String(form.get('study_start_time')),
      focus_session_minutes: Number(form.get('focus_session_minutes')),
      break_minutes: Number(form.get('break_minutes')),
      study_subjects: selectedSubjects,
      math_share_percent: selectedSubjects.length === 2 ? Number(form.get('math_share_percent')) : preferences.math_share_percent,
    }
    setPreferencesBusy(true); setError('')
    try { setPreferences(await api.updateStudyPlannerPreferences(token, next)); setPlan(await api.todayStudyPlan(token)); setTomorrowPlan(null); setDayView('today'); setSettingsOpen(false) }
    catch (cause) { setError(cause instanceof Error ? cause.message : 'Unable to save your study routine.') }
    finally { setPreferencesBusy(false) }
  }
  const activePlan = dayView === 'today' ? plan : tomorrowPlan
  const isBusy = busy || (dayView === 'tomorrow' && tomorrowBusy)
  const dateLabel = activePlan ? new Date(`${activePlan.plan_date}T00:00:00`).toLocaleDateString(undefined, { weekday: 'long', month: 'long', day: 'numeric' }) : ''
  const progress = activePlan?.tasks.length ? (activePlan.completed_count / activePlan.tasks.length) * 100 : 0

  return <div className="study-planner-overlay" role="presentation" onMouseDown={event => { if (event.target === event.currentTarget) close() }}>
    <section className="study-planner" role="dialog" aria-modal="true" aria-labelledby="study-planner-title">
      <header className="study-planner-header">
        <div><span className="study-planner-eyebrow"><CalendarDays /> ADAPTIVE HOME STUDY DAY</span><h2 id="study-planner-title">{preferences.planner_setup_complete ? (dayView === 'today' ? "Today's study day" : "Tomorrow's plan") : 'Build your study plan'}</h2><p>{dateLabel || (preferences.planner_setup_complete ? 'Your plan follows your choices and progress.' : 'Tell us which subjects, hours, and study rhythm work for you.')}</p></div>
        <button className="study-planner-close" onClick={close} title="Close study plan"><X /></button>
      </header>
      {!isBusy && !preferences.planner_setup_complete && <div className="study-planner-setup">
        <div><h3>How do you want to study?</h3><p>Choose your subjects and daily routine. You can change any choice later.</p></div>
        <form className="study-routine-form" onSubmit={event => void savePreferences(event)}>
          <fieldset className="study-subject-choices"><legend>Which NDA subjects should we plan for?</legend>
            <label><input type="checkbox" checked={selectedSubjects.includes('MATH')} onChange={() => setSelectedSubjects(current => current.includes('MATH') ? current.filter(subject => subject !== 'MATH') : [...current, 'MATH'])} /><span><b>Mathematics</b><small>Concept learning, revision, and practice</small></span></label>
            <label><input type="checkbox" checked={selectedSubjects.includes('GAT')} onChange={() => setSelectedSubjects(current => current.includes('GAT') ? current.filter(subject => subject !== 'GAT') : [...current, 'GAT'])} /><span><b>General Ability Test (GAT)</b><small>English and general knowledge areas</small></span></label>
          </fieldset>
          {selectedSubjects.length === 2 && <label>Time split for Mathematics<select required name="math_share_percent" defaultValue=""><option value="" disabled>Choose how to split your time</option><option value="30">30% Math · 70% GAT</option><option value="40">40% Math · 60% GAT</option><option value="50">Equal time</option><option value="60">60% Math · 40% GAT</option><option value="70">70% Math · 30% GAT</option></select></label>}
          <label>How much do you want to study per day?<select required name="daily_study_minutes" defaultValue=""><option value="" disabled>Choose your daily study time</option><option value="120">2 hours</option><option value="180">3 hours</option><option value="240">4 hours</option><option value="360">6 hours</option><option value="480">8 hours</option><option value="600">10 hours</option><option value="720">12 hours</option></select></label>
          <label>What time would you like to start?<input required type="time" name="study_start_time" defaultValue="" /></label>
          <label>How long can you focus at a time?<select required name="focus_session_minutes" defaultValue=""><option value="" disabled>Choose a focus session</option><option value="25">25 minutes</option><option value="40">40 minutes</option><option value="50">50 minutes</option><option value="60">60 minutes</option><option value="90">90 minutes</option></select></label>
          <label>How long of a break do you want?<select required name="break_minutes" defaultValue=""><option value="" disabled>Choose a break length</option><option value="5">5 minutes</option><option value="10">10 minutes</option><option value="15">15 minutes</option><option value="20">20 minutes</option><option value="30">30 minutes</option></select></label>
          <p>The plan uses your selected subjects, mastery, and unfinished work. You can adjust it whenever your day changes.</p>
          {error && <p className="study-planner-error">{error}</p>}
          <button className="study-routine-save" type="submit" disabled={preferencesBusy}>{preferencesBusy ? <Loader2 className="spin" /> : <Check />} Create my study plan</button>
        </form>
      </div>}
      {preferences.planner_setup_complete && <>
        <div className="study-plan-day-switch"><button className={dayView === 'today' ? 'selected' : ''} onClick={() => setDayView('today')}>Today</button><button className={dayView === 'tomorrow' ? 'selected' : ''} onClick={() => void openTomorrow()}>Tomorrow</button></div>
        <div className="study-routine-bar"><span>{preferences.study_subjects.includes('MATH') && preferences.study_subjects.includes('GAT') ? `Math ${preferences.math_share_percent}% · GAT ${100 - preferences.math_share_percent}%` : preferences.study_subjects.includes('MATH') ? 'Mathematics selected' : 'GAT selected'} · ${preferences.daily_study_minutes / 60} hours per day</span><div className="study-routine-actions"><button onClick={() => setCalendarOpen(true)}><History /> Activity calendar</button><button onClick={() => setSettingsOpen(value => !value)}><Settings2 /> Customize</button></div></div>
        {settingsOpen && <form className="study-routine-form" onSubmit={event => void savePreferences(event)}>
          <fieldset className="study-subject-choices"><legend>Choose the subjects you want in your plan</legend>
            <label><input type="checkbox" checked={selectedSubjects.includes('MATH')} onChange={() => setSelectedSubjects(current => current.includes('MATH') ? current.filter(subject => subject !== 'MATH') : [...current, 'MATH'])} /><span><b>Mathematics</b><small>Concepts, revision, and practice</small></span></label>
            <label><input type="checkbox" checked={selectedSubjects.includes('GAT')} onChange={() => setSelectedSubjects(current => current.includes('GAT') ? current.filter(subject => subject !== 'GAT') : [...current, 'GAT'])} /><span><b>General Ability Test (GAT)</b><small>English and general knowledge areas</small></span></label>
          </fieldset>
          {selectedSubjects.length === 2 && <label>Time split for Mathematics<select name="math_share_percent" defaultValue={preferences.math_share_percent}><option value="30">30% Math · 70% GAT</option><option value="40">40% Math · 60% GAT</option><option value="50">Equal time</option><option value="60">60% Math · 40% GAT</option><option value="70">70% Math · 30% GAT</option></select></label>}
          <label>Daily study goal<select required name="daily_study_minutes" defaultValue={preferences.daily_study_minutes}><option value="120">2 hours</option><option value="180">3 hours</option><option value="240">4 hours</option><option value="360">6 hours</option><option value="480">8 hours</option><option value="600">10 hours</option><option value="720">12 hours</option></select></label>
          <label>Start time<input required type="time" name="study_start_time" defaultValue={preferences.study_start_time} /></label>
          <label>Focus session<select required name="focus_session_minutes" defaultValue={preferences.focus_session_minutes}><option value="25">25 minutes</option><option value="40">40 minutes</option><option value="50">50 minutes</option><option value="60">60 minutes</option><option value="90">90 minutes</option></select></label>
          <label>Break length<select required name="break_minutes" defaultValue={preferences.break_minutes}><option value="5">5 minutes</option><option value="10">10 minutes</option><option value="15">15 minutes</option><option value="20">20 minutes</option><option value="30">30 minutes</option></select></label>
          <p>Completed topics stay saved. Unfinished work is rebuilt around your new choices.</p>
          <button className="study-routine-save" type="submit" disabled={preferencesBusy}>{preferencesBusy ? <Loader2 className="spin" /> : <Check />} Save my choices</button>
        </form>}
      </>}
      {isBusy && <div className="study-planner-state"><Loader2 className="spin" /> {dayView === 'today' ? 'Loading today’s plan...' : 'Building tomorrow’s plan from your progress...'}</div>}
      {error && preferences.planner_setup_complete && <p className="study-planner-error">{error}</p>}
      {preferences.planner_setup_complete && !isBusy && activePlan && <>
        <div className="study-planner-stats">
          <div><Clock3 /><span><b>{activePlan.total_minutes} min</b><small>Estimated study</small></span></div>
          <div><Check /><span><b>{activePlan.completed_count}/{activePlan.tasks.length}</b><small>{dayView === 'today' ? 'Tasks complete' : 'Planned tasks'}</small></span></div>
          <div><Target /><span><b>{activePlan.days_to_exam === null ? 'Not set' : activePlan.days_to_exam < 0 ? 'Date passed' : `${activePlan.days_to_exam} days`}</b><small>Until {activePlan.exam_target}</small></span></div>
        </div>
        <div className="study-planner-progress"><span style={{ width: `${progress}%` }} /></div>
        {dayView === 'tomorrow' && <div className="tomorrow-plan-note"><span>PREVIEW</span>Unfinished topics come first, followed by weak or new concepts. This plan will become your schedule tomorrow.</div>}
        {activePlan.schedule.length ? <div className="study-day-timeline">{activePlan.schedule.map((block, index) => {
          const task = block.task_id ? activePlan.tasks.find(item => item.id === block.task_id) : undefined
          return <article className={`study-day-block ${block.kind}${block.is_completed ? ' completed' : ''}`} key={`${block.kind}-${block.start_time}-${index}`}>
            <time>{block.start_time}<small>{block.end_time}</small></time>
            {task && <button className="study-task-check" onClick={() => void toggleTask(task.id, task.is_completed)} disabled={dayView === 'tomorrow' || savingId === task.id} aria-label={task.is_completed ? `Mark ${task.concept_name} incomplete` : `Mark ${task.concept_name} complete`}>{savingId === task.id ? <Loader2 className="spin" /> : task.is_completed ? <Check /> : null}</button>}
            <div className="study-day-block-copy"><span>{block.label}{task ? ` · ${task.subject_name}` : ''}</span>{task && <><b>{task.concept_name}</b><small>{taskLabels[task.task_type]} · {task.mastery_score === null ? 'New topic' : `${Math.round(task.mastery_score)}% mastery`}</small></>}</div>
            <em>{block.duration_minutes} min</em>
          </article>
        })}</div> : <div className="study-planner-empty"><BookOpen /><h3>No curriculum topics yet</h3><p>Add curriculum topics to generate a personalized daily plan.</p><button onClick={openCurriculum}>Browse curriculum <ArrowRight /></button></div>}
        {dayView === 'tomorrow' && <>
          <div className="study-plan-review-action tomorrow-exam-action"><button disabled={activePlan.tasks.length === 0} onClick={() => { setRevisionPlanDate(activePlan.plan_date); setRevisionOpen(true) }}><Check /> Open tomorrow's 15-mark exam <ArrowRight /></button><small>Separate from today's result. Your answers and score save as you go.</small></div>
          <div className="study-plan-review-action tomorrow-refresh"><button disabled={tomorrowBusy} onClick={() => void regenerateTomorrow()}>{tomorrowBusy ? <Loader2 className="spin" /> : <RefreshCw />} Regenerate from today's progress</button></div>
        </>}
        {dayView === 'today' && <>
          {activePlan.tasks.length > 0 && <p className="study-planner-note">Tasks are prioritized from your recorded mastery. New topics come first; weaker topics receive review time.</p>}
          <div className="study-plan-review-action"><button disabled={activePlan.completed_count === 0} onClick={() => { setRevisionPlanDate(activePlan.plan_date); setRevisionOpen(true) }}><Check /> Start today's 15-mark exam <ArrowRight /></button>{activePlan.completed_count === 0 && <small>Complete at least one study task first.</small>}</div>
          <div className="study-plan-review-action daily-growth-action"><button onClick={() => setGrowthOpen(true)}><CalendarDays /> Daily words + SSB tip <ArrowRight /></button><small>Five vocabulary questions and one SSB preparation tip.</small></div>
        </>}
      </>}
    </section>
    {revisionOpen && <DailyReviewPanel token={token} planDate={revisionPlanDate} close={() => closeWithMotion('.daily-review-panel', () => setRevisionOpen(false))} />}
    {growthOpen && <DailyGrowthPanel token={token} close={() => closeWithMotion('.daily-growth-panel', () => setGrowthOpen(false))} />}
    {calendarOpen && <StudyActivityCalendar token={token} close={() => closeWithMotion('.study-activity-calendar', () => setCalendarOpen(false))} />}
  </div>
}
