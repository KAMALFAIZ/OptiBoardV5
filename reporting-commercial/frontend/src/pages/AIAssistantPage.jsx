import { useEffect, useState } from 'react'
import { Bot, MessageSquare, Code, HelpCircle, Trash2, Settings, Minimize2 } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useChat } from '../context/ChatContext'
import ChatMessageList from '../components/ai/ChatMessageList'
import ChatInput from '../components/ai/ChatInput'
import AIGridViewModal from '../components/ai/AIGridViewModal'

const modeConfig = [
  { id: 'chat', label: 'Analyse', icon: MessageSquare, description: 'Questions sur vos donnees' },
  { id: 'sql', label: 'Assistant SQL', icon: Code, description: 'Generer des requetes SQL' },
  { id: 'help', label: 'Aide OptiBoard', icon: HelpCircle, description: 'Guide utilisateur' }
]

export default function AIAssistantPage() {
  const navigate = useNavigate()
  const {
    messages, isLoading, error, mode, aiStatus,
    pendingDwhSelection,
    setMode, sendMessageStream, stopStreaming, selectDwhAndResend, clearConversation,
    openWidget, closeFullPage, loadAiStatus
  } = useChat()

  const [gridViewData, setGridViewData] = useState(null) // { sql, results, columns }

  // Historique des messages utilisateur pour la navigation ↑/↓
  const userHistory = messages.filter(m => m.role === 'user').map(m => m.content)

  useEffect(() => {
    loadAiStatus()
  }, [loadAiStatus])

  const handleMinimize = () => {
    closeFullPage()
    openWidget()
  }

  return (
    <div className="flex h-full gap-4">
      {/* Panneau lateral gauche */}
      <div className="w-60 flex-shrink-0 space-y-4">
        {/* Header */}
        <div className="flex items-center gap-2">
          <div className="w-9 h-9 rounded-xl bg-primary-100 dark:bg-primary-900/30 flex items-center justify-center">
            <Bot className="w-5 h-5 text-primary-600 dark:text-primary-400" />
          </div>
          <div>
            <h1 className="text-base font-bold text-gray-900 dark:text-white">Assistant IA</h1>
            <p className="text-[10px] text-gray-500 dark:text-gray-400">OptiBoard Intelligence</p>
          </div>
        </div>

        {/* Statut fournisseur */}
        {aiStatus && (
          <div className={`p-3 rounded-xl border text-sm
            ${aiStatus.configured
              ? 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800'
              : 'bg-amber-50 dark:bg-amber-900/20 border-amber-200 dark:border-amber-800'
            }`}>
            <div className="flex items-center gap-2">
              <span className={`w-2 h-2 rounded-full flex-shrink-0 ${aiStatus.configured ? 'bg-green-500' : 'bg-amber-500'}`} />
              <span className="font-medium text-gray-700 dark:text-gray-300 text-xs">
                {aiStatus.configured ? `${aiStatus.provider} (${aiStatus.model})` : 'Non configure'}
              </span>
            </div>
            {!aiStatus.configured && (
              <button
                onClick={() => navigate('/settings')}
                className="mt-2 text-xs text-primary-600 dark:text-primary-400 hover:underline"
              >
                Configurer l'IA &rarr;
              </button>
            )}
          </div>
        )}

        {/* Selecteur de mode */}
        <div>
          <p className="text-[10px] font-semibold text-gray-500 dark:text-gray-400 mb-2 uppercase tracking-wider">
            Mode
          </p>
          <div className="space-y-1">
            {modeConfig.map(({ id, label, icon: Icon, description }) => (
              <button
                key={id}
                onClick={() => setMode(id)}
                className={`w-full text-left p-2.5 rounded-xl transition-colors
                  ${mode === id
                    ? 'bg-primary-50 dark:bg-primary-900/20 text-primary-700 dark:text-primary-400 border border-primary-200 dark:border-primary-800'
                    : 'hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-700 dark:text-gray-300'
                  }`}
              >
                <div className="flex items-center gap-2">
                  <Icon className="w-4 h-4 flex-shrink-0" />
                  <span className="text-sm font-medium">{label}</span>
                </div>
                <p className="text-[10px] text-gray-500 dark:text-gray-400 mt-0.5 ml-6">{description}</p>
              </button>
            ))}
          </div>
        </div>

        {/* Actions */}
        <div className="space-y-1 pt-2 border-t border-gray-200 dark:border-gray-700">
          <button
            onClick={clearConversation}
            className="w-full flex items-center gap-2 px-3 py-2 text-sm text-gray-600 dark:text-gray-300
                       hover:bg-gray-100 dark:hover:bg-gray-800 rounded-xl transition-colors"
          >
            <Trash2 className="w-4 h-4" />
            Nouvelle conversation
          </button>
          <button
            onClick={() => navigate('/settings')}
            className="w-full flex items-center gap-2 px-3 py-2 text-sm text-gray-600 dark:text-gray-300
                       hover:bg-gray-100 dark:hover:bg-gray-800 rounded-xl transition-colors"
          >
            <Settings className="w-4 h-4" />
            Parametres IA
          </button>
        </div>
      </div>

      {/* Zone principale de chat */}
      <div className="flex-1 flex flex-col bg-white dark:bg-gray-900
                      rounded-2xl border border-gray-200 dark:border-gray-700 overflow-hidden shadow-sm">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3
                        border-b border-gray-200 dark:border-gray-700 flex-shrink-0">
          <div className="flex items-center gap-2 text-gray-700 dark:text-gray-300">
            {(() => {
              const cfg = modeConfig.find(m => m.id === mode)
              if (!cfg) return null
              const Icon = cfg.icon
              return (
                <>
                  <Icon className="w-5 h-5 text-primary-600 dark:text-primary-400" />
                  <span className="font-semibold text-sm">{cfg.label}</span>
                  <span className="text-gray-400 dark:text-gray-500 text-xs">&mdash; {cfg.description}</span>
                </>
              )
            })()}
          </div>
          <button
            onClick={handleMinimize}
            className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg text-gray-500 transition-colors"
            title="Reduire en widget"
          >
            <Minimize2 className="w-4 h-4" />
          </button>
        </div>

        {/* Messages */}
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
          <div className="mx-5 mb-3 p-3 bg-red-50 dark:bg-red-900/20 rounded-xl
                          text-sm text-red-600 dark:text-red-400 border border-red-200 dark:border-red-800">
            {error}
          </div>
        )}

        {/* Input */}
        <ChatInput
          onSend={(text) => sendMessageStream(text)}
          onStop={stopStreaming}
          disabled={isLoading || !aiStatus?.configured}
          history={userHistory}
          mode={mode}
        />
      </div>

      {/* Modal GridView */}
      {gridViewData && (
        <AIGridViewModal
          sql={gridViewData.sql}
          results={gridViewData.results}
          columns={gridViewData.columns}
          onClose={() => setGridViewData(null)}
        />
      )}
    </div>
  )
}
