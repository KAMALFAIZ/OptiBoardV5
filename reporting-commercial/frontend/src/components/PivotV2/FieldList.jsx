import { useState, useMemo } from 'react'
import { Search, Type, Hash, Calendar, ChevronDown, ChevronRight } from 'lucide-react'
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

  const toggleGroup = (key) => {
    setCollapsed(prev => ({ ...prev, [key]: !prev[key] }))
  }

  return (
    <div className={`flex flex-col h-full ${className}`}>
      {/* Barre de recherche */}
      <div className="relative mb-3">
        <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400" />
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Rechercher un champ..."
          className="w-full pl-8 pr-3 py-2 text-sm bg-white dark:bg-gray-800 border border-primary-300 dark:border-primary-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all"
        />
      </div>

      {/* Groupes de champs */}
      <div className="flex-1 overflow-y-auto space-y-1">
        {Object.entries(grouped).map(([key, group]) => {
          if (group.fields.length === 0) return null
          const isCollapsed = collapsed[key]
          const GroupIcon = group.icon

          return (
            <div key={key}>
              <button
                onClick={() => toggleGroup(key)}
                className="flex items-center gap-1.5 w-full px-2 py-1.5 text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition-colors rounded"
              >
                {isCollapsed ? <ChevronRight size={14} /> : <ChevronDown size={14} />}
                <GroupIcon size={14} />
                <span>{group.label}</span>
                <span className="ml-auto text-gray-400 font-normal">{group.fields.length}</span>
              </button>

              {!isCollapsed && (
                <div className="pl-2 space-y-1 pb-2 overflow-hidden">
                  {group.fields.map(f => {
                    const isUsed = usedSet.has(f.name)
                    return (
                      <div
                        key={f.name}
                        onDoubleClick={() => onFieldDoubleClick?.(f)}
                        className={isUsed ? 'opacity-60' : ''}
                      >
                        <FieldPill
                          field={f.name}
                          type={f.type}
                          draggable
                          compact
                        />
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          )
        })}

        {fields.length === 0 && (
          <div className="text-center py-8 text-sm text-gray-400 dark:text-gray-500">
            Selectionnez une source de donnees pour voir les champs disponibles
          </div>
        )}
      </div>
    </div>
  )
}
