import { createContext, useContext, useState, useCallback, useRef } from 'react'
import api from '../services/api'

const ChatContext = createContext(null)

const getDWHHeaders = () => {
  const headers = {}
  try {
    const savedDWH = localStorage.getItem('currentDWH')
    if (savedDWH) {
      const parsedDWH = JSON.parse(savedDWH)
      if (parsedDWH?.code) headers['X-DWH-Code'] = parsedDWH.code
    }
  } catch (e) { /* ignore */ }
  return headers
}

const getUserHeader = () => {
  try {
    const user = JSON.parse(localStorage.getItem('user') || '{}')
    return user.id ? { 'X-User-Id': String(user.id) } : {}
  } catch { return {} }
}

export function ChatProvider({ children }) {
  const [isOpen, setIsOpen] = useState(false)
  const [isFullPage, setIsFullPage] = useState(false)
  const [messages, setMessages] = useState([])
  const [sessionId, setSessionId] = useState(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState(null)
  const [mode, setMode] = useState('chat')
  const [aiStatus, setAiStatus] = useState(null)
  // Sélection DWH en attente (quand le backend détecte plusieurs DWH disponibles)
  const [pendingDwhSelection, setPendingDwhSelection] = useState(null) // { dwh_list, pendingMessage, pendingMode }
  const pendingDwhRef = useRef(null) // ref pour accès dans useCallback
  const abortControllerRef = useRef(null) // pour annuler le streaming en cours

  const loadAiStatus = useCallback(async () => {
    try {
      const res = await api.get('/ai/status')
      setAiStatus(res.data)
    } catch (e) {
      setAiStatus({ enabled: false, configured: false, provider: '', model: '' })
    }
  }, [])

  // Arrêter le streaming en cours
  const stopStreaming = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
      abortControllerRef.current = null
    }
  }, [])

  const sendMessage = useCallback(async (content, currentMode) => {
    const useMode = currentMode || mode
    if (!content.trim() || isLoading) return

    const userMsg = {
      id: Date.now(),
      role: 'user',
      content,
      timestamp: new Date().toISOString()
    }
    setMessages(prev => [...prev, userMsg])
    setIsLoading(true)
    setError(null)

    try {
      const headers = { ...getDWHHeaders(), ...getUserHeader() }
      const res = await api.post('/ai/chat', {
        message: content,
        session_id: sessionId,
        mode: useMode,
        context: _getGlobalContext()
      }, { headers })

      const data = res.data
      if (data.session_id && !sessionId) setSessionId(data.session_id)

      const assistantMsg = {
        id: Date.now() + 1,
        role: 'assistant',
        content: data.response,
        timestamp: new Date().toISOString(),
        sqlQuery: data.sql_query,
        sqlResults: data.sql_results,
        sqlColumns: data.sql_columns,
        provider: data.provider
      }
      setMessages(prev => [...prev, assistantMsg])
    } catch (err) {
      setError(err.response?.data?.detail || "Erreur de communication avec l'IA")
    } finally {
      setIsLoading(false)
    }
  }, [isLoading, mode, sessionId])

  const sendMessageStream = useCallback(async (content, currentMode) => {
    const useMode = currentMode || mode
    if (!content.trim() || isLoading) return

    const userMsg = {
      id: Date.now(),
      role: 'user',
      content,
      timestamp: new Date().toISOString()
    }
    setMessages(prev => [...prev, userMsg])
    setIsLoading(true)
    setError(null)

    const assistantMsgId = Date.now() + 1
    setMessages(prev => [...prev, {
      id: assistantMsgId,
      role: 'assistant',
      content: '',
      timestamp: new Date().toISOString(),
      streaming: true
    }])

    // Créer un AbortController pour pouvoir arrêter le streaming
    const controller = new AbortController()
    abortControllerRef.current = controller

    try {
      const headers = {
        ...getDWHHeaders(),
        ...getUserHeader(),
        'Content-Type': 'application/json',
        'Accept': 'text/event-stream'
      }
      const response = await fetch('/api/ai/chat/stream', {
        method: 'POST',
        headers,
        signal: controller.signal,
        body: JSON.stringify({
          message: content,
          session_id: sessionId,
          mode: useMode,
          context: _getGlobalContext()
        })
      })

      if (!response.ok) {
        // Tenter de lire le message d'erreur du serveur
        let errorMsg = `Erreur HTTP ${response.status}`
        try {
          const contentType = response.headers.get('content-type') || ''
          if (contentType.includes('application/json')) {
            const errData = await response.json()
            errorMsg = errData.detail || errData.error || errorMsg
          } else {
            const text = await response.text()
            if (text) errorMsg = text.substring(0, 200)
          }
        } catch { /* ignore */ }
        throw new Error(errorMsg)
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let hasReceivedTokens = false

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6))

              // Sélection DWH requise (plusieurs DWH disponibles)
              if (data.dwh_selection_required) {
                // Supprimer le message assistant vide et le message utilisateur
                setMessages(prev => prev.filter(m => m.id !== assistantMsgId))
                const pending = {
                  dwh_list: data.dwh_list,
                  pendingMessage: content,
                  pendingMode: useMode
                }
                setPendingDwhSelection(pending)
                pendingDwhRef.current = pending
                setIsLoading(false)
                return
              }

              if (data.token) {
                hasReceivedTokens = true
                setMessages(prev => prev.map(m =>
                  m.id === assistantMsgId
                    ? { ...m, content: m.content + data.token }
                    : m
                ))
              }
              if (data.done) {
                if (data.session_id) setSessionId(data.session_id)
                setMessages(prev => prev.map(m =>
                  m.id === assistantMsgId
                    ? {
                        ...m,
                        streaming: false,
                        sqlQuery: data.sql_query || null,
                        sqlResults: data.sql_results || null,
                        sqlColumns: data.sql_columns || null,
                        sqlError: data.sql_error || null,
                        sqlExecutionTime: data.sql_execution_time_ms || null
                      }
                    : m
                ))
              }
              if (data.error) {
                setError(data.error)
                // Supprimer le message assistant vide si aucun token recu
                if (!hasReceivedTokens) {
                  setMessages(prev => prev.filter(m => m.id !== assistantMsgId))
                }
              }
            } catch { /* ignore malformed SSE */ }
          }
        }
      }
    } catch (err) {
      // Si annulé volontairement → garder le contenu partiel, ne pas montrer d'erreur
      if (err.name === 'AbortError') {
        setMessages(prev => prev.map(m =>
          m.id === assistantMsgId
            ? { ...m, streaming: false, aborted: true }
            : m
        ))
      } else {
        const errorMsg = err.message || "Erreur de streaming. Veuillez reessayer."
        setError(errorMsg)
        setMessages(prev => prev.filter(m => m.id !== assistantMsgId))
      }
    } finally {
      abortControllerRef.current = null
      setIsLoading(false)
    }
  }, [isLoading, mode, sessionId])

  // Sélectionner un DWH et renvoyer le message en attente
  const selectDwhAndResend = useCallback((dwhCode, dwhNom) => {
    // Mettre à jour le DWH courant dans localStorage
    localStorage.setItem('currentDWH', JSON.stringify({ code: dwhCode, nom: dwhNom }))
    const pending = pendingDwhRef.current
    setPendingDwhSelection(null)
    pendingDwhRef.current = null
    if (pending?.pendingMessage) {
      // Relancer le message avec le nouveau DWH
      sendMessageStream(pending.pendingMessage, pending.pendingMode)
    }
  }, [sendMessageStream])

  const clearConversation = useCallback(async () => {
    // Arrêter le streaming en cours si actif
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
      abortControllerRef.current = null
    }
    if (sessionId) {
      try {
        await api.delete(`/ai/session/${sessionId}`)
      } catch { /* ignore */ }
    }
    setMessages([])
    setSessionId(null)
    setError(null)
    setPendingDwhSelection(null)
    pendingDwhRef.current = null
  }, [sessionId])

  const submitFeedback = useCallback(async (questionText, sqlQuery, rating) => {
    try {
      const headers = { ...getDWHHeaders(), ...getUserHeader(), 'Content-Type': 'application/json' }
      const dwh = (() => { try { return JSON.parse(localStorage.getItem('currentDWH') || '{}') } catch { return {} } })()
      await fetch('/api/ai/learning/feedback', {
        method: 'POST',
        headers,
        body: JSON.stringify({
          question_text: questionText,
          sql_query: sqlQuery,
          rating,
          dwh_code: dwh.code || null
        })
      })
    } catch (e) {
      console.warn('Feedback submission failed:', e)
    }
  }, [])

  const openWidget = () => { setIsOpen(true); setIsFullPage(false) }
  const closeWidget = () => setIsOpen(false)
  const openFullPage = () => { setIsFullPage(true); setIsOpen(false) }
  const closeFullPage = () => { setIsFullPage(false) }

  return (
    <ChatContext.Provider value={{
      isOpen, isFullPage,
      messages, sessionId,
      isLoading, error, mode,
      aiStatus,
      pendingDwhSelection,
      setMode,
      sendMessage,
      sendMessageStream,
      stopStreaming, submitFeedback,
      selectDwhAndResend,
      clearConversation,
      openWidget, closeWidget,
      openFullPage, closeFullPage,
      loadAiStatus
    }}>
      {children}
    </ChatContext.Provider>
  )
}

export function useChat() {
  const context = useContext(ChatContext)
  if (!context) throw new Error('useChat must be used within a ChatProvider')
  return context
}

function _getGlobalContext() {
  try {
    const filters = JSON.parse(localStorage.getItem('reporting_global_filters') || '{}')
    const dwh = JSON.parse(localStorage.getItem('currentDWH') || '{}')
    return { ...filters, dwh_code: dwh.code }
  } catch { return {} }
}
