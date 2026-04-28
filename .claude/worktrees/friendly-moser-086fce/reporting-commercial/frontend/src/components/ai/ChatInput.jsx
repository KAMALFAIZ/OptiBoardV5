import { useState, useRef } from 'react'
import { Send, Loader2, StopCircle } from 'lucide-react'

const placeholders = {
  chat: 'Posez une question sur vos donnees...',
  sql: 'Decrivez la requete SQL souhaitee...',
  help: 'Que voulez-vous savoir sur OptiBoard ?'
}

const MAX_CHARS = 2000

export default function ChatInput({ onSend, onStop, disabled, mode, history = [] }) {
  const [value, setValue] = useState('')
  const [historyIndex, setHistoryIndex] = useState(-1)
  const textareaRef = useRef(null)

  const handleSend = () => {
    if (!value.trim() || disabled) return
    onSend(value.trim())
    setValue('')
    setHistoryIndex(-1)
    if (textareaRef.current) {
      textareaRef.current.style.height = '40px'
    }
  }

  const handleKeyDown = (e) => {
    // Envoyer avec Entrée (sans Shift)
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
      return
    }

    // Vider l'input avec Escape
    if (e.key === 'Escape') {
      if (value) {
        setValue('')
        setHistoryIndex(-1)
      }
      return
    }

    // Historique des messages envoyés avec ↑/↓
    const userHistory = history.filter(Boolean)
    if (e.key === 'ArrowUp' && userHistory.length > 0) {
      const cursorAtStart = textareaRef.current?.selectionStart === 0
      if (cursorAtStart || historyIndex >= 0) {
        e.preventDefault()
        const newIndex = Math.min(historyIndex + 1, userHistory.length - 1)
        setHistoryIndex(newIndex)
        const msg = userHistory[userHistory.length - 1 - newIndex]
        setValue(msg)
        setTimeout(() => {
          if (textareaRef.current) {
            textareaRef.current.selectionStart = msg.length
            textareaRef.current.selectionEnd = msg.length
          }
        }, 0)
      }
      return
    }

    if (e.key === 'ArrowDown' && historyIndex >= 0) {
      e.preventDefault()
      const newIndex = historyIndex - 1
      setHistoryIndex(newIndex)
      if (newIndex < 0) {
        setValue('')
      } else {
        const msg = userHistory[userHistory.length - 1 - newIndex]
        setValue(msg)
      }
      return
    }

    // Toute autre frappe reset l'index historique
    if (historyIndex >= 0 && e.key.length === 1) {
      setHistoryIndex(-1)
    }
  }

  const handleInput = (e) => {
    const newVal = e.target.value
    if (newVal.length > MAX_CHARS) return
    setValue(newVal)
    // Auto-resize
    const el = e.target
    el.style.height = '40px'
    el.style.height = Math.min(el.scrollHeight, 128) + 'px'
  }

  // isStreaming = loading ET un handler Stop est fourni
  const isStreaming = disabled && typeof onStop === 'function'
  const charCount = value.length
  const showCounter = charCount > 100

  return (
    <div className="p-3 border-t border-gray-200 dark:border-gray-700 flex-shrink-0">
      <div className="flex items-end gap-2">
        <textarea
          ref={textareaRef}
          value={value}
          onChange={handleInput}
          onKeyDown={handleKeyDown}
          placeholder={placeholders[mode] || placeholders.chat}
          disabled={disabled && !isStreaming}
          rows={1}
          className="flex-1 resize-none rounded-xl border border-gray-300 dark:border-gray-600
                     bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100
                     placeholder-gray-400 dark:placeholder-gray-500
                     px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500
                     disabled:opacity-50 disabled:cursor-not-allowed"
          style={{ minHeight: '40px', maxHeight: '128px' }}
        />

        {/* Bouton Stop (pendant streaming) ou Send */}
        {isStreaming ? (
          <button
            onClick={onStop}
            className="w-10 h-10 flex items-center justify-center rounded-xl
                       bg-red-500 hover:bg-red-600 text-white
                       transition-colors flex-shrink-0"
            title="Arrêter la génération"
          >
            <StopCircle className="w-4 h-4" />
          </button>
        ) : (
          <button
            onClick={handleSend}
            disabled={disabled || !value.trim()}
            className="w-10 h-10 flex items-center justify-center rounded-xl
                       bg-primary-600 hover:bg-primary-700 text-white
                       disabled:opacity-40 disabled:cursor-not-allowed
                       transition-colors flex-shrink-0"
            title="Envoyer (Entrée)"
          >
            {disabled
              ? <Loader2 className="w-4 h-4 animate-spin" />
              : <Send className="w-4 h-4" />
            }
          </button>
        )}
      </div>

      {/* Ligne infos bas */}
      <div className="flex items-center justify-between mt-1.5">
        <p className="text-[10px] text-gray-400 dark:text-gray-500">
          {isStreaming
            ? 'Génération en cours… cliquez ⬛ pour arrêter'
            : 'Entrée · ↑↓ historique · Échap pour effacer'
          }
        </p>
        {showCounter && (
          <span className={`text-[10px] font-mono ${
            charCount > MAX_CHARS * 0.9
              ? 'text-red-400 dark:text-red-500'
              : 'text-gray-400 dark:text-gray-500'
          }`}>
            {charCount}/{MAX_CHARS}
          </span>
        )}
      </div>
    </div>
  )
}
