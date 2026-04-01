import { useState, useRef, useEffect, useCallback } from 'react'
import { Send, Bot, User, Trash2, MessageSquare } from 'lucide-react'
import { useAuth } from '../../context/AuthContext'
import { useDWH } from '../../context/DWHContext'

const HISTORY_KEY = (uid) => `chat_history_${uid}`
const SESSION_KEY  = (uid) => `chat_session_${uid}`

const SUGGESTIONS = [
  "Quel est mon chiffre d'affaires du mois ?",
  "Quels sont mes meilleurs clients ?",
  "Montre-moi les ventes par commercial",
  "Quelle est l'évolution de mes ventes ?",
]

// ─── Markdown lite ─────────────────────────────────────────────────────────────
function renderMd(text) {
  return text
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/`([^`\n]+)`/g, '<code style="background:rgba(0,0,0,.08);padding:1px 4px;border-radius:4px;font-size:.8em">$1</code>')
    .replace(/\n/g, '<br/>')
}

// ─── Table SQL ─────────────────────────────────────────────────────────────────
function SQLTable({ columns, rows }) {
  if (!rows?.length || !columns?.length) return null
  const display = rows.slice(0, 15)
  return (
    <div className="mt-2 overflow-x-auto rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm">
      <table className="text-xs min-w-full">
        <thead className="bg-gray-50 dark:bg-gray-800/80">
          <tr>
            {columns.map(col => (
              <th key={col} className="px-2.5 py-1.5 text-left font-semibold text-gray-600 dark:text-gray-400 whitespace-nowrap">
                {col}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100 dark:divide-gray-700/50">
          {display.map((row, i) => (
            <tr key={i} className={i % 2 === 0 ? 'bg-white dark:bg-gray-900' : 'bg-gray-50/50 dark:bg-gray-800/30'}>
              {columns.map(col => (
                <td key={col} className="px-2.5 py-1.5 text-gray-700 dark:text-gray-300 whitespace-nowrap">
                  {row[col] ?? '—'}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {rows.length > 15 && (
        <div className="px-3 py-1.5 bg-gray-50 dark:bg-gray-800/50 text-center text-[10px] text-gray-400 border-t border-gray-100 dark:border-gray-700">
          +{rows.length - 15} lignes supplémentaires
        </div>
      )}
    </div>
  )
}

// ─── Bulle de message ──────────────────────────────────────────────────────────
function Message({ msg }) {
  const isUser = msg.role === 'user'
  return (
    <div className={`flex gap-2.5 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
      {/* Avatar */}
      <div className={`w-7 h-7 rounded-full flex-shrink-0 flex items-center justify-center mt-0.5 ${
        isUser
          ? 'bg-primary-500'
          : 'bg-gray-200 dark:bg-gray-700'
      }`}>
        {isUser
          ? <User className="w-3.5 h-3.5 text-white" />
          : <Bot className="w-3.5 h-3.5 text-gray-600 dark:text-gray-300" />}
      </div>

      {/* Contenu */}
      <div className={`max-w-[80%] flex flex-col gap-1 ${isUser ? 'items-end' : 'items-start'}`}>
        <div className={`rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
          isUser
            ? 'bg-primary-500 text-white rounded-tr-sm'
            : 'bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-200 border border-gray-100 dark:border-gray-700/80 rounded-tl-sm shadow-sm'
        }`}>
          {isUser
            ? msg.content
            : <span dangerouslySetInnerHTML={{ __html: renderMd(msg.content || '\u00a0') }} />}

          {/* Indicateur typing */}
          {msg.streaming && !msg.content && (
            <span className="inline-flex gap-1 items-center h-4">
              {[0, 150, 300].map(d => (
                <span key={d} className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce"
                  style={{ animationDelay: `${d}ms` }} />
              ))}
            </span>
          )}
        </div>

        {/* Résultats SQL */}
        {msg.sql_columns && msg.sql_results && (
          <SQLTable columns={msg.sql_columns} rows={msg.sql_results} />
        )}
        {msg.sql_error && (
          <p className="text-xs text-red-500 dark:text-red-400 px-1">{msg.sql_error}</p>
        )}
      </div>
    </div>
  )
}

// ─── Page principale ───────────────────────────────────────────────────────────
export default function MobileChatPage() {
  const { user } = useAuth()
  const { currentDWH } = useDWH()

  const [messages, setMessages] = useState(() => {
    try { return JSON.parse(localStorage.getItem(HISTORY_KEY(user?.id))) || [] } catch { return [] }
  })
  const [input,     setInput]     = useState('')
  const [loading,   setLoading]   = useState(false)
  const [sessionId, setSessionId] = useState(() => localStorage.getItem(SESSION_KEY(user?.id)) || null)
  const [mode,      setMode]      = useState('chat')  // 'chat' | 'sql'

  const bottomRef  = useRef(null)
  const inputRef   = useRef(null)
  const abortRef   = useRef(null)
  const textareaRef = useRef(null)

  // Persist history (keep last 60 messages)
  useEffect(() => {
    if (user?.id) localStorage.setItem(HISTORY_KEY(user.id), JSON.stringify(messages.slice(-60)))
  }, [messages, user?.id])

  // Persist session
  useEffect(() => {
    if (sessionId && user?.id) localStorage.setItem(SESSION_KEY(user.id), sessionId)
  }, [sessionId, user?.id])

  // Auto-scroll
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Auto-resize textarea
  const autoResize = useCallback(() => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = Math.min(el.scrollHeight, 120) + 'px'
  }, [])

  const clearHistory = useCallback(() => {
    setMessages([])
    setSessionId(null)
    if (user?.id) {
      localStorage.removeItem(HISTORY_KEY(user.id))
      localStorage.removeItem(SESSION_KEY(user.id))
    }
  }, [user?.id])

  const sendMessage = useCallback(async (text) => {
    const msg = (text ?? input).trim()
    if (!msg || loading) return
    setInput('')
    if (textareaRef.current) { textareaRef.current.style.height = 'auto' }
    setLoading(true)

    const userMsgId      = Date.now()
    const assistantMsgId = userMsgId + 1

    setMessages(prev => [
      ...prev,
      { id: userMsgId,      role: 'user',      content: msg },
      { id: assistantMsgId, role: 'assistant', content: '', streaming: true },
    ])

    abortRef.current = new AbortController()

    try {
      const token  = localStorage.getItem('token') || sessionStorage.getItem('token') || ''
      const dwhRaw = localStorage.getItem('currentDWH')
      const dwhCode = currentDWH?.code || (dwhRaw ? JSON.parse(dwhRaw)?.code : '') || ''

      const res = await fetch('/api/ai/chat/stream', {
        method: 'POST',
        headers: {
          'Content-Type':  'application/json',
          'Authorization': `Bearer ${token}`,
          'X-DWH-Code':   dwhCode,
          'X-User-Id':    String(user?.id || ''),
        },
        body: JSON.stringify({ message: msg, session_id: sessionId, mode }),
        signal: abortRef.current.signal,
      })

      if (!res.ok) throw new Error(`Erreur ${res.status}`)

      const reader  = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer    = ''
      let fullText  = ''
      let sqlData   = {}
      let newSid    = sessionId

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          try {
            const data = JSON.parse(line.slice(6))

            if (data.token) {
              fullText += data.token
              setMessages(prev => prev.map(m =>
                m.id === assistantMsgId ? { ...m, content: fullText } : m
              ))
            } else if (data.done) {
              newSid = data.session_id || newSid
              if (data.sql_query) {
                sqlData = {
                  sql_query:   data.sql_query,
                  sql_results: data.sql_results,
                  sql_columns: data.sql_columns,
                  sql_error:   data.sql_error,
                }
              }
            } else if (data.error) {
              fullText += (fullText ? '\n\n' : '') + `⚠️ ${data.error}`
              setMessages(prev => prev.map(m =>
                m.id === assistantMsgId ? { ...m, content: fullText } : m
              ))
            }
          } catch { /* JSON parse error — ignore */ }
        }
      }

      setSessionId(newSid)
      setMessages(prev => prev.map(m =>
        m.id === assistantMsgId ? { ...m, streaming: false, ...sqlData } : m
      ))
    } catch (err) {
      if (err.name === 'AbortError') return
      setMessages(prev => prev.map(m =>
        m.id === assistantMsgId
          ? { ...m, content: 'Impossible de joindre l\'assistant. Vérifiez que le module IA est configuré.', streaming: false }
          : m
      ))
    } finally {
      setLoading(false)
      inputRef.current?.focus()
    }
  }, [loading, sessionId, mode, currentDWH, user?.id, input])

  const isEmpty = messages.length === 0

  return (
    <div className="flex flex-col h-full bg-gray-50 dark:bg-gray-900">

      {/* ── Toolbar mode ───────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between px-4 py-2 bg-white dark:bg-gray-800 border-b border-gray-100 dark:border-gray-700">
        <div className="flex gap-1">
          {[['chat', 'Discussion'], ['sql', 'SQL']].map(([m, label]) => (
            <button key={m} onClick={() => setMode(m)}
              className={`px-3 py-1 rounded-full text-xs font-semibold transition-colors ${
                mode === m
                  ? 'bg-primary-100 dark:bg-primary-900/40 text-primary-700 dark:text-primary-300'
                  : 'text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700'
              }`}
            >
              {label}
            </button>
          ))}
        </div>
        <button
          onClick={clearHistory}
          disabled={isEmpty}
          className="p-1.5 rounded-lg text-gray-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 disabled:opacity-30 transition-colors"
          title="Effacer la conversation"
        >
          <Trash2 className="w-4 h-4" />
        </button>
      </div>

      {/* ── Messages ───────────────────────────────────────────────────────── */}
      <div className="flex-1 overflow-y-auto px-4 py-4">
        {isEmpty ? (
          <div className="flex flex-col items-center justify-center h-full gap-5 text-center py-8">
            <div className="w-16 h-16 rounded-2xl flex items-center justify-center shadow-sm"
              style={{ backgroundColor: 'var(--color-primary-100)' }}>
              <MessageSquare className="w-8 h-8" style={{ color: 'var(--color-primary-500)' }} />
            </div>
            <div>
              <p className="text-base font-bold text-gray-800 dark:text-gray-200">Assistant IA</p>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 max-w-[220px]">
                Posez vos questions sur vos données commerciales
              </p>
            </div>
            <div className="w-full space-y-2 max-w-sm">
              {SUGGESTIONS.map(s => (
                <button key={s} onClick={() => sendMessage(s)}
                  className="w-full text-left px-4 py-2.5 rounded-xl bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 text-sm text-gray-700 dark:text-gray-300 hover:border-primary-300 dark:hover:border-primary-600 hover:bg-primary-50 dark:hover:bg-primary-900/20 transition-colors"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            {messages.map(msg => <Message key={msg.id} msg={msg} />)}
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* ── Zone de saisie ─────────────────────────────────────────────────── */}
      <div ref={inputRef} className="px-4 py-3 bg-white dark:bg-gray-800 border-t border-gray-100 dark:border-gray-700">
        <div className="flex items-end gap-2">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={e => { setInput(e.target.value); autoResize() }}
            onKeyDown={e => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                sendMessage(input)
              }
            }}
            placeholder="Posez votre question…"
            rows={1}
            className="flex-1 resize-none rounded-2xl border border-gray-200 dark:border-gray-600 bg-gray-50 dark:bg-gray-900 px-4 py-2.5 text-sm text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:border-transparent transition-all"
            style={{ minHeight: '42px', maxHeight: '120px', '--tw-ring-color': 'var(--color-primary-500)' }}
          />
          <button
            onClick={() => sendMessage(input)}
            disabled={!input.trim() || loading}
            className="flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center text-white transition-all disabled:opacity-40 active:scale-95"
            style={{ backgroundColor: 'var(--color-primary-600)' }}
          >
            {loading
              ? <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              : <Send className="w-4 h-4" />}
          </button>
        </div>
      </div>
    </div>
  )
}
