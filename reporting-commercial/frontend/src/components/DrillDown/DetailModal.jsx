import { X, Download, ChevronLeft, ChevronRight } from 'lucide-react'
import { useState } from 'react'

export default function DetailModal({
  isOpen,
  onClose,
  title,
  breadcrumb = [],
  data = [],
  columns = [],
  total = 0,
  page = 1,
  pageSize = 50,
  onPageChange,
  onExport,
  loading = false
}) {
  // Fonction de formatage des valeurs
  const formatValue = (value, format, align) => {
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

  if (!isOpen) return null

  const totalPages = Math.ceil(total / pageSize)
  const hasNext = page < totalPages
  const hasPrevious = page > 1

  return (
    <div className="fixed inset-0 z-50 overflow-hidden">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="absolute inset-4 lg:inset-10 bg-white dark:bg-gray-800 rounded-xl shadow-xl flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-2 border-b border-gray-200 dark:border-gray-700">
          <div>
            {/* Breadcrumb */}
            {breadcrumb.length > 0 && (
              <div className="flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400">
                {breadcrumb.map((item, index) => (
                  <span key={index}>
                    {index > 0 && <span className="mx-1">/</span>}
                    {item}
                  </span>
                ))}
              </div>
            )}
            <h2 className="text-sm font-semibold text-gray-900 dark:text-white">
              {title}
            </h2>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              {total} resultat{total > 1 ? 's' : ''}
            </p>
          </div>

          <div className="flex items-center gap-2">
            {onExport && (
              <button
                onClick={onExport}
                className="btn-secondary btn-sm flex items-center gap-1"
              >
                <Download className="w-3 h-3" />
                Exporter
              </button>
            )}
            <button
              onClick={onClose}
              className="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto p-3">
          {loading ? (
            <div className="flex items-center justify-center h-full">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
            </div>
          ) : data.length === 0 ? (
            <div className="flex items-center justify-center h-full text-gray-500">
              Aucune donnee
            </div>
          ) : (
            <div className="overflow-x-auto border border-primary-300 dark:border-primary-600 rounded">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-primary-50 dark:bg-gray-700 border-b border-primary-300 dark:border-primary-600">
                    {columns.map((col, index) => (
                      <th
                        key={index}
                        className={`px-3 py-2 text-xs font-semibold text-primary-700 dark:text-gray-300 border-r border-primary-300 dark:border-primary-600 last:border-r-0 ${col.align === 'right' ? 'text-right' : 'text-left'}`}
                      >
                        {col.header}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {data.map((row, rowIndex) => (
                    <tr
                      key={rowIndex}
                      className={`
                        border-b border-primary-200 dark:border-gray-700 last:border-b-0
                        ${rowIndex % 2 === 0 ? 'bg-white dark:bg-gray-800' : 'bg-primary-50/50 dark:bg-gray-750'}
                        hover:bg-primary-100 dark:hover:bg-gray-700 transition-colors
                      `}
                    >
                      {columns.map((col, colIndex) => (
                        <td
                          key={colIndex}
                          className={`px-3 py-2 text-gray-900 dark:text-gray-100 border-r border-primary-200 dark:border-gray-700 last:border-r-0 ${col.align === 'right' ? 'text-right' : ''}`}
                        >
                          {col.render ? col.render(row[col.key], row) : formatValue(row[col.key], col.format)}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between px-6 py-4 border-t border-gray-200 dark:border-gray-700">
            <div className="text-sm text-gray-500 dark:text-gray-400">
              Page {page} sur {totalPages}
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => onPageChange(page - 1)}
                disabled={!hasPrevious}
                className="btn-secondary flex items-center gap-1 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <ChevronLeft className="w-4 h-4" style={{ color: 'var(--color-primary-500)' }} />
                Precedent
              </button>
              <button
                onClick={() => onPageChange(page + 1)}
                disabled={!hasNext}
                className="btn-secondary flex items-center gap-1 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Suivant
                <ChevronRight className="w-4 h-4" style={{ color: 'var(--color-primary-500)' }} />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
