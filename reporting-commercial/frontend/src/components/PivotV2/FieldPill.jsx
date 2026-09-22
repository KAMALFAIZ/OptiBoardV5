import { GripVertical, X, Type, Hash, Calendar, Check, SlidersHorizontal } from 'lucide-react'

const typeIcons = {
  text: Type,
  number: Hash,
  date: Calendar,
}

// Pastille d'icone colorée par type (le corps de la pastille reste neutre)
const typeBadge = {
  text: 'bg-sky-100 text-sky-700 dark:bg-sky-900/40 dark:text-sky-300',
  number: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300',
  date: 'bg-violet-100 text-violet-700 dark:bg-violet-900/40 dark:text-violet-300',
}

export default function FieldPill({
  field,
  type = 'text',
  label,
  badge,
  draggable = true,
  removable = false,
  used = false,
  onRemove,
  onSettings,
  onDragStart,
  onDragEnd,
  className = '',
  compact = false,
  block = false,
}) {
  const Icon = typeIcons[type] || Type
  const badgeClass = typeBadge[type] || typeBadge.text
  const displayLabel = label || field

  return (
    <div
      draggable={draggable}
      onDragStart={(e) => {
        e.dataTransfer.setData('text/plain', JSON.stringify({ field, type, label: displayLabel }))
        e.dataTransfer.effectAllowed = 'move'
        onDragStart?.(e)
      }}
      onDragEnd={onDragEnd}
      title={displayLabel}
      className={`
        group flex items-center gap-2 min-w-0 rounded-md select-none
        bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700
        ${draggable ? 'cursor-grab active:cursor-grabbing' : ''}
        hover:border-primary-300 dark:hover:border-primary-600 hover:shadow-sm
        transition-all duration-150
        ${compact ? 'h-7 pl-1 pr-1.5 text-xs' : 'h-8 pl-1.5 pr-2 text-sm'}
        ${block ? 'w-full' : ''}
        ${className}
      `}
    >
      {draggable && (
        <GripVertical size={12} className="flex-shrink-0 text-gray-300 group-hover:text-gray-400 dark:text-gray-600" />
      )}
      <span className={`flex items-center justify-center w-5 h-5 rounded flex-shrink-0 ${badgeClass}`}>
        <Icon size={11} strokeWidth={2.5} />
      </span>
      <span className={`truncate font-medium ${used ? 'text-gray-400 dark:text-gray-500' : 'text-gray-700 dark:text-gray-200'}`}>
        {displayLabel}
      </span>
      {badge && (
        <span className="flex-shrink-0 px-1.5 py-px rounded text-[10px] font-semibold uppercase tracking-wide bg-gray-100 text-gray-500 dark:bg-gray-700 dark:text-gray-300">
          {badge}
        </span>
      )}
      {used && <Check size={13} className="ml-auto flex-shrink-0 text-primary-500" />}
      {(onSettings || (removable && onRemove)) && (
        <span className="ml-auto flex items-center gap-0.5 pl-1 flex-shrink-0">
          {onSettings && (
            <button
              type="button"
              onClick={(e) => { e.stopPropagation(); onSettings(e) }}
              className="p-0.5 rounded text-gray-400 hover:text-primary-600 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
              title="Paramètres du champ"
            >
              <SlidersHorizontal size={12} />
            </button>
          )}
          {removable && onRemove && (
            <button
              type="button"
              onClick={(e) => { e.stopPropagation(); onRemove(field) }}
              className="p-0.5 rounded text-gray-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
              title="Retirer"
            >
              <X size={12} />
            </button>
          )}
        </span>
      )}
    </div>
  )
}
