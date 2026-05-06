import { useState, useEffect, useCallback, useRef } from 'react'
import { useParams } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useGlobalFilters } from '../context/GlobalFilterContext'
import {
  getSpreadsheet, getSpreadsheetData,
  getSpreadsheetUserState, saveSpreadsheetUserState, resetSpreadsheetUserState,
  exportSpreadsheet, downloadBlob, importSpreadsheetExcel
} from '../services/api'
import {
  RefreshCw, Save, Download, RotateCcw, Loader2, FileSpreadsheet,
  AlertCircle, Upload
} from 'lucide-react'
import { Workbook } from '@fortune-sheet/react'
import '@fortune-sheet/react/dist/index.css'

export default function SpreadsheetViewer() {
  const { id } = useParams()
  const { user } = useAuth()
  const { filters: globalFilters } = useGlobalFilters()

  const [config, setConfig] = useState(null)
  const [sheetData, setSheetData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [saving, setSaving] = useState(false)
  const [exporting, setExporting] = useState(false)
  const [error, setError] = useState(null)
  const [hasUserState, setHasUserState] = useState(false)
  const [workbookKey, setWorkbookKey] = useState(0)
  const [importing, setImporting] = useState(false)

  const saveTimerRef = useRef(null)
  const currentSheetsRef = useRef(null)
  const fileInputRef = useRef(null)

  const buildContext = useCallback(() => ({
    dateDebut: globalFilters?.dateDebut,
    dateFin: globalFilters?.dateFin,
    societe: globalFilters?.societe,
  }), [globalFilters])

  useEffect(() => {
    if (id) loadAll()
    return () => {
      if (saveTimerRef.current) clearTimeout(saveTimerRef.current)
    }
  }, [id])

  const loadAll = async () => {
    setLoading(true)
    setError(null)
    try {
      const [configRes, dataRes, stateRes] = await Promise.all([
        getSpreadsheet(id),
        getSpreadsheetData(id, buildContext()),
        user?.id ? getSpreadsheetUserState(id, user.id) : Promise.resolve({ data: { data: null } }),
      ])

      if (!configRes.data?.success) throw new Error('Config introuvable')
      setConfig(configRes.data.data)

      const userState = stateRes.data?.data?.sheet_data
      setHasUserState(!!userState)

      if (userState && Array.isArray(userState) && userState.length > 0) {
        setSheetData(userState)
      } else if (dataRes.data?.success) {
        const fortuneSheets = buildFortuneSheets(dataRes.data.sheets || [])
        setSheetData(fortuneSheets)
      }
    } catch (err) {
      console.error('Erreur chargement:', err)
      setError(err.response?.data?.detail || err.message || 'Erreur de chargement')
    } finally {
      setLoading(false)
    }
  }

  const buildFortuneSheets = (apiSheets) => {
    return apiSheets.map((s, i) => ({
      name: s.name || `Feuille ${i + 1}`,
      celldata: s.celldata || [],
      order: i,
      row: Math.max((s.row_count || 0) + 20, 80),
      column: Math.max((s.column_count || 0) + 10, 26),
      config: {},
      status: i === 0 ? 1 : 0,
    }))
  }

  const handleRefresh = async () => {
    setRefreshing(true)
    setError(null)
    try {
      const dataRes = await getSpreadsheetData(id, buildContext())
      if (dataRes.data?.success) {
        const fortuneSheets = buildFortuneSheets(dataRes.data.sheets || [])
        setSheetData(fortuneSheets)
        setWorkbookKey(k => k + 1)
        setHasUserState(false)
      }
    } catch (err) {
      setError('Erreur rafraichissement: ' + (err.message || ''))
    } finally {
      setRefreshing(false)
    }
  }

  const handleSave = async () => {
    if (!user?.id || !currentSheetsRef.current) return
    setSaving(true)
    try {
      await saveSpreadsheetUserState(id, user.id, {
        sheet_data: currentSheetsRef.current,
      })
      setHasUserState(true)
    } catch (err) {
      console.error('Erreur sauvegarde:', err)
      setError('Erreur sauvegarde')
    } finally {
      setSaving(false)
    }
  }

  const handleReset = async () => {
    if (!user?.id) return
    if (!window.confirm('Reinitialiser vos modifications ? Les donnees seront rechargees depuis la source.')) return
    try {
      await resetSpreadsheetUserState(id, user.id)
      setHasUserState(false)
      await handleRefresh()
    } catch (err) {
      setError('Erreur reinitialisation')
    }
  }

  const handleExport = async () => {
    setExporting(true)
    try {
      const res = await exportSpreadsheet(id, buildContext())
      const filename = (config?.nom || 'spreadsheet').replace(/[^\w\s-]/g, '') + '.xlsx'
      downloadBlob(res.data, filename)
    } catch (err) {
      setError('Erreur export')
    } finally {
      setExporting(false)
    }
  }

  const handleChange = useCallback((data) => {
    currentSheetsRef.current = data
  }, [])

  const handleImportExcel = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    e.target.value = ''
    setImporting(true)
    setError(null)
    try {
      const res = await importSpreadsheetExcel(file)
      if (res.data?.success) {
        const fortuneSheets = (res.data.sheets || []).map((s, i) => ({
          name: s.name || `Feuille ${i + 1}`,
          celldata: s.celldata || [],
          order: i,
          row: Math.max((s.row_count || 0) + 20, 80),
          column: Math.max((s.column_count || 0) + 10, 26),
          config: s.config || {},
          status: i === 0 ? 1 : 0,
        }))
        setSheetData(fortuneSheets)
        setWorkbookKey(k => k + 1)
      }
    } catch (err) {
      setError('Erreur import: ' + (err.response?.data?.detail || err.message))
    } finally {
      setImporting(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full bg-gray-50 dark:bg-gray-900">
        <div className="text-center">
          <Loader2 className="w-10 h-10 animate-spin text-primary-500 mx-auto mb-3" />
          <p className="text-sm text-gray-500">Chargement du classeur...</p>
        </div>
      </div>
    )
  }

  if (error && !sheetData) {
    return (
      <div className="flex items-center justify-center h-full bg-gray-50 dark:bg-gray-900">
        <div className="text-center max-w-md">
          <AlertCircle className="w-10 h-10 text-red-400 mx-auto mb-3" />
          <p className="text-sm text-red-600 dark:text-red-400 mb-4">{error}</p>
          <button onClick={loadAll}
            className="px-4 py-2 text-sm bg-primary-600 text-white rounded-xl hover:bg-primary-700 transition-colors">
            Reessayer
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full bg-gray-50 dark:bg-gray-900">
      {/* Toolbar */}
      <div className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-4 py-2 flex items-center gap-3">
        <div className="flex items-center gap-2">
          <FileSpreadsheet size={18} className="text-primary-500" />
          <h1 className="text-sm font-semibold text-gray-800 dark:text-gray-200 truncate max-w-xs">
            {config?.nom || 'Classeur'}
          </h1>
          {config?.description && (
            <span className="text-xs text-gray-400 truncate max-w-xs hidden md:inline">
              — {config.description}
            </span>
          )}
        </div>

        <div className="flex-1" />

        {error && (
          <span className="text-xs text-red-500 mr-2">{error}</span>
        )}

        {hasUserState && (
          <span className="text-xs bg-amber-50 dark:bg-amber-900/20 text-amber-600 dark:text-amber-400 px-2 py-0.5 rounded-full">
            Modifications sauvegardees
          </span>
        )}

        <button onClick={handleRefresh} disabled={refreshing}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-40 transition-colors"
          title="Rafraichir les donnees">
          <RefreshCw size={14} className={refreshing ? 'animate-spin' : ''} />
          Rafraichir
        </button>

        <button onClick={handleSave} disabled={saving}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-primary-50 dark:bg-primary-900/20 text-primary-700 dark:text-primary-300 hover:bg-primary-100 dark:hover:bg-primary-900/40 disabled:opacity-40 transition-colors">
          {saving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
          Sauvegarder
        </button>

        {hasUserState && (
          <button onClick={handleReset}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
            title="Reinitialiser mes modifications">
            <RotateCcw size={14} />
          </button>
        )}

        <input ref={fileInputRef} type="file" accept=".xlsx,.xls" onChange={handleImportExcel} className="hidden" />
        <button onClick={() => fileInputRef.current?.click()} disabled={importing}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-amber-50 dark:bg-amber-900/20 text-amber-700 dark:text-amber-300 hover:bg-amber-100 dark:hover:bg-amber-900/40 disabled:opacity-40 transition-colors"
          title="Ouvrir un fichier Excel">
          {importing ? <Loader2 size={14} className="animate-spin" /> : <Upload size={14} />}
          Ouvrir Excel
        </button>

        <button onClick={handleExport} disabled={exporting}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-emerald-50 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-300 hover:bg-emerald-100 dark:hover:bg-emerald-900/40 disabled:opacity-40 transition-colors">
          {exporting ? <Loader2 size={14} className="animate-spin" /> : <Download size={14} />}
          Excel
        </button>
      </div>

      {/* FortuneSheet */}
      <div className="flex-1 overflow-hidden">
        {sheetData && sheetData.length > 0 ? (
          <Workbook key={workbookKey} data={sheetData} onChange={handleChange} />
        ) : (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <FileSpreadsheet className="w-12 h-12 text-gray-300 mx-auto mb-3" />
              <p className="text-sm text-gray-500">Aucune donnee disponible</p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
