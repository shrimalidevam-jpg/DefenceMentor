import { useEffect, useState } from 'react'
import { ArrowRight, Check, Loader2, X } from 'lucide-react'
import { api, Concept, DiagnosticAnswer, DiagnosticQuestion } from './services/api'
import './diagnostic.css'

export default function DiagnosticPanel({ token, concept, close }: { token: string; concept: Concept; close: () => void }) {
  const [questions, setQuestions] = useState<DiagnosticQuestion[]>([])
  const [index, setIndex] = useState(0)
  const [answer, setAnswer] = useState<DiagnosticAnswer | null>(null)
  const [selected, setSelected] = useState('')
  const [busy, setBusy] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  useEffect(() => { api.startDiagnostic(token, concept.id).then(result => setQuestions(result.questions)).catch(cause => setError(cause instanceof Error ? cause.message : 'Unable to start diagnostic.')).finally(() => setBusy(false)) }, [token, concept.id])
  const question = questions[index]
  const submit = async () => { if (!question || !selected) return; setSubmitting(true); setError(''); try { setAnswer(await api.answerDiagnostic(token, question.id, selected)) } catch (cause) { setError(cause instanceof Error ? cause.message : 'Unable to submit answer.') } finally { setSubmitting(false) } }
  const next = () => { setSelected(''); setAnswer(null); setIndex(current => current + 1) }
  return <div className="diagnostic-overlay"><section className="diagnostic-panel"><header><div><span className="eyebrow">PHASE 8 DIAGNOSTIC</span><h2>{concept.name}</h2><p>Check the prerequisite knowledge before learning this concept.</p></div><button onClick={close} title="Close diagnostic"><X /></button></header>{busy && <div className="diagnostic-loading"><Loader2 className="spin" /> Loading diagnostic questions...</div>}{error && <p className="error">{error}</p>}{!busy && !error && question && <><div className="diagnostic-progress">Question {index + 1} of {questions.length}<span>{question.difficulty}</span></div><div className="diagnostic-question"><h3>{question.prompt}</h3><div className="diagnostic-options">{question.options.map(option => <button className={selected === option.id ? 'selected' : ''} disabled={Boolean(answer)} key={option.id} onClick={() => setSelected(option.id)}>{option.text}{selected === option.id && <Check />}</button>)}</div></div>{answer ? <div className={answer.is_correct ? 'diagnostic-result correct' : 'diagnostic-result incorrect'}><b>{answer.is_correct ? 'Correct answer' : 'Review this prerequisite'}</b><p>{answer.explanation || answer.next_step}</p>{answer.mastery_score !== null && <small>Current concept mastery evidence: {answer.mastery_score}%</small>}{index + 1 < questions.length ? <button onClick={next}>Next question <ArrowRight /></button> : <button onClick={close}>Finish diagnostic <Check /></button>}</div> : <button className="diagnostic-submit" disabled={!selected || submitting} onClick={() => void submit()}>{submitting ? <Loader2 className="spin" /> : <>Check answer <ArrowRight /></>}</button>}</>}</section></div>
}
