import { createContext, useContext, useState, useCallback, useEffect } from 'react'
import { useDWH } from './DWHContext'

const DataSourceContext = createContext()

export function DataSourceProvider({ children }) {
  const { currentDWH } = useDWH()

  const [dataSource, setDataSourceState] = useState(() => {
    try {
      // Migration : supprimer l'ancienne clé globale 'dataSource' qui pouvait rester sur 'sage'
      localStorage.removeItem('dataSource')
      const dwhCode = JSON.parse(localStorage.getItem('currentDWH') || 'null')?.code
      if (dwhCode) {
        return localStorage.getItem(`dataSource_${dwhCode}`) || 'dwh'
      }
      return 'dwh'
    } catch {
      return 'dwh'
    }
  })

  // Migration au montage : force 'dwh' si aucune clé per-DWH n'est définie
  useEffect(() => {
    try { localStorage.removeItem('dataSource') } catch { /* ignore */ }
    const dwhCode = currentDWH?.code
    if (dwhCode) {
      const saved = localStorage.getItem(`dataSource_${dwhCode}`)
      setDataSourceState(saved || 'dwh')
    } else {
      setDataSourceState('dwh')
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // Sync quand le DWH actif change
  useEffect(() => {
    if (currentDWH?.code) {
      const saved = localStorage.getItem(`dataSource_${currentDWH.code}`) || 'dwh'
      setDataSourceState(saved)
    }
  }, [currentDWH?.code])

  const setDataSource = useCallback((value, dwhCode) => {
    const v = value === 'sage' ? 'sage' : 'dwh'
    const code = dwhCode || currentDWH?.code
    setDataSourceState(v)
    try {
      if (code) localStorage.setItem(`dataSource_${code}`, v)
    } catch { /* ignore */ }
  }, [currentDWH?.code])

  const toggleDataSource = useCallback(() => {
    setDataSource(dataSource === 'dwh' ? 'sage' : 'dwh')
  }, [dataSource, setDataSource])

  const isSageDirect = dataSource === 'sage'

  return (
    <DataSourceContext.Provider value={{ dataSource, setDataSource, toggleDataSource, isSageDirect }}>
      {children}
    </DataSourceContext.Provider>
  )
}

export function useDataSource() {
  const ctx = useContext(DataSourceContext)
  if (!ctx) throw new Error('useDataSource must be used within DataSourceProvider')
  return ctx
}

export function getDWHDataSource(dwhCode) {
  try { return localStorage.getItem(`dataSource_${dwhCode}`) || 'dwh' } catch { return 'dwh' }
}

export function setDWHDataSource(dwhCode, value) {
  try { localStorage.setItem(`dataSource_${dwhCode}`, value === 'sage' ? 'sage' : 'dwh') } catch { /* ignore */ }
}

export default DataSourceContext
