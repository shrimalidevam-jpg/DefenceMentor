import { ChangeEvent, FormEvent, useEffect, useId, useRef, useState } from 'react'
import { Check, Copy, Download, ExternalLink, FileText, Headphones, Image, Loader2, MessageSquare, Mic, MicOff, MoreHorizontal, Paperclip, Pencil, Plus, Send, ThumbsDown, ThumbsUp, Trash2, Volume2, VolumeX, X } from 'lucide-react'
import katex from 'katex'
import ReactMarkdown, { type Components } from 'react-markdown'
import { api, ApiError, ChatAttachment, ChatAttachmentUpload, ChatDocumentSource, ChatMessage, ChatSession } from './services/api'
import './chat.css'
import './chat-message-actions.css'
import './chat-manage-dialog.css'
import './chat-realtime.css'
import './chat-tutorial-links.css'
import './chat-diagram.css'
import 'katex/dist/katex.min.css'

let mermaidInitialized = false

function MermaidDiagram({ source }: { source: string }) {
  const id = `chat-diagram-${useId().replace(/:/g, '')}`
  const [svg, setSvg] = useState('')
  const [renderFailed, setRenderFailed] = useState(false)

  useEffect(() => {
    let cancelled = false
    const render = async () => {
      const { default: mermaid } = await import('mermaid')
      if (cancelled) return
      if (!mermaidInitialized) {
        mermaid.initialize({ startOnLoad: false, securityLevel: 'strict', theme: 'dark', flowchart: { htmlLabels: false } })
        mermaidInitialized = true
      }
      const result = await mermaid.render(id, source)
      if (!cancelled) setSvg(result.svg)
    }
    void render().catch(() => { if (!cancelled) setRenderFailed(true) })
    return () => { cancelled = true }
  }, [id, source])

  const download = () => {
    if (!svg) return
    const url = URL.createObjectURL(new Blob([svg], { type: 'image/svg+xml' }))
    const link = document.createElement('a')
    link.href = url
    link.download = 'nda-tutor-diagram.svg'
    link.click()
    window.setTimeout(() => URL.revokeObjectURL(url), 1000)
  }

  if (renderFailed) return <p className="chat-diagram-error">Could not render this diagram. Ask the tutor to try again.</p>
  return <div className="chat-diagram-wrap">
    {svg ? <div className="chat-diagram" role="img" aria-label="AI-generated educational diagram" dangerouslySetInnerHTML={{ __html: svg }} /> : <span className="chat-diagram-loading">Creating diagram...</span>}
    {svg && <button className="chat-diagram-download" onClick={download} title="Download diagram as SVG" aria-label="Download diagram as SVG"><Download /></button>}
  </div>
}

function getMermaidSource(content: string): string | null {
  return content.match(/```mermaid\s*([\s\S]*?)```/i)?.[1]?.trim() || null
}

function removeMermaidSource(content: string): string {
  return content.replace(/```mermaid\s*[\s\S]*?```/i, '').trim()
}

function prepareTutorSpeech(content: string): string {
  return content
    .replace(/```mermaid\s*[\s\S]*?```/gi, '')
    .replace(/```([\s\S]*?)```/g, '$1')
    .replace(/!\[([^\]]*)\]\([^)]*\)/g, '$1')
    .replace(/\[([^\]]+)\]\([^)]*\)/g, '$1')
    .replace(/^#{1,6}\s+/gm, '')
    .replace(/^\s*[-*+]\s+/gm, '')
    .replace(/^\s*\d+\.\s+/gm, '')
    .replace(/[*_~`]/g, '')
    .replace(/\$\$?|\$\$/g, '')
    .replace(/\\\[|\\\]|\\\(|\\\)/g, '')
    .replace(/\s+/g, ' ')
    .trim()
}

type TutorMathExpression = { latex: string; display: boolean }
type SpeechResultEvent = { results: ArrayLike<{ 0: { transcript: string } }> }
type SpeechRecognitionLike = {
  lang: string
  interimResults: boolean
  maxAlternatives: number
  onresult: ((event: SpeechResultEvent) => void) | null
  onerror: ((event: { error: string }) => void) | null
  onend: (() => void) | null
  start: () => void
  stop: () => void
  abort: () => void
}
type SpeechRecognitionWindow = Window & {
  SpeechRecognition?: new () => SpeechRecognitionLike
  webkitSpeechRecognition?: new () => SpeechRecognitionLike
}

const MAX_CHAT_FILE_BYTES = 4 * 1024 * 1024
const MAX_CHAT_FILES = 3
const MAX_CHAT_FILES_TOTAL_BYTES = 10 * 1024 * 1024

function getAttachmentMediaType(file: File): string | null {
  const extension = file.name.split('.').pop()?.toLowerCase()
  if (file.type === 'application/pdf' || extension === 'pdf') return 'application/pdf'
  if (file.type === 'image/jpeg' || ['jpg', 'jpeg'].includes(extension || '')) return 'image/jpeg'
  if (file.type === 'image/png' || extension === 'png') return 'image/png'
  if (file.type === 'image/webp' || extension === 'webp') return 'image/webp'
  return null
}

async function encodeChatAttachment(file: File): Promise<ChatAttachmentUpload> {
  const bytes = new Uint8Array(await file.arrayBuffer())
  let binary = ''
  for (let offset = 0; offset < bytes.length; offset += 0x8000) {
    binary += String.fromCharCode(...bytes.subarray(offset, offset + 0x8000))
  }
  const mediaType = getAttachmentMediaType(file)
  if (!mediaType) throw new Error(`Unsupported file type: ${file.name}`)
  return { file_name: file.name, media_type: mediaType, data_base64: btoa(binary) }
}

function prepareTutorMarkdown(content: string): { markdown: string; math: TutorMathExpression[] } {
  const math: TutorMathExpression[] = []
  const mathPattern = /\$\$([\s\S]+?)\$\$|\\\[([\s\S]+?)\\\]|\\\(([\s\S]+?)\\\)|(?<!\$)\$(?!\$)([^\n$]+?)(?<!\$)\$(?!\$)/g
  const markdown = content.replace(mathPattern, (match, blockDollar: string | undefined, blockBracket: string | undefined, inlineBracket: string | undefined, inlineDollar: string | undefined) => {
    const display = Boolean(blockDollar || blockBracket)
    const latex = blockDollar || blockBracket || inlineBracket || inlineDollar || match
    const index = math.push({ latex, display }) - 1
    const placeholder = `[math](https://nda-chat-math.invalid/equation-${index})`
    return display ? `\n\n${placeholder}\n\n` : placeholder
  })
  const normalized = markdown
    .replace(/\\(?:leq?|le)(?![a-z])/gi, '≤')
    .replace(/\\(?:geq?|ge)(?![a-z])/gi, '≥')
    .replace(/\\neq(?![a-z])/gi, '≠')
    .replace(/\\times(?![a-z])/gi, '×')
    .replace(/\\cdot(?![a-z])/gi, '·')
    .replace(/\\text\{([^{}]*)\}/g, '$1')
    .replace(/\\frac\{([^{}]*)\}\{([^{}]*)\}/g, '$1 / $2')
    .replace(/\\([{}])/g, '$1')
    .replace(/(?<!&)(?<!\\)<(?=\s|\d|[A-Za-z(])/g, '&lt;')
    .replace(/(?<!&)(?<!\\)>(?=\s|\d|[A-Za-z(])/g, '&gt;')
  return { markdown: normalized, math }
}

function TutorMarkdown({ content }: { content: string }) {
  const { markdown, math } = prepareTutorMarkdown(content)
  const components: Components = {
    a({ href, children, ...props }) {
      const match = href?.match(/^https:\/\/nda-chat-math\.invalid\/equation-(\d+)$/)
      if (match) {
        const expression = math[Number(match[1])]
        if (expression) {
          return <span className={expression.display ? 'chat-math display' : 'chat-math'} dangerouslySetInnerHTML={{ __html: katex.renderToString(expression.latex, { displayMode: expression.display, throwOnError: false, strict: 'ignore' }) }} />
        }
      }
      return <a href={href} target="_blank" rel="noopener noreferrer" {...props}>{children}</a>
    },
  }
  return <ReactMarkdown components={components}>{markdown}</ReactMarkdown>
}

function isTopicExplanation(content: string): boolean {
  const answer = content.trim()
  if (answer.length < 320) return false
  const hasTeachingStructure = /(?:^|\n)\s*(?:#{1,6}\s|\d+[.)]\s|[-*]\s)|\$\$?/m.test(answer)
  const hasTeachingLanguage = /\b(?:example|steps?|formula|concept|because|therefore|means)\b|ઉદાહરણ|પગલાં|સૂત્ર|કારણ|સમજાવ|અર્થ/i.test(answer)
  return hasTeachingStructure || hasTeachingLanguage
}

function isDirectDocumentLink(source: ChatDocumentSource): boolean {
  try {
    const url = new URL(source.url)
    const host = url.hostname.toLowerCase().replace(/^www\./, '')
    return ['http:', 'https:'].includes(url.protocol)
      && !['youtube.com', 'm.youtube.com', 'youtu.be'].includes(host)
      && !(host.endsWith('google.com') && url.pathname.startsWith('/search'))
  } catch {
    return false
  }
}

export default function ChatPanel({ token, close }: { token: string; close: () => void }) {
  const [sessions, setSessions] = useState<ChatSession[]>([])
  const [active, setActive] = useState<ChatSession | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [draft, setDraft] = useState('')
  const [selectedFiles, setSelectedFiles] = useState<File[]>([])
  const [voiceLanguage, setVoiceLanguage] = useState<'en-IN' | 'hi-IN'>(() => navigator.language.toLowerCase().startsWith('hi') ? 'hi-IN' : 'en-IN')
  const [oralExplanation, setOralExplanation] = useState(false)
  const [recording, setRecording] = useState(false)
  const [busy, setBusy] = useState(true)
  const [sending, setSending] = useState(false)
  const [error, setError] = useState('')
  const [realtime, setRealtime] = useState<'connecting' | 'connected' | 'offline'>('offline')
  const [realtimeDetail, setRealtimeDetail] = useState('')
  const [typing, setTyping] = useState(false)
  const [menuChatId, setMenuChatId] = useState<string | null>(null)
  const [messageFeedback, setMessageFeedback] = useState<Record<string, 'like' | 'dislike'>>({})
  const [copiedMessageId, setCopiedMessageId] = useState<string | null>(null)
  const [manageDialog, setManageDialog] = useState<{ type: 'rename' | 'delete'; chat: ChatSession } | null>(null)
  const [renameTitle, setRenameTitle] = useState('')
  const [dialogBusy, setDialogBusy] = useState(false)
  const [dialogError, setDialogError] = useState('')
  const socket = useRef<WebSocket | null>(null)
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const copiedTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const renameInput = useRef<HTMLInputElement | null>(null)
  const speechRecognition = useRef<SpeechRecognitionLike | null>(null)
  const speechUtterance = useRef<SpeechSynthesisUtterance | null>(null)
  const attachmentInput = useRef<HTMLInputElement | null>(null)
  const [speakingMessageId, setSpeakingMessageId] = useState<string | null>(null)

  const loadChats = async () => {
    setBusy(true); setError('')
    try {
      const nextSessions = await api.chats(token)
      setSessions(nextSessions)
      const draft = await api.draftChat(token)
      setActive(draft)
      setMessages([])
      connectSocket(draft.id)
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'Unable to load conversations.') } finally { setBusy(false) }
  }
  // Load once for the authenticated chat panel; token is fixed for this mounted panel.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { void loadChats() }, [])

  const connectSocket = (chatId: string, attempt = 0) => {
    if (reconnectTimer.current) clearTimeout(reconnectTimer.current)
    socket.current?.close()
    setRealtime('connecting')
    setRealtimeDetail(attempt > 0 ? `Reconnecting (attempt ${attempt})...` : '')
    const apiOrigin = import.meta.env.VITE_API_URL || window.location.origin
    const websocketOrigin = apiOrigin.replace(/^http/, 'ws')
    let connection: WebSocket
    try {
      connection = new WebSocket(`${websocketOrigin}/api/chats/${chatId}/ws?token=${encodeURIComponent(token)}`)
    } catch {
      setRealtime('offline')
      setRealtimeDetail('Could not create the live connection; retrying.')
      reconnectTimer.current = setTimeout(() => connectSocket(chatId, attempt + 1), Math.min(1000 * (attempt + 1), 10000))
      return
    }
    socket.current = connection
    connection.onopen = () => {
      if (socket.current !== connection) return
      setRealtime('connected')
      setRealtimeDetail('')
      setError('')
    }
    connection.onmessage = event => {
      if (socket.current !== connection) return
      const payload = JSON.parse(event.data) as { type: string; message?: ChatMessage; error?: string; is_typing?: boolean }
      if (payload.type === 'message' && payload.message) setMessages(current => current.some(message => message.id === payload.message?.id) ? current : [...current, payload.message as ChatMessage])
      if (payload.type === 'typing') setTyping(Boolean(payload.is_typing))
      if (payload.type === 'error' && typeof payload.error === 'string') setError(payload.error)
    }
    connection.onerror = () => {
      if (socket.current === connection) {
        setRealtime('offline')
        setRealtimeDetail('Live connection failed; retrying.')
      }
    }
    connection.onclose = event => {
      if (socket.current !== connection) return
      setRealtime('offline')
      const closeReason = event.reason ? `: ${event.reason}` : ''
      setRealtimeDetail(`Live connection closed (${event.code}${closeReason}); retrying.`)
      reconnectTimer.current = setTimeout(() => connectSocket(chatId, attempt + 1), Math.min(1000 * (attempt + 1), 10000))
    }
  }

  useEffect(() => () => {
    if (reconnectTimer.current) clearTimeout(reconnectTimer.current)
    if (copiedTimer.current) clearTimeout(copiedTimer.current)
    socket.current?.close()
    speechRecognition.current?.abort()
    window.speechSynthesis?.cancel()
  }, [])

  const speakMessage = (message: ChatMessage) => {
    if (!('speechSynthesis' in window)) {
      setError('Spoken replies are not supported in this browser. Try the latest Chrome or Edge.')
      return
    }
    if (speakingMessageId === message.id) {
      window.speechSynthesis.cancel()
      speechUtterance.current = null
      setSpeakingMessageId(null)
      return
    }

    const text = prepareTutorSpeech(message.content)
    if (!text) {
      setError('This tutor reply has no text to read aloud.')
      return
    }

    const synthesis = window.speechSynthesis
    synthesis.cancel()
    const utterance = new SpeechSynthesisUtterance(text)
    const language = /[\u0900-\u097f]/.test(text) ? 'hi-IN' : voiceLanguage
    utterance.lang = language
    const languagePrefix = language.slice(0, 2).toLowerCase()
    const voices = synthesis.getVoices()
    utterance.voice = voices.find(voice => voice.lang.toLowerCase() === language.toLowerCase())
      || voices.find(voice => voice.lang.slice(0, 2).toLowerCase() === languagePrefix)
      || null
    utterance.onend = () => {
      if (speechUtterance.current === utterance) {
        speechUtterance.current = null
        setSpeakingMessageId(null)
      }
    }
    utterance.onerror = event => {
      if (speechUtterance.current === utterance) {
        speechUtterance.current = null
        setSpeakingMessageId(null)
        if (event.error !== 'canceled' && event.error !== 'interrupted') {
          setError(event.error === 'voice-unavailable'
            ? `No ${language === 'hi-IN' ? 'Hindi' : 'English'} speech voice is available in your browser. Enable or install that language's speech voice in your device settings, then reload the app.`
            : event.error === 'not-allowed'
              ? 'The browser blocked speech playback. Click Listen on the tutor reply to start it.'
              : `Spoken reply failed (${event.error}). Check your browser audio output and try Listen again.`)
        }
      }
    }
    speechUtterance.current = utterance
    setError('')
    setSpeakingMessageId(message.id)
    try {
      synthesis.speak(utterance)
    } catch {
      speechUtterance.current = null
      setSpeakingMessageId(null)
      setError('The browser could not start spoken playback. Try the latest Chrome or Edge and check your audio output.')
    }
  }

  const toggleVoiceInput = () => {
    if (recording) {
      speechRecognition.current?.stop()
      setRecording(false)
      return
    }
    const speechWindow = window as SpeechRecognitionWindow
    const SpeechRecognitionApi = speechWindow.SpeechRecognition || speechWindow.webkitSpeechRecognition
    if (!SpeechRecognitionApi) {
      setError('Voice input is not supported in this browser. Try the latest Chrome or Edge.')
      return
    }
    const recognition = new SpeechRecognitionApi()
    recognition.lang = voiceLanguage
    recognition.interimResults = false
    recognition.maxAlternatives = 1
    recognition.onresult = event => {
      const transcript = event.results[0]?.[0]?.transcript?.trim()
      if (transcript) setDraft(current => current ? `${current} ${transcript}` : transcript)
    }
    recognition.onerror = event => {
      setRecording(false)
      setError(event.error === 'not-allowed' ? 'Allow microphone access in your browser to use voice input.' : `Voice input failed (${event.error}). Please try again.`)
    }
    recognition.onend = () => setRecording(false)
    speechRecognition.current = recognition
    setError('')
    try {
      recognition.start()
      setRecording(true)
    } catch {
      setRecording(false)
      setError('Could not start voice input. Check microphone access and try again.')
    }
  }

  useEffect(() => {
    if (!manageDialog) return
    if (manageDialog.type === 'rename') renameInput.current?.focus()
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && !dialogBusy) setManageDialog(null)
    }
    window.addEventListener('keydown', closeOnEscape)
    return () => window.removeEventListener('keydown', closeOnEscape)
  }, [manageDialog, dialogBusy])

  const copyMessage = async (message: ChatMessage) => {
    try {
      await navigator.clipboard.writeText(message.content)
      setCopiedMessageId(message.id)
      if (copiedTimer.current) clearTimeout(copiedTimer.current)
      copiedTimer.current = setTimeout(() => setCopiedMessageId(current => current === message.id ? null : current), 1800)
    } catch {
      setError('Unable to copy this response. Check your browser clipboard permissions and try again.')
    }
  }

  const toggleMessageFeedback = (messageId: string, feedback: 'like' | 'dislike') => {
    setMessageFeedback(current => {
      const next = { ...current }
      if (next[messageId] === feedback) delete next[messageId]
      else next[messageId] = feedback
      return next
    })
  }

  const openChat = async (chat: ChatSession) => {
    try { setMenuChatId(null); const detail = await api.chat(token, chat.id); setActive(detail); setMessages(detail.messages); setSelectedFiles([]); connectSocket(chat.id) } catch (cause) { setError(cause instanceof Error ? cause.message : 'Unable to open conversation.') }
  }
  const createChat = async () => {
    setError('')
    try { const chat = await api.createChat(token); setActive(chat); setMessages([]); setSelectedFiles([]); connectSocket(chat.id) } catch (cause) { setError(cause instanceof Error ? cause.message : 'Unable to create conversation.') }
  }
  const addSelectedFiles = (event: ChangeEvent<HTMLInputElement>) => {
    const incoming = Array.from(event.currentTarget.files || [])
    event.currentTarget.value = ''
    if (!incoming.length) return
    const combined = [...selectedFiles, ...incoming]
    const unsupported = combined.find(file => !getAttachmentMediaType(file))
    if (unsupported) { setError(`Unsupported file type: ${unsupported.name}. Choose an image or PDF.`); return }
    const tooLarge = combined.find(file => file.size > MAX_CHAT_FILE_BYTES)
    if (tooLarge) { setError(`${tooLarge.name} is larger than 4 MB.`); return }
    if (combined.length > MAX_CHAT_FILES) { setError('Attach no more than three files per message.'); return }
    if (combined.reduce((total, file) => total + file.size, 0) > MAX_CHAT_FILES_TOTAL_BYTES) {
      setError('Selected attachments must total 10 MB or less.')
      return
    }
    setError('')
    setSelectedFiles(combined)
  }
  const downloadAttachment = async (message: ChatMessage, attachment: ChatAttachment) => {
    if (!active) return
    try {
      const blob = await api.chatAttachment(token, active.id, message.id, attachment.id)
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = attachment.file_name
      link.click()
      window.setTimeout(() => URL.revokeObjectURL(url), 1000)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Unable to download this chat attachment.')
    }
  }
  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); if (!active || (!draft.trim() && selectedFiles.length === 0)) return
    setSending(true); setError('')
    try {
      const content = draft.trim() || (selectedFiles.length ? 'Please explain the attached file.' : '')
      const attachments = await Promise.all(selectedFiles.map(encodeChatAttachment))
      const completion = await api.completeMessage(token, active.id, content, oralExplanation, attachments)
      const updated = { ...active, title: completion.chat_title, updated_at: new Date().toISOString() }
      setActive(updated); setSessions(current => [updated, ...current.filter(chat => chat.id !== updated.id)]); setMessages(current => [...current, completion.user_message, completion.assistant_message]); setDraft(''); setSelectedFiles([])
      if (oralExplanation) speakMessage(completion.assistant_message)
    } catch (cause) {
      if (selectedFiles.length === 0 && cause instanceof ApiError && cause.status >= 500) {
        try {
          const message = await api.sendMessage(token, active.id, draft.trim()); const refreshed = await api.chats(token); const updated = refreshed.find(chat => chat.id === active.id) || active
          setActive(updated); setSessions(refreshed); setMessages(current => [...current, message]); setDraft(''); setError('AI tutor is unavailable. Your message was saved.')
        } catch (fallbackCause) { setError(fallbackCause instanceof Error ? fallbackCause.message : 'Unable to save message.') }
      } else { setError(cause instanceof Error ? cause.message : 'Unable to send message.') }
    } finally { if (socket.current?.readyState === WebSocket.OPEN) socket.current.send(JSON.stringify({ type: 'typing', is_typing: false })); setSending(false) }
  }
  const rename = (chat: ChatSession) => {
    setMenuChatId(null)
    setRenameTitle(chat.title)
    setDialogError('')
    setManageDialog({ type: 'rename', chat })
  }
  const saveRename = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!manageDialog || manageDialog.type !== 'rename') return
    const title = renameTitle.trim()
    if (!title || title === manageDialog.chat.title) { setManageDialog(null); return }
    setDialogBusy(true)
    setDialogError('')
    try {
      const updated = await api.renameChat(token, manageDialog.chat.id, title)
      setActive(current => current?.id === updated.id ? updated : current)
      setSessions(current => current.map(item => item.id === updated.id ? updated : item))
      setManageDialog(null)
    } catch (cause) {
      setDialogError(cause instanceof Error ? cause.message : 'Unable to rename conversation.')
    } finally {
      setDialogBusy(false)
    }
  }
  const remove = (chat: ChatSession) => {
    setMenuChatId(null)
    setDialogError('')
    setManageDialog({ type: 'delete', chat })
  }
  const confirmRemove = async () => {
    if (!manageDialog || manageDialog.type !== 'delete') return
    const chat = manageDialog.chat
    setDialogBusy(true)
    setDialogError('')
    try {
      await api.deleteChat(token, chat.id); const remaining = sessions.filter(item => item.id !== chat.id); setSessions(remaining)
      setManageDialog(null)
      if (active?.id === chat.id) { setActive(null); setMessages([]); if (remaining[0]) await openChat(remaining[0]) }
    } catch (cause) {
      setDialogError(cause instanceof Error ? cause.message : 'Unable to delete conversation.')
    } finally {
      setDialogBusy(false)
    }
  }

  return (
    <div className="chat-overlay">
      <section className="chat-panel">
        <aside className="chat-list">
          <header><div><span className="eyebrow">PHASE 6 CHAT</span><h2>Conversations</h2></div><button onClick={close} title="Close chat"><X /></button></header>
          <button className="chat-new" onClick={() => void createChat()}><Plus /> New conversation</button>
          {busy ? <Loader2 className="spin chat-loader" /> : sessions.length === 0 ? <p className="muted">No conversations yet.</p> : sessions.map(chat => <div className="chat-item-row" key={chat.id}><button className={active?.id === chat.id ? 'chat-item active' : 'chat-item'} onClick={() => void openChat(chat)}><MessageSquare /><span>{chat.title}</span></button><button className="chat-item-menu" onClick={() => setMenuChatId(menuChatId === chat.id ? null : chat.id)} title="Conversation actions"><MoreHorizontal /></button>{menuChatId === chat.id && <div className="chat-item-menu-panel"><button onClick={() => rename(chat)}><Pencil /> Rename</button><button onClick={() => remove(chat)}><Trash2 /> Delete</button></div>}</div>)}
        </aside>
        <section className="chat-main">
          <header><div><b>{active?.title || 'New conversation'}</b><small>{realtime === 'connected' ? 'Live connection' : realtime === 'connecting' ? realtimeDetail || 'Connecting...' : `Offline - REST fallback${realtimeDetail ? ` · ${realtimeDetail}` : ''}`}</small></div><div className="chat-actions"><button onClick={close} title="Close chat"><X /></button></div></header>
          <div className="chat-messages">
            {error && <p className="error">{error}</p>}
            {!active ? <div className="chat-empty"><MessageSquare /><h3>Start a conversation</h3><p>Create a chat and write what you want to learn.</p><button onClick={() => void createChat()}>New conversation <Plus /></button></div> : messages.length === 0 ? <div className="chat-empty"><MessageSquare /><h3>Your learning space is ready</h3><p>Send your first question. Messages will be stored securely.</p></div> : messages.map(message => {
              const diagramSource = message.role === 'assistant' ? getMermaidSource(message.content) : null
              const messageContent = diagramSource ? removeMermaidSource(message.content) : message.content
              const documentLinks = message.role === 'assistant' ? (message.sources || []).filter(isDirectDocumentLink) : []
              const showDocumentSection = documentLinks.length > 0 || (message.role === 'assistant' && isTopicExplanation(messageContent))
              return (
                <article className={message.role === 'user' ? 'chat-message user' : 'chat-message'} key={message.id}>
                  <small>{message.role === 'user' ? 'You' : 'NDA Chatbot'}</small>
                  {messageContent && (message.role === 'assistant'
                    ? <div className="chat-markdown"><TutorMarkdown content={messageContent} /></div>
                    : <p>{messageContent}</p>)}
                  {message.role === 'user' && message.attachments?.length > 0 && <div className="chat-message-attachments">
                    {message.attachments.map(attachment => <button type="button" key={attachment.id} onClick={() => void downloadAttachment(message, attachment)} title={`Download ${attachment.file_name}`}>
                      {attachment.media_type.startsWith('image/') ? <Image /> : <FileText />}
                      <span>{attachment.file_name}</span>
                      <Download />
                    </button>)}
                  </div>}
                  {diagramSource && <MermaidDiagram source={diagramSource} />}
                  {showDocumentSection && <nav className="chat-document-links" aria-label="Verified topic documents">
                    <span className="chat-document-heading"><FileText /> Topic documents</span>
                    {documentLinks.length > 0 ? documentLinks.map(source => <a href={source.url} key={source.document_id} target="_blank" rel="noopener noreferrer"><span>{source.title}{source.page_reference ? ` · ${source.page_reference}` : ''}</span><ExternalLink /></a>) : <small>No verified document link is available for this topic yet.</small>}
                  </nav>}
                  {message.role === 'assistant' && <div className="chat-message-actions" aria-label="Response actions">
                    <button type="button" onClick={() => void copyMessage(message)} title="Copy response" aria-label="Copy response">
                      {copiedMessageId === message.id ? <Check /> : <Copy />}
                      <span>{copiedMessageId === message.id ? 'Copied' : 'Copy'}</span>
                    </button>
                    <button type="button" onClick={() => speakMessage(message)} title={speakingMessageId === message.id ? 'Stop spoken reply' : 'Read reply aloud'} aria-label={speakingMessageId === message.id ? 'Stop spoken reply' : 'Read reply aloud'} aria-pressed={speakingMessageId === message.id}>
                      {speakingMessageId === message.id ? <VolumeX /> : <Volume2 />}
                      <span>{speakingMessageId === message.id ? 'Stop' : 'Listen'}</span>
                    </button>
                    <button type="button" className={messageFeedback[message.id] === 'like' ? 'selected' : ''} onClick={() => toggleMessageFeedback(message.id, 'like')} title="Like response" aria-label="Like response" aria-pressed={messageFeedback[message.id] === 'like'}>
                      <ThumbsUp />
                    </button>
                    <button type="button" className={messageFeedback[message.id] === 'dislike' ? 'selected' : ''} onClick={() => toggleMessageFeedback(message.id, 'dislike')} title="Dislike response" aria-label="Dislike response" aria-pressed={messageFeedback[message.id] === 'dislike'}>
                      <ThumbsDown />
                    </button>
                  </div>}
                </article>
              )
            })}
          </div>
          {typing && <p className="chat-typing">A participant is typing...</p>}
          {selectedFiles.length > 0 && <div className="chat-selected-attachments" aria-label="Attachments to send">
            {selectedFiles.map((file, index) => <span className="chat-attachment-chip" key={`${file.name}-${index}`}>
              {getAttachmentMediaType(file)?.startsWith('image/') ? <Image /> : <FileText />}
              <span>{file.name}</span>
              <button type="button" onClick={() => setSelectedFiles(current => current.filter((_, itemIndex) => itemIndex !== index))} aria-label={`Remove ${file.name}`} title={`Remove ${file.name}`}><X /></button>
            </span>)}
          </div>}
          <form className="chat-composer" onSubmit={submit}>
            <input value={draft} onChange={event => { setDraft(event.target.value); if (socket.current?.readyState === WebSocket.OPEN) socket.current.send(JSON.stringify({ type: 'typing', is_typing: Boolean(event.target.value) })) }} placeholder={active ? 'Write or dictate your question...' : 'Create a conversation first'} disabled={!active || sending} maxLength={10000} />
            <label className="chat-attach-button" title="Attach images or PDFs">
              <input ref={attachmentInput} type="file" aria-label="Attach images or PDFs" accept="image/jpeg,image/png,image/webp,application/pdf,.jpg,.jpeg,.png,.webp,.pdf" multiple onChange={addSelectedFiles} disabled={!active || sending} />
              <Paperclip />
            </label>
            <select aria-label="Voice language" value={voiceLanguage} onChange={event => setVoiceLanguage(event.target.value as 'en-IN' | 'hi-IN')} disabled={recording}>
              <option value="en-IN">English</option><option value="hi-IN">हिन्दी</option>
            </select>
            <button type="button" className={`oral-explanation-toggle${oralExplanation ? ' oral-mode' : ''}`} onClick={() => setOralExplanation(value => !value)} disabled={!active || sending} title={oralExplanation ? 'Turn off oral explanations' : 'Request oral explanations'} aria-label={oralExplanation ? 'Turn off oral explanations' : 'Request oral explanations'} aria-pressed={oralExplanation}>
              <Headphones /><span>Oral</span>
            </button>
            <button type="button" className={recording ? 'voice-recording' : ''} onClick={toggleVoiceInput} disabled={!active || sending} title={recording ? 'Stop voice input' : 'Speak your question'} aria-label={recording ? 'Stop voice input' : 'Speak your question'} aria-pressed={recording}>
              {recording ? <MicOff /> : <Mic />}
            </button>
            <button type="submit" disabled={!active || (!draft.trim() && selectedFiles.length === 0) || sending} title="Send message">{sending ? <Loader2 className="spin" /> : <Send />}</button>
          </form>
          <p className="chat-notice">{recording ? 'Listening… your speech will be transcribed into the message box.' : 'Attach up to 3 images or PDFs (4 MB each; 10 MB total). '}{oralExplanation && 'Oral explanation is on; replies will also be spoken aloud.'}</p>
        </section>
      </section>
      {manageDialog && <div className="chat-manage-backdrop" role="presentation" onMouseDown={event => { if (event.target === event.currentTarget && !dialogBusy) setManageDialog(null) }}>
        <section className="chat-manage-dialog" role={manageDialog.type === 'delete' ? 'alertdialog' : 'dialog'} aria-modal="true" aria-labelledby="chat-manage-title" aria-describedby="chat-manage-description">
          <span className={manageDialog.type === 'delete' ? 'chat-manage-icon danger' : 'chat-manage-icon'}>{manageDialog.type === 'delete' ? <Trash2 /> : <Pencil />}</span>
          <h3 id="chat-manage-title">{manageDialog.type === 'delete' ? 'Delete conversation?' : 'Rename conversation'}</h3>
          <p id="chat-manage-description">{manageDialog.type === 'delete' ? `“${manageDialog.chat.title}” and its messages will be permanently deleted.` : 'Choose a name that helps you find this conversation later.'}</p>
          {manageDialog.type === 'rename' && <form onSubmit={event => void saveRename(event)}>
            <label htmlFor="chat-rename-title">Conversation name</label>
            <input ref={renameInput} id="chat-rename-title" value={renameTitle} onChange={event => setRenameTitle(event.target.value)} maxLength={120} required autoComplete="off" />
            {dialogError && <p className="chat-manage-error" role="alert">{dialogError}</p>}
            <div className="chat-manage-actions">
              <button type="button" className="chat-manage-cancel" onClick={() => setManageDialog(null)} disabled={dialogBusy}>Cancel</button>
              <button type="submit" className="chat-manage-confirm" disabled={dialogBusy || !renameTitle.trim()}>{dialogBusy ? <><Loader2 className="spin" /> Saving...</> : 'Save name'}</button>
            </div>
          </form>}
          {manageDialog.type === 'delete' && <>
            {dialogError && <p className="chat-manage-error" role="alert">{dialogError}</p>}
            <div className="chat-manage-actions">
              <button type="button" className="chat-manage-cancel" onClick={() => setManageDialog(null)} disabled={dialogBusy}>Cancel</button>
              <button type="button" className="chat-manage-confirm danger" onClick={() => void confirmRemove()} disabled={dialogBusy}>{dialogBusy ? <><Loader2 className="spin" /> Deleting...</> : 'Delete conversation'}</button>
            </div>
          </>}
        </section>
      </div>}
    </div>
  )
}
