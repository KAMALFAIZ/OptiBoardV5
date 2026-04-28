import { useEffect, useRef, useState, useContext } from 'react'
import { Bot, User, Database, Copy, Check } from 'lucide-react'
import ChatSQLBlock from './ChatSQLBlock'
import { useAuth } from '../../context/AuthContext'
import FeedbackButtons from './FeedbackButtons'

// Suggestions de suivi contextuelles selon le contenu de la réponse
function getFollowUpSuggestions(content) {
  const lower = (content || '').toLowerCase()

  if (lower.includes('client') || lower.includes('chiffre d') || lower.includes('ca total')) {
    return [
      "Évolution du CA sur les 3 derniers mois ?",
      "Quels clients sont en baisse par rapport à l'année dernière ?",
    ]
  }
  if (lower.includes('stock') || lower.includes('article') || lower.includes('rupture')) {
    return [
      "Quels articles sont en rupture de stock ?",
      "Valeur totale du stock par dépôt ?",
    ]
  }
  if (lower.includes('échéance') || lower.includes('creance') || lower.includes('règlement') || lower.includes('impayé')) {
    return [
      "Créances échues depuis plus de 90 jours ?",
      "Top 5 clients avec le plus de retards de paiement ?",
    ]
  }
  if (lower.includes('marge') || lower.includes('revient') || lower.includes('profit')) {
    return [
      "Quels articles ont la marge la plus faible ?",
      "Évolution de la marge brute sur 6 mois ?",
    ]
  }
  // Suggestions génériques
  return [
    "Peux-tu détailler ce résultat ?",
    "Affiche les données sous forme de tableau",
  ]
}

export default function ChatMessageList({ messages, isLoading, onSuggestionClick, onOpenGridView, pendingDwhSelection, onSelectDwh }) {
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isLoading])

  // Index du dernier message assistant terminé (non-streaming)
  const lastAssistantIdx = messages.reduce((last, msg, idx) =>
    msg.role === 'assistant' && !msg.streaming ? idx : last, -1)

  if (messages.length === 0) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-6 text-center">
        <div className="w-16 h-16 rounded-2xl bg-primary-100 dark:bg-primary-900/30 flex items-center justify-center mb-4">
          <Bot className="w-8 h-8 text-primary-600 dark:text-primary-400" />
        </div>
        <p className="text-sm font-semibold text-gray-700 dark:text-gray-300">
          Comment puis-je vous aider ?
        </p>
        <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 max-w-[250px]">
          Posez une question sur vos ventes, stocks ou creances
        </p>
        <div className="mt-4 space-y-2 w-full max-w-[280px]">
          {[
            "Quel est le CA du mois en cours ?",
            "Top 5 clients par chiffre d'affaires",
            "Etat du stock dormant"
          ].map((suggestion, i) => (
            <button
              key={i}
              onClick={() => onSuggestionClick?.(suggestion)}
              className="w-full text-left text-xs px-3 py-2.5 rounded-xl
                         bg-gray-50 dark:bg-gray-800 hover:bg-primary-50 dark:hover:bg-primary-900/20
                         text-gray-600 dark:text-gray-300 border border-gray-200 dark:border-gray-700
                         transition-colors"
            >
              {suggestion}
            </button>
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-4">
      {messages.map((msg, idx) => {
        // Trouver la question utilisateur précédant ce message assistant
        let userQuestion = ''
        if (msg.role === 'assistant' && !msg.streaming) {
          for (let i = idx - 1; i >= 0; i--) {
            if (messages[i].role === 'user') {
              userQuestion = messages[i].content
              break
            }
          }
        }
        return (
          <div key={msg.id}>
            <MessageBubble message={msg} onOpenGridView={onOpenGridView} />

            {/* Feedback 👍/👎 pour les messages assistant terminés */}
            {msg.role === 'assistant' && !msg.streaming && (
              <FeedbackButtons
                question={userQuestion}
                sqlQuery={msg.sqlQuery}
                messageId={msg.id}
              />
            )}

            {/* Suggestions de suivi après le dernier message assistant terminé */}
            {idx === lastAssistantIdx && !isLoading && !pendingDwhSelection && (
              <FollowUpSuggestions
                content={msg.content}
                onSuggestionClick={onSuggestionClick}
              />
            )}
          </div>
        )
      })}

      {/* Sélecteur DWH inline — affiché quand le backend détecte plusieurs DWH */}
      {pendingDwhSelection && onSelectDwh && (
        <div className="flex gap-2">
          <div className="w-8 h-8 rounded-full bg-gray-100 dark:bg-gray-800 flex items-center justify-center flex-shrink-0">
            <Bot className="w-4 h-4 text-primary-600 dark:text-primary-400" />
          </div>
          <div className="max-w-[85%] rounded-2xl rounded-tl-sm px-4 py-3
                          bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-gray-100">
            <div className="flex items-center gap-2 mb-3 text-sm font-medium">
              <Database className="w-4 h-4 text-primary-600 dark:text-primary-400 flex-shrink-0" />
              Plusieurs datasources DWH sont disponibles. Lequel souhaitez-vous interroger ?
            </div>
            <div className="space-y-2">
              {pendingDwhSelection.dwh_list.map(dwh => (
                <button
                  key={dwh.code}
                  onClick={() => onSelectDwh(dwh.code, dwh.nom)}
                  className="w-full text-left px-3 py-2.5 rounded-xl
                             bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600
                             hover:bg-primary-50 dark:hover:bg-primary-900/30
                             hover:border-primary-300 dark:hover:border-primary-700
                             transition-colors group"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-gray-800 dark:text-gray-200 group-hover:text-primary-700 dark:group-hover:text-primary-300">
                      {dwh.nom}
                    </span>
                    <span className="text-xs text-gray-400 dark:text-gray-500 font-mono ml-2">
                      {dwh.code}
                    </span>
                  </div>
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {isLoading && !messages.find(m => m.streaming) && (
        <div className="flex items-center gap-2 text-gray-400">
          <div className="w-8 h-8 rounded-full bg-primary-100 dark:bg-primary-900/30 flex items-center justify-center flex-shrink-0">
            <Bot className="w-4 h-4 text-primary-600 dark:text-primary-400" />
          </div>
          <div className="flex gap-1">
            <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
            <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
            <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
          </div>
        </div>
      )}
      <div ref={bottomRef} />
    </div>
  )
}

function FollowUpSuggestions({ content, onSuggestionClick }) {
  const suggestions = getFollowUpSuggestions(content)
  if (!suggestions.length || !onSuggestionClick) return null

  return (
    <div className="ml-10 mt-2 flex flex-wrap gap-1.5">
      {suggestions.map((s, i) => (
        <button
          key={i}
          onClick={() => onSuggestionClick(s)}
          className="text-[11px] px-2.5 py-1.5 rounded-full
                     bg-primary-50 dark:bg-primary-900/20
                     text-primary-700 dark:text-primary-300
                     border border-primary-200 dark:border-primary-800
                     hover:bg-primary-100 dark:hover:bg-primary-900/40
                     transition-colors"
        >
          {s}
        </button>
      ))}
    </div>
  )
}

function MessageBubble({ message, onOpenGridView }) {
  const isUser = message.role === 'user'
  const [copied, setCopied] = useState(false)
  const { user } = useAuth()
  // Affichage SQL (code + execution) reservé aux superadmin uniquement
  const isSuperAdmin = user?.role === 'superadmin'

  const handleCopy = () => {
    const textOnly = message.content.replace(/```sql[\s\S]*?```/gi, '').trim()
    navigator.clipboard.writeText(textOnly).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }

  return (
    <div className={`flex gap-2 ${isUser ? 'flex-row-reverse' : 'flex-row'} group`}>
      <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0
        ${isUser
          ? 'bg-primary-600 text-white'
          : 'bg-gray-100 dark:bg-gray-800 text-primary-600 dark:text-primary-400'
        }`}>
        {isUser ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
      </div>

      <div className="relative max-w-[85%]">
        <div className={`rounded-2xl px-4 py-3 text-sm leading-relaxed
          ${isUser
            ? 'bg-primary-600 text-white rounded-tr-sm'
            : 'bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-gray-100 rounded-tl-sm'
          }`}>
          <SimpleMarkdown content={message.content} />

          {message.streaming && (
            <span className="inline-block w-1.5 h-4 bg-current animate-pulse ml-0.5 rounded-sm" />
          )}

          {/* Indicateur si interrompu */}
          {message.aborted && (
            <span className="block mt-1 text-[10px] text-gray-400 dark:text-gray-500 italic">
              — génération interrompue
            </span>
          )}

          {message.sqlQuery && (
            <ChatSQLBlock
              sql={message.sqlQuery}
              results={message.sqlResults}
              columns={message.sqlColumns}
              sqlError={message.sqlError}
              executionTimeMs={message.sqlExecutionTime}
              onOpenGridView={onOpenGridView}
              isSuperAdmin={isSuperAdmin}
            />
          )}
        </div>

        {/* Bouton Copier au hover (messages assistant uniquement) */}
        {!isUser && !message.streaming && (
          <button
            onClick={handleCopy}
            className="absolute -bottom-5 right-0
                       opacity-0 group-hover:opacity-100
                       flex items-center gap-1 px-1.5 py-0.5 rounded-md
                       bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700
                       text-[10px] text-gray-400 dark:text-gray-500
                       hover:text-gray-600 dark:hover:text-gray-300
                       shadow-sm transition-all duration-150"
            title="Copier la réponse"
          >
            {copied
              ? <><Check className="w-3 h-3 text-green-500" /> Copié</>
              : <><Copy className="w-3 h-3" /> Copier</>
            }
          </button>
        )}
      </div>
    </div>
  )
}

function SimpleMarkdown({ content }) {
  // Supprimer les blocs SQL (affiches separement par ChatSQLBlock)
  const textOnly = content.replace(/```sql[\s\S]*?```/gi, '').trim()
  if (!textOnly) return null

  const lines = textOnly.split('\n')
  return (
    <div className="whitespace-pre-wrap break-words">
      {lines.map((line, i) => {
        if (line.startsWith('### ')) return <div key={i} className="font-bold mt-2 mb-1">{line.slice(4)}</div>
        if (line.startsWith('## ')) return <div key={i} className="font-bold text-base mt-2 mb-1">{line.slice(3)}</div>
        if (line.startsWith('- ') || line.startsWith('* ')) {
          return <div key={i} className="flex gap-1.5 ml-1"><span className="text-primary-400">&#8226;</span><span>{renderInline(line.slice(2))}</span></div>
        }
        if (/^\d+\.\s/.test(line)) {
          const match = line.match(/^(\d+)\.\s(.*)/)
          return <div key={i} className="flex gap-1.5 ml-1"><span className="text-primary-400 font-medium">{match[1]}.</span><span>{renderInline(match[2])}</span></div>
        }
        if (!line.trim()) return <div key={i} className="h-2" />
        return <div key={i}>{renderInline(line)}</div>
      })}
    </div>
  )
}

function renderInline(text) {
  return text.split(/(\*\*.*?\*\*)/g).map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return <strong key={i}>{part.slice(2, -2)}</strong>
    }
    return part.split(/(`.*?`)/g).map((sub, j) => {
      if (sub.startsWith('`') && sub.endsWith('`')) {
        return <code key={`${i}-${j}`} className="bg-gray-200 dark:bg-gray-700 px-1 rounded text-xs font-mono">{sub.slice(1, -1)}</code>
      }
      return sub
    })
  })
}
