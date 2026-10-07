import { useEffect, useMemo, useState } from 'react'
import { ChevronLeft, ChevronRight, Clock3, Loader2, X } from 'lucide-react'
import { api, StudyCalendarDay } from './services/api'
import './study-activity-calendar.css'

const monthKey = (date: Date) => `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`
const dateKey = (year: number, month: number, day: number) => `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`

export default function StudyActivityCalendar({ token, close }: { token: string; close: () => void }) {
  const now = new Date()
  const [view, setView] = useState(() => new Date(now.getFullYear(), now.getMonth(), 1))
  const [selectedDate, setSelectedDate] = useState(dateKey(now.getFullYear(), now.getMonth(), now.getDate()))
  const [days, setDays] = useState<StudyCalendarDay[]>([])
  const [busy, setBusy] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    setBusy(true); setError('')
    api.studyCalendar(token, monthKey(view))
      .then(result => { if (active) { setDays(result.days); setSelectedDate(current => current.startsWith(`${result.month}-`) ? current : result.days[0]?.plan_date ?? `${result.month}-01`) } })
      .catch(cause => { if (active) setError(cause instanceof Error ? cause.message : 'Unable to load study activity.') })
      .finally(() => { if (active) setBusy(false) })
    return () => { active = false }
  }, [token, view])

  const activityByDate = useMemo(() => new Map(days.map(day => [day.plan_date, day])), [days])
  const year = view.getFullYear()
  const month = view.getMonth()
  const dayCount = new Date(year, month + 1, 0).getDate()
  const firstWeekday = new Date(year, month, 1).getDay()
  const selected = activityByDate.get(selectedDate)
  const currentMonth = monthKey(now)
  const isCurrentMonth = monthKey(view) === currentMonth
  const monthLabel = view.toLocaleDateString(undefined, { month: 'long', year: 'numeric' })

  return <div className="study-activity-overlay" role="presentation" onMouseDown={event => { if (event.target === event.currentTarget) close() }}>
    <section className="study-activity-calendar" role="dialog" aria-modal="true" aria-labelledby="study-activity-title">
      <header><div><span>STUDY HISTORY</span><h2 id="study-activity-title">Activity calendar</h2><p>Choose a day to review your study and exam activity.</p></div><button className="study-activity-close" onClick={close} aria-label="Close calendar"><X /></button></header>
      <div className="study-activity-month"><button onClick={() => setView(new Date(year, month - 1, 1))} aria-label="Previous month"><ChevronLeft /></button><h3>{monthLabel}</h3><button onClick={() => setView(new Date(year, month + 1, 1))} disabled={isCurrentMonth} aria-label="Next month"><ChevronRight /></button></div>
      {error && <p className="study-activity-error">{error}</p>}
      <div className="study-activity-grid" aria-label={monthLabel}>
        {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map(day => <span className="study-activity-weekday" key={day}>{day}</span>)}
        {Array.from({ length: firstWeekday }, (_, index) => <span className="study-activity-blank" key={`blank-${index}`} />)}
        {Array.from({ length: dayCount }, (_, index) => {
          const number = index + 1
          const key = dateKey(year, month, number)
          const activity = activityByDate.get(key)
          return <button key={key} className={`study-activity-date${selectedDate === key ? ' selected' : ''}${activity ? ' has-activity' : ''}`} onClick={() => setSelectedDate(key)} aria-pressed={selectedDate === key}>
            <span>{number}</span>{activity && <i aria-label={`${activity.tasks.length} study tasks and ${activity.exams.length} exams`}><b />{activity.exams.length > 0 && <b className="exam-dot" />}</i>}
          </button>
        })}
      </div>
      <section className="study-activity-details" aria-live="polite">
        <h3>{new Date(`${selectedDate}T00:00:00`).toLocaleDateString(undefined, { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' })}</h3>
        {busy ? <p className="study-activity-loading"><Loader2 className="spin" /> Loading activity…</p> : selected ? <>
          <div className="study-activity-summary"><span><Clock3 /> {selected.completed_minutes} of {selected.total_minutes} minutes completed</span><span>{selected.completed_count}/{selected.tasks.length} tasks</span></div>
          {selected.tasks.length > 0 && <div className="study-activity-list"><h4>Study tasks</h4>{selected.tasks.map(task => <article key={task.id} className={task.is_completed ? 'done' : ''}><span className="activity-status">{task.is_completed ? 'Completed' : 'Not completed'}</span><b>{task.concept_name}</b><small>{task.subject_name} · {task.task_type} · {task.estimated_minutes} min{task.completed_at ? ` · ${new Date(task.completed_at).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })}` : ''}</small></article>)}</div>}
          {selected.exams.length > 0 && <div className="study-activity-list"><h4>15-mark revision exam</h4>{selected.exams.map(exam => <article key={exam.id}><span className="activity-status">{exam.status === 'completed' ? 'Completed' : 'In progress'} · Attempt {exam.attempt_no}</span><b>{exam.status === 'completed' ? `${exam.score_marks}/${exam.max_marks} marks` : `${exam.answered_count}/${exam.question_count} answered`}</b><small>{exam.score_percent === null ? 'Score not recorded yet' : `${exam.score_percent}% score`}{exam.completed_at ? ` · ${new Date(exam.completed_at).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })}` : ''}</small></article>)}</div>}
        </> : <p className="study-activity-empty">No activity recorded for this day.</p>}
      </section>
    </section>
  </div>
}
