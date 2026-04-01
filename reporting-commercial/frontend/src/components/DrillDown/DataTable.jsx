import { useState } from 'react'
import { ChevronUp, ChevronDown, ChevronLeft, ChevronRight } from 'lucide-react'

export default function DataTable({
  data = [],
  columns = [],
  onRowClick,
  sortable = true,
  pagination = true,
  pageSize = 10,
  clickable = false
}) {
  const [sortConfig, setSortConfig] = useState({ key: null, direction: 'asc' })
  const [currentPage, setCurrentPage] = useState(1)

  // Sorting
  const sortedData = [...data].sort((a, b) => {
    if (!sortConfig.key) return 0

    const aValue = a[sortConfig.key]
    const bValue = b[sortConfig.key]

    if (aValue === null || aValue === undefined) return 1
    if (bValue === null || bValue === undefined) return -1

    if (typeof aValue === 'number' && typeof bValue === 'number') {
      return sortConfig.direction === 'asc' ? aValue - bValue : bValue - aValue
    }

    const aStr = String(aValue).toLowerCase()
    const bStr = String(bValue).toLowerCase()
    return sortConfig.direction === 'asc'
      ? aStr.localeCompare(bStr)
      : bStr.localeCompare(aStr)
  })

  // Pagination
  const totalPages = Math.ceil(sortedData.length / pageSize)
  const startIndex = (currentPage - 1) * pageSize
  const paginatedData = pagination
    ? sortedData.slice(startIndex, startIndex + pageSize)
    : sortedData

  const handleSort = (key) => {
    if (!sortable) return
    setSortConfig((prev) => ({
      key,
      direction: prev.key === key && prev.direction === 'asc' ? 'desc' : 'asc'
    }))
  }

  const getSortIcon = (key) => {
    if (sortConfig.key !== key) return null
    return sortConfig.direction === 'asc'
      ? <ChevronUp className="w-4 h-4" />
      : <ChevronDown className="w-4 h-4" />
  }

  const formatValue = (value, format) => {
    if (value === null || value === undefined) return '-'

    switch (format) {
      case 'currency':
        return Number(value).toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
      case 'number':
        return Number(value).toLocaleString('fr-FR')
      case 'percent':
        return `${Number(value).toFixed(2)}%`
      case 'date':
        return new Date(value).toLocaleDateString('fr-FR')
      default:
        return value
    }
  }

  return (
    <div className="card overflow-hidden">
      <div className="overflow-x-auto border border-primary-300 dark:border-primary-600 rounded">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-primary-50 dark:bg-gray-700 border-b border-primary-300 dark:border-primary-600">
              {columns.map((col, index) => (
                <th
                  key={index}
                  onClick={() => col.sortable !== false && handleSort(col.key)}
                  className={`
                    px-3 py-2 text-xs font-semibold text-primary-700 dark:text-gray-300
                    whitespace-nowrap border-r border-primary-300 dark:border-primary-600 last:border-r-0
                    ${col.align === 'right' ? 'text-right' : 'text-left'}
                    ${sortable && col.sortable !== false ? 'cursor-pointer hover:bg-primary-100 dark:hover:bg-gray-600' : ''}
                  `}
                >
                  <div className={`flex items-center gap-1 ${col.align === 'right' ? 'justify-end' : ''}`}>
                    {col.header}
                    {getSortIcon(col.key)}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {paginatedData.length === 0 ? (
              <tr>
                <td
                  colSpan={columns.length}
                  className="px-3 py-8 text-center text-gray-500 dark:text-gray-400"
                >
                  Aucune donnee
                </td>
              </tr>
            ) : (
              paginatedData.map((row, rowIndex) => (
                <tr
                  key={rowIndex}
                  onClick={() => clickable && onRowClick && onRowClick(row)}
                  className={`
                    border-b border-primary-200 dark:border-gray-700 last:border-b-0
                    ${rowIndex % 2 === 0 ? 'bg-white dark:bg-gray-800' : 'bg-primary-50/50 dark:bg-gray-750'}
                    hover:bg-primary-100 dark:hover:bg-gray-700 transition-colors
                    ${clickable ? 'cursor-pointer' : ''}
                  `}
                >
                  {columns.map((col, colIndex) => (
                    <td
                      key={colIndex}
                      className={`
                        px-3 py-2 text-gray-900 dark:text-gray-100
                        border-r border-primary-200 dark:border-gray-700 last:border-r-0
                        ${col.align === 'right' ? 'text-right' : ''}
                        ${col.nowrap ? 'whitespace-nowrap' : ''}
                      `}
                    >
                      {col.render
                        ? col.render(row[col.key], row)
                        : formatValue(row[col.key], col.format)
                      }
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {pagination && totalPages > 1 && (
        <div className="flex items-center justify-between px-4 py-3 border-t border-gray-200 dark:border-gray-700">
          <div className="text-sm text-gray-500 dark:text-gray-400">
            {startIndex + 1} - {Math.min(startIndex + pageSize, data.length)} sur {data.length}
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              disabled={currentPage === 1}
              className="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-50"
            >
              <ChevronLeft className="w-5 h-5" />
            </button>
            <span className="text-sm text-gray-700 dark:text-gray-300">
              {currentPage} / {totalPages}
            </span>
            <button
              onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
              disabled={currentPage === totalPages}
              className="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-50"
            >
              <ChevronRight className="w-5 h-5" />
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
