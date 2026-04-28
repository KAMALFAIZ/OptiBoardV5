import { createContext, useContext, useState, useCallback } from 'react'

const DataSourceContext = createContext()

const STORAGE_KEY = 'dataSource'

export function DataSourceProvider({ children }) {
  const [dataSource, setDataSourceState] = useState(() => {
    try {
      return localStorage.getItem(STORAGE_KEY) || 'dwh'
    } catch {
      return 'dwh'
    }
  })

  const setDataSource = useCallback((value) => {
    const v = value === 'sage' ? 'sage' : 'dwh'
    setDataSourceState(v)
    try { localStorage.setItem(STORAGE_KEY, v) } catch { /* ignore */ }
  }, [])

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

export default DataSourceContext
