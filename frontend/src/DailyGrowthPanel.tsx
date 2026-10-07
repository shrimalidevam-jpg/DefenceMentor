import { useEffect, useState } from 'react'
import { ArrowRight, BookOpenText, Check, Loader2, RotateCcw, Shield, X } from 'lucide-react'
import { api, DailyGrowth } from './services/api'
import './daily-growth.css'

const optionLetters = ['A', 'B', 'C', 'D']

export default function DailyGrowthPanel({ token, close }: { token: string; close: () => void }) {
  const [daily, setDaily] = useState<DailyGrowth | null>(null)
  const [selected, setSelected] = useState('')
  const [busy, setBusy] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    api.dailyGrowth(token)
      .then(setDaily)
      .catch(cause => setError(cause instanceof Error ? cause.message : 'Unable to load daily practice.'))
      .finally(() => setBusy(false))
  }, [token])

  const answer = async (wordId: string) => {
    if (!selected) return
    setSaving(true)
    setError('')
    try {
      const result = await api.answerDailyVocabulary(token, wordId, selected)
      setDaily(current => current ? {
        ...current,
        answered_count: result.answered_count,
        correct_count: result.correct_count,
        score_percent: result.score_percent,
        questions: current.questions.map(question => question.id === wordId ? {
          ...question,
          selected_option: selected,
          correct_option: result.correct_option,
          is_correct: result.is_correct,
          explanation: result.meaning,
          example: result.example,
        } : question),
      } : current)
      setSelected('')
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'Unable to save your answer.') }
    finally { setSaving(false) }
  }

  const progress = daily ? daily.answered_count / daily.questions.length * 100 : 0
  const todayWord = daily?.questions.find(question => question.selected_option === null)

  return <div className="daily-growth-overlay" role="presentation" onMouseDown={event => { if (event.target === event.currentTarget) close() }}>
    <section className="daily-growth-panel" role="dialog" aria-modal="true" aria-labelledby="daily-growth-title">
      <header><div><span className="daily-growth-eyebrow"><BookOpenText /> DAILY ENGLISH + SSB</span><h2 id="daily-growth-title">A little practice, every day</h2><p>Five vocabulary questions and one SSB preparation tip.</p></div><button onClick={close} title="Close daily practice"><X /></button></header>
      {busy && <div className="daily-growth-loading"><Loader2 className="spin" /> Loading today's practice...</div>}
      {error && <p className="daily-growth-error">{error}</p>}
      {!busy && daily && <>
        <section className="ssb-tip"><div><Shield /><span>{daily.ssb_category}</span></div><h3>{daily.ssb_title}</h3><p>{daily.ssb_tip}</p></section>
        <div className="daily-growth-score"><span>Vocabulary practice</span><b>{daily.answered_count}/{daily.questions.length} answered</b>{daily.score_percent !== null && <strong>{Math.round(daily.score_percent)}%</strong>}</div>
        <div className="daily-growth-progress"><span style={{ width: `${progress}%` }} /></div>
        {todayWord ? <article className="vocab-card"><div className="vocab-count">WORD {daily.answered_count + 1} OF {daily.questions.length}</div><h3>{todayWord.word}</h3><p className="vocab-instruction">Choose the closest meaning.</p><div className="vocab-options">{optionLetters.map(letter => <button className={selected === letter ? 'selected' : ''} disabled={saving} key={letter} onClick={() => setSelected(letter)}><span>{letter}</span>{todayWord.options[letter]}</button>)}</div>{error && <p className="daily-growth-error">{error}</p>}<button className="daily-growth-submit" disabled={!selected || saving} onClick={() => void answer(todayWord.id)}>{saving ? <Loader2 className="spin" /> : <>Check answer <ArrowRight /></>}</button></article> : <div className="vocab-complete"><Check /><h3>Today's words complete</h3><strong>{daily.correct_count} / {daily.questions.length} correct</strong><p>Come back tomorrow for five new words and a new SSB tip.</p><button onClick={close}>Done <Check /></button></div>}
        <details className="vocab-review"><summary><RotateCcw /> Review today's answers</summary>{daily.questions.filter(question => question.selected_option).map(question => <article key={question.id}><b>{question.word}</b><span className={question.is_correct ? 'right' : 'wrong'}>{question.is_correct ? 'Correct' : `Correct answer: ${question.correct_option}. ${question.options[question.correct_option || '']}`}</span>{question.explanation && <p>{question.explanation}</p>}{question.example && <small>{question.example}</small>}</article>)}</details>
      </>}
    </section>
  </div>
}
