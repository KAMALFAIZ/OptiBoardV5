import { useState, useMemo } from 'react'
import { Search, Type, Hash, Calendar, ChevronDown, X, Database } from 'lucide-react'
import FieldPill from './FieldPill'

export default function FieldList({
  fields = [],
  usedFields = [],
  onFieldDoubleClick,
  className = '',
}) {
  const [search, setSearch] = useState('')
  const [collapsed, setCollapsed] = useState({})

  // Grouper les champs par type
  const grouped = useMemo(() => {
    const groups = {
      dimensions: { label: 'Dimensions', icon: Type, fields: [] },
      mesures: { label: 'Mesures', icon: Hash, fields: [] },
      dates: { label: 'Temporel', icon: Calendar, fields: [] },
    }

    const filtered = fields.filter(f =>
      f.name.toLowerCase().includes(search.toLowerCase())
    )

    for (const f of filtered) {
      if (f.type === 'number') {
        groups.mesures.fields.push(f)
      } else if (f.type === 'date') {
        groups.dates.fields.push(f)
      } else {
        groups.dimensions.fields.push(f)
      }
    }

    return groups
  }, [fields, search])

  const usedSet = new Set(usedFields.map(f => f.field || f))
  const noMatch = fields.length > 0 && Object.values(grouped).every(g => g.fields.length === 0)

  const toggleGroup = (key) => {
    setCollapsed(prev => ({ ...prev, [key]: !prev[key] }))
  }

  return (
    <div className={`flex flex-col h-full min-h-0 ${className}`}>
      {/* Barre de recherche */}
      <div className="px-3 pt-3 pb-2"><div className="relative">
        <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Rechercher un champ…"
          className="w-full h-8 pl-8 pr-7 text-xs bg-gray-50 dark:bg-gray-900/40 border border-gray-200 dark:border-gray-700 rounded-md focus:bg-white dark:focus:bg-gray-800 focus:ring-2 focus:ring-primary-500/30 focus:border-primary-400 outline-none transition-all"
        />
        {search && (
          <button
            type="button"
            onClick={() => setSearch('')}
            className="absolute right-2 top-1/2 -translate-y-1/2 p-0.5 rounded text-gray-400 hover:text-gray-600"
            title="Effacer"
          >
            <X size={12} />
          </button>
        )}
      </div></div>

      {/* Groupes de champs */}
      <div className="flex-1 min-h-0 overflow-y-auto px-3 pb-3 space-y-2">
        {Object.entries(grouped).map(([key, group]) => {
          if (group.fields.length === 0) return null
          const isCollapsed = collapsed[key] && !search
          const GroupIcon = group.icon

          return (
            <div key={key}>
              <button
                type="button"
                onClick={() => toggleGroup(key)}
                className="sticky top-0 z-10 flex items-center gap-1.5 w-full py-1.5 bg-white dark:bg-gray-800 text-[11px] font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200 transition-colors"
              >
                <ChevronDown size={13} className={`transition-transform ${isCollapsed ? '-rotate-90' : ''}`} />
                <GroupIcon size={12} />
                <span>{group.label}</span>
                <span className="ml-auto min-w-[20px] px-1.5 rounded-full bg-gray-100 dark:bg-gray-700 text-[10px] font-semibold text-gray-500 dark:text-gray-300 text-center">
                  {group.fields.length}
                </span>
              </button>

              {!isCollapsed && (
                <div className="space-y-1 pt-1">
                  {group.fields.map(f => (
                    <div
                      key={f.name}
                      onDoubleClick={() => onFieldDoubleClick?.(f)}
                    >
                      <FieldPill
                        field={f.name}
                        type={f.type}
                        used={usedSet.has(f.name)}
                        draggable
                        compact
                        block
                      />
                    </div>
                  ))}
                </div>
              )}
            </div>
          )
        })}

        {noMatch && (
          <div className="text-center py-6 text-xs text-gray-400">
            Aucun champ ne correspond à « {search} »
          </div>
        )}

        {fields.length === 0 && (
          <div className="flex flex-col items-center text-center py-10 px-2 text-xs text-gray-400 dark:text-gray-500">
            <Database size={22} className="mb-2 text-gray-300 dark:text-gray-600" />
            Sélectionnez une source de données pour voir les champs disponibles
          </div>
        )}
      </div>

      {fields.length > 0 && (
        <div className="px-3 py-2 border-t border-gray-100 dark:border-gray-700 text-[10px] text-gray-400 leading-snug">
          Glissez un champ vers une zone, ou double-cliquez pour l'ajouter en lignes.
        </div>
      )}
    </div>
  )
}
