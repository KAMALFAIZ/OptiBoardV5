import { useState, useEffect, useCallback, useMemo, createContext, useContext } from 'react'
import { CheckCircle2, AlertCircle, Info, X } from 'lucide-react'

const ToastContext = createContext(null)

const ICONS = {
  success: CheckCircle2,
  error: AlertCircle,
  info: Info,
  warning: AlertCircle,
}

const STYLES = {
  success: 'bg-emerald-50 dark:bg-emerald-900/30 border-emerald-300 dark:border-emerald-700 text-emerald-800 dark:text-emerald-200',
  error: 'bg-red-50 dark:bg-red-900/30 border-red-300 dark:border-red-700 text-red-800 dark:text-red-200',
  info: 'bg-blue-50 dark:bg-blue-900/30 border-blue-300 dark:border-blue-700 text-blue-800 dark:text-blue-200',
  warning: 'bg-amber-50 dark:bg-amber-900/30 border-amber-300 dark:border-amber-700 text-amber-800 dark:text-amber-200',
}

const ICON_STYLES = {
  success: 'text-emerald-500',
  error: 'text-red-500',
  info: 'text-blue-500',
  warning: 'text-amber-500',
}

let _toastId = 0

function ToastItem({ toast, onRemove }) {
  const [exiting, setExiting] = useState(false)
  const Icon = ICONS[toast.type] || Info

  useEffect(() => {
    const timer = setTimeout(() => {
      setExiting(true)
      setTimeout(() => onRemove(toast.id), 300)
    }, toast.duration || 3500)
    return () => clearTimeout(timer)
  }, [toast, onRemove])

  return (
    <div className={`flex items-start gap-2.5 px-4 py-3 rounded-xl border shadow-lg max-w-sm transition-all duration-300 ${STYLES[toast.type]}
      ${exiting ? 'opacity-0 translate-x-8' : 'opacity-100 translate-x-0'}`}>
      <Icon size={18} className={`flex-shrink-0 mt-0.5 ${ICON_STYLES[toast.type]}`} />
      <div className="flex-1 min-w-0">
        {toast.title && <p className="text-sm font-semibold">{toast.title}</p>}
        <p className="text-sm whitespace-pre-line">{toast.message}</p>
      </div>
      <button onClick={() => { setExiting(true); setTimeout(() => onRemove(toast.id), 300) }}
        className="flex-shrink-0 opacity-60 hover:opacity-100 transition-opacity">
        <X size={14} />
      </button>
    </div>
  )
}

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([])

  const addToast = useCallback((type, message, options = {}) => {
    const id = ++_toastId
    setToasts(prev => [...prev, { id, type, message, ...options }])
    return id
  }, [])

  const removeToast = useCallback((id) => {
    setToasts(prev => prev.filter(t => t.id !== id))
  }, [])

  const toast = useMemo(() => ({
    success: (msg, opts) => addToast('success', msg, opts),
    error: (msg, opts) => addToast('error', msg, opts),
    info: (msg, opts) => addToast('info', msg, opts),
    warning: (msg, opts) => addToast('warning', msg, opts),
  }), [addToast])

  return (
    <ToastContext.Provider value={toast}>
      {children}
      <div className="fixed top-4 right-4 z-[9999] flex flex-col gap-2">
        {toasts.map(t => (
          <ToastItem key={t.id} toast={t} onRemove={removeToast} />
        ))}
      </div>
    </ToastContext.Provider>
  )
}

export function useToast() {
  const ctx = useContext(ToastContext)
  if (!ctx) {
    return {
      success: (msg) => console.log('[toast:success]', msg),
      error: (msg) => console.error('[toast:error]', msg),
      info: (msg) => console.log('[toast:info]', msg),
      warning: (msg) => console.warn('[toast:warning]', msg),
    }
  }
  return ctx
}
