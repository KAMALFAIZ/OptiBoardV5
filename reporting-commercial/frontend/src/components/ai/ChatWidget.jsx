import { useEffect, useState } from 'react'
import { X, Trash2, Maximize2, Bot, XCircle, Settings } from 'lucide-react'
import { useChat } from '../../context/ChatContext'
import { useAuth } from '../../context/AuthContext'
import { useNavigate } from 'react-router-dom'
import ChatMessageList from './ChatMessageList'
import ChatInput from './ChatInput'
import AIGridViewModal from './AIGridViewModal'

export default function ChatWidget() {
  const { isAuthenticated } = useAuth()
  const navigate = useNavigate()
  const {
    isOpen, isFullPage,
    messages, isLoading, error, mode, aiStatus,
    pendingDwhSelection,
    setMode, sendMessageStream, stopStreaming, selectDwhAndResend, clearConversation,
    openWidget, closeWidget, openFullPage, loadAiStatus
  } = useChat()

  // Historique des messages utilisateur pour la navigation ↑/↓
  const userHistory = messages.filter(m => m.role === 'user').map(m => m.content)

  const [gridViewData, setGridViewData] = useState(null) // { sql, results, columns }

  useEffect(() => {
    if (isAuthenticated) loadAiStatus()
  }, [isAuthenticated, loadAiStatus])

  // Masque si non connecte ou en mode page complete
  if (!isAuthenticated || isFullPage) return null

  return (
    <>
      {/* Bulle d'ouverture */}
      {!isOpen && (
        <button
          onClick={openWidget}
          className="fixed bottom-6 right-6 z-[60] w-14 h-14 bg-primary-600 hover:bg-primary-700
                     text-white rounded-full shadow-lg flex items-center justify-center
                     transition-all duration-200 hover:scale-110"
          title="Assistant IA OptiBoard"
        >
          <Bot className="w-7 h-7" />
          {aiStatus?.configured && (
            <span className="absolute top-0 right-0 w-3 h-3 bg-green-400 rounded-full border-2 border-white dark:border-gray-900" />
          )}
        </button>
      )}

      {/* Panneau de chat */}
      {isOpen && (
        <div className="fixed bottom-6 right-6 z-[60] w-[380px] h-[580px] max-h-[80vh]
                        flex flex-col bg-white dark:bg-gray-900
                        rounded-2xl shadow-2xl border border-gray-200 dark:border-gray-700
                        overflow-hidden">
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3
                          bg-primary-600 dark:bg-primary-700 text-white flex-shrink-0">
            <div className="flex items-center gap-2">
              <Bot className="w-5 h-5" />
              <span className="font-semibold text-sm">Assistant IA</span>
              {aiStatus?.provider && aiStatus.provider !== 'non configure' && (
                <span className="text-xs text-primary-200">
                  {aiStatus.provider}
                </span>
              )}
            </div>
            <div className="flex items-center gap-0.5">
              <button
                onClick={clearConversation}
                className="p-1.5 hover:bg-white/20 rounded-lg transition-colors"
                title="Nouvelle conversation"
              >
                <Trash2 className="w-4 h-4" />
              </button>
              <button
                onClick={openFullPage}
                className="p-1.5 hover:bg-white/20 rounded-lg transition-colors"
                title="Ouvrir en pleine page"
              >
                <Maximize2 className="w-4 h-4" />
              </button>
              <button
                onClick={closeWidget}
                className="p-1.5 hover:bg-white/20 rounded-lg transition-colors"
                title="Fermer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Selecteur de mode */}
          <div className="flex border-b border-gray-200 dark:border-gray-700 flex-shrink-0">
            {[
              { id: 'chat', label: 'Analyse' },
              { id: 'sql', label: 'SQL' },
              { id: 'help', label: 'Aide' }
            ].map(({ id, label }) => (
              <button
                key={id}
                onClick={() => setMode(id)}
                className={`flex-1 py-2 text-xs font-medium transition-colors
                  ${mode === id
                    ? 'text-primary-600 dark:text-primary-400 border-b-2 border-primary-600 dark:border-primary-400'
                    : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
                  }`}
              >
                {label}
              </button>
            ))}
          </div>

          {/* Message IA non configuree */}
          {aiStatus && !aiStatus.configured && (
            <div className="mx-3 mt-3 p-3 bg-amber-50 dark:bg-amber-900/20 rounded-xl
                            text-xs text-amber-700 dark:text-amber-300 border border-amber-200 dark:border-amber-700">
              <p className="mb-2">Module IA non configure. Ajoutez votre cle API pour activer l'assistant.</p>
              <button
                onClick={() => { closeWidget(); navigate('/settings') }}
                className="inline-flex items-center gap-1 px-2 py-1 bg-amber-100 dark:bg-amber-800 rounded text-xs font-medium hover:bg-amber-200 dark:hover:bg-amber-700 transition-colors"
              >
                <Settings className="w-3 h-3" />
                Parametres IA
              </button>
            </div>
          )}

          {/* Liste de messages */}
          <ChatMessageList
            messages={messages}
            isLoading={isLoading}
            onSuggestionClick={(text) => sendMessageStream(text)}
            onOpenGridView={(sql, results, columns) => setGridViewData({ sql, results, columns })}
            pendingDwhSelection={pendingDwhSelection}
            onSelectDwh={selectDwhAndResend}
          />

          {/* Erreur */}
          {error && (
            <div className="mx-3 mb-2 p-2 bg-red-50 dark:bg-red-900/20 rounded-xl
                            text-xs text-red-600 dark:text-red-400 border border-red-200 dark:border-red-800
                            flex items-start gap-2">
              <XCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
              <span className="flex-1">{error}</span>
            </div>
          )}

          {/* Zone de saisie */}
          <ChatInput
            onSend={(text) => sendMessageStream(text)}
            onStop={stopStreaming}
            disabled={isLoading}
            mode={mode}
            history={userHistory}
          />
        </div>
      )}

      {/* Modal GridView (plein écran, au-dessus du widget) */}
      {gridViewData && (
        <AIGridViewModal
          sql={gridViewData.sql}
          results={gridViewData.results}
          columns={gridViewData.columns}
          onClose={() => setGridViewData(null)}
        />
      )}
    </>
  )
}
