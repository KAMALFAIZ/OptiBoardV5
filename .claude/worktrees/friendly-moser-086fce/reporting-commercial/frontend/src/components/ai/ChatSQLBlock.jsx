import { useState, useRef } from 'react'
import { Code, Table, BarChart3, Copy, Check, AlertCircle, Database, LayoutGrid, Loader2, Pencil, X, Play } from 'lucide-react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'

export default function ChatSQLBlock({ sql, results, columns, sqlError, executionTimeMs, onOpenGridView, isSuperAdmin = false }) {
  // Pour les non-superadmin : démarrer sur la vue 'table' (les données), jamais sur 'sql'
  const [view, setView] = useState(results && results.length > 0 ? 'table' : (isSuperAdmin ? 'sql' : 'table'))
  const [copied, setCopied] = useState(false)
  const [isExecuting, setIsExecuting] = useState(false)
  const [execError, setExecError] = useState(null)
  // Éditeur SQL inline
  const [isEditing, setIsEditing] = useState(false)
  const [editedSql, setEditedSql] = useState('')
  const editTextareaRef = useRef(null)

  const hasResults = results && results.length > 0
  const isEmpty = results !== null && results !== undefined && results.length === 0
  const hasNumericColumn = columns?.some(col =>
    results?.[0]?.[col] !== undefined && !isNaN(Number(results[0][col]))
  )

  const activeSql = isEditing ? editedSql : sql

  const copySQL = () => {
    navigator.clipboard.writeText(activeSql)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const startEditing = () => {
    setEditedSql(sql)
    setIsEditing(true)
    setView('sql')
    setTimeout(() => editTextareaRef.current?.focus(), 50)
  }

  const cancelEditing = () => {
    setIsEditing(false)
    setEditedSql('')
    setExecError(null)
  }

  const getDwhHeaders = () => {
    try {
      const saved = localStorage.getItem('currentDWH')
      if (saved) {
        const parsed = JSON.parse(saved)
        if (parsed?.code) return { 'X-DWH-Code': parsed.code }
      }
    } catch { /* ignore */ }
    return {}
  }

  const handleExecuteInGridView = async (sqlToRun) => {
    const query = sqlToRun || activeSql
    if (!query || !onOpenGridView || isExecuting) return
    setIsExecuting(true)
    setExecError(null)
    try {
      const response = await fetch('/api/ai/sql/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...getDwhHeaders() },
        body: JSON.stringify({ query })
      })
      const data = await response.json()
      if (!response.ok) throw new Error(data.detail || "Erreur d'exécution")
      if (isEditing) setIsEditing(false)
      onOpenGridView(query, data.data, data.columns)
    } catch (e) {
      setExecError(e.message)
    } finally {
      setIsExecuting(false)
    }
  }

  return (
    <div className="mt-3 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
      {/* Barre d'onglets */}
      <div className="flex items-center border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900">

        {/* Onglet SQL — visible uniquement pour superadmin */}
        {isSuperAdmin && (
          <button
            onClick={() => { setView('sql'); if (isEditing) cancelEditing() }}
            className={`flex items-center gap-1 px-3 py-2 text-xs font-medium transition-colors
              ${view === 'sql' ? 'text-primary-600 border-b-2 border-primary-600' : 'text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'}`}
          >
            <Code className="w-3.5 h-3.5" /> SQL
          </button>
        )}

        {hasResults && (
          <button
            onClick={() => { setView('table'); cancelEditing() }}
            className={`flex items-center gap-1 px-3 py-2 text-xs font-medium transition-colors
              ${view === 'table' ? 'text-primary-600 border-b-2 border-primary-600' : 'text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'}`}
          >
            <Table className="w-3.5 h-3.5" /> Données ({results.length})
          </button>
        )}
        {hasResults && hasNumericColumn && (
          <button
            onClick={() => { setView('chart'); cancelEditing() }}
            className={`flex items-center gap-1 px-3 py-2 text-xs font-medium transition-colors
              ${view === 'chart' ? 'text-primary-600 border-b-2 border-primary-600' : 'text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'}`}
          >
            <BarChart3 className="w-3.5 h-3.5" /> Graphe
          </button>
        )}

        {/* Droite : badge résultats + temps + boutons action */}
        <div className="ml-auto flex items-center gap-0.5 px-2">
          {/* Badge : nombre de lignes et temps d'exécution */}
          {hasResults && (
            <span className="text-[10px] text-gray-400 dark:text-gray-500 mr-1 font-mono">
              {results.length} ligne{results.length > 1 ? 's' : ''}
              {executionTimeMs != null && ` · ${executionTimeMs}ms`}
            </span>
          )}

          {/* Bouton Éditer — superadmin seulement, en vue SQL */}
          {isSuperAdmin && view === 'sql' && !isEditing && (
            <button
              onClick={startEditing}
              title="Modifier le SQL"
              className="flex items-center gap-1 px-1.5 py-1 text-xs text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 rounded-lg transition-colors"
            >
              <Pencil className="w-3.5 h-3.5" />
            </button>
          )}

          {/* En mode édition : boutons Exécuter et Annuler — superadmin seulement */}
          {isSuperAdmin && isEditing && (
            <>
              <button
                onClick={() => handleExecuteInGridView(editedSql)}
                disabled={isExecuting || !editedSql.trim()}
                title="Exécuter le SQL modifié"
                className="flex items-center gap-1 px-2 py-1 text-xs font-medium
                           bg-primary-600 hover:bg-primary-700 text-white rounded-lg
                           disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {isExecuting
                  ? <Loader2 className="w-3 h-3 animate-spin" />
                  : <Play className="w-3 h-3" />
                }
                Exécuter
              </button>
              <button
                onClick={cancelEditing}
                title="Annuler les modifications"
                className="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 rounded-lg transition-colors"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </>
          )}

          {/* GridView — superadmin seulement */}
          {isSuperAdmin && !isEditing && onOpenGridView && sql && (
            hasResults ? (
              <button
                onClick={() => onOpenGridView(sql, results, columns)}
                title="Ouvrir dans GridView interactif"
                className="flex items-center gap-1 px-2 py-1 text-xs font-medium text-primary-600 dark:text-primary-400
                           hover:bg-primary-50 dark:hover:bg-primary-900/30 rounded-lg transition-colors"
              >
                <LayoutGrid className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">GridView</span>
              </button>
            ) : (
              <button
                onClick={() => handleExecuteInGridView(sql)}
                disabled={isExecuting}
                title="Exécuter la requête et ouvrir dans GridView"
                className="flex items-center gap-1 px-2 py-1 text-xs font-medium text-primary-600 dark:text-primary-400
                           hover:bg-primary-50 dark:hover:bg-primary-900/30 rounded-lg transition-colors
                           disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isExecuting ? (
                  <><Loader2 className="w-3.5 h-3.5 animate-spin" /><span className="hidden sm:inline">Exécution...</span></>
                ) : (
                  <><LayoutGrid className="w-3.5 h-3.5" /><span className="hidden sm:inline">Exécuter dans GridView</span></>
                )}
              </button>
            )
          )}

          {/* Copier le SQL — superadmin seulement */}
          {isSuperAdmin && (
            <button onClick={copySQL} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 p-1" title="Copier le SQL">
              {copied ? <Check className="w-3.5 h-3.5 text-green-500" /> : <Copy className="w-3.5 h-3.5" />}
            </button>
          )}
        </div>
      </div>

      {/* Erreur SQL (backend automatique) */}
      {sqlError && (
        <div className="px-3 py-2 bg-red-50 dark:bg-red-900/20 border-b border-red-200 dark:border-red-800
                        flex items-start gap-2 text-xs text-red-600 dark:text-red-400">
          <AlertCircle className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
          <span>Erreur d'exécution : {sqlError}</span>
        </div>
      )}

      {/* Erreur d'exécution manuelle */}
      {execError && (
        <div className="px-3 py-2 bg-red-50 dark:bg-red-900/20 border-b border-red-200 dark:border-red-800
                        flex items-start gap-2 text-xs text-red-600 dark:text-red-400">
          <AlertCircle className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
          <span>Erreur lors de l'exécution : {execError}</span>
        </div>
      )}

      {/* Contenu */}
      <div className="max-h-64 overflow-auto">
        {view === 'sql' && !isEditing && (
          <pre className="p-3 text-xs font-mono text-gray-800 dark:text-gray-200
                          bg-gray-50 dark:bg-gray-900 whitespace-pre-wrap break-all">
            {sql}
          </pre>
        )}

        {/* Mode édition SQL */}
        {view === 'sql' && isEditing && (
          <div className="relative">
            <textarea
              ref={editTextareaRef}
              value={editedSql}
              onChange={e => setEditedSql(e.target.value)}
              className="w-full p-3 text-xs font-mono bg-gray-900 text-green-300
                         border-0 outline-none resize-none
                         focus:ring-1 focus:ring-primary-500"
              style={{ minHeight: '120px' }}
              placeholder="Entrez votre requête SQL…"
              spellCheck={false}
            />
            <div className="absolute bottom-2 right-2 text-[10px] text-gray-500 pointer-events-none">
              Modifiez le SQL puis cliquez Exécuter
            </div>
          </div>
        )}

        {view === 'table' && hasResults && (
          <table className="w-full text-xs">
            <thead className="bg-gray-100 dark:bg-gray-800 sticky top-0">
              <tr>
                {columns.map(col => (
                  <th key={col} className="px-3 py-2 text-left font-semibold text-gray-600 dark:text-gray-300 whitespace-nowrap">
                    {col}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {results.slice(0, 100).map((row, i) => (
                <tr key={i} className={i % 2 === 0
                  ? 'bg-white dark:bg-gray-900'
                  : 'bg-gray-50 dark:bg-gray-800/50'}>
                  {columns.map(col => (
                    <td key={col} className="px-3 py-1.5 text-gray-700 dark:text-gray-300 whitespace-nowrap">
                      {formatCellValue(row[col])}
                    </td>
                  ))}
                </tr>
              ))}
              {results.length > 100 && (
                <tr>
                  <td colSpan={columns.length} className="px-3 py-2 text-center text-gray-400 text-xs italic">
                    ... {results.length - 100} lignes supplémentaires — ouvrir dans GridView pour tout voir
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        )}

        {view === 'table' && isEmpty && !sqlError && (
          <div className="flex flex-col items-center justify-center py-6 text-gray-400 dark:text-gray-500">
            <Database className="w-6 h-6 mb-2 opacity-50" />
            <p className="text-xs">Aucune donnée pour cette période</p>
          </div>
        )}

        {view === 'chart' && hasResults && (
          <div className="p-3 h-48">
            <MiniChart data={results} columns={columns} />
          </div>
        )}
      </div>
    </div>
  )
}

function MiniChart({ data, columns }) {
  const numericCols = columns.filter(col => !isNaN(Number(data[0]?.[col])))
  const labelCol = columns.find(col => isNaN(Number(data[0]?.[col]))) || columns[0]
  const valueCol = numericCols[0]

  if (!valueCol) return <p className="text-xs text-gray-500 text-center mt-8">Pas de donnees numeriques</p>

  const chartData = data.slice(0, 15).map(row => ({
    name: String(row[labelCol] || '').slice(0, 15),
    value: Number(row[valueCol]) || 0
  }))

  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={chartData} margin={{ top: 4, right: 4, bottom: 20, left: 0 }}>
        <XAxis dataKey="name" tick={{ fontSize: 9 }} angle={-30} textAnchor="end" />
        <YAxis tick={{ fontSize: 9 }} />
        <Tooltip formatter={(v) => [v.toLocaleString('fr-FR'), valueCol]} />
        <Bar dataKey="value" fill="var(--color-primary-500, #3b82f6)" radius={[2, 2, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  )
}

function formatCellValue(value) {
  if (value === null || value === undefined) return '-'
  if (typeof value === 'number') {
    if (Math.abs(value) >= 1000) return value.toLocaleString('fr-FR', { maximumFractionDigits: 2 })
    return value.toLocaleString('fr-FR')
  }
  if (typeof value === 'string' && value.match(/^\d{4}-\d{2}-\d{2}/)) {
    try { return new Date(value).toLocaleDateString('fr-FR') } catch { return value }
  }
  return String(value)
}
