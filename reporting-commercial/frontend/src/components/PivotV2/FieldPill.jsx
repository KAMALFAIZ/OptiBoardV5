import { GripVertical, X, Type, Hash, Calendar } from 'lucide-react'

const typeIcons = {
  text: Type,
  number: Hash,
  date: Calendar,
}

const typeColors = {
  text: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300',
  number: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300',
  date: 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300',
}

export default function FieldPill({
  field,
  type = 'text',
  label,
  draggable = true,
  removable = false,
  onRemove,
  onDragStart,
  onDragEnd,
  className = '',
  compact = false,
}) {
  const Icon = typeIcons[type] || Type
  const colorClass = typeColors[type] || typeColors.text
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
      className={`
        flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-sm font-medium min-w-0
        border border-transparent cursor-grab active:cursor-grabbing
        transition-all duration-150 select-none
        ${colorClass}
        hover:shadow-sm hover:border-primary-300 dark:hover:border-gray-600
        ${compact ? 'px-2 py-1 text-xs' : ''}
        ${className}
      `}
    >
      {draggable && (
        <GripVertical size={compact ? 12 : 14} className="opacity-40 flex-shrink-0" />
      )}
      <Icon size={compact ? 12 : 14} className="flex-shrink-0 opacity-60" />
      <span className="truncate">{displayLabel}</span>
      {removable && onRemove && (
        <button
          onClick={(e) => {
            e.stopPropagation()
            onRemove(field)
          }}
          className="ml-0.5 p-0.5 rounded hover:bg-black/10 dark:hover:bg-white/10 transition-colors"
        >
          <X size={compact ? 12 : 14} />
        </button>
      )}
    </div>
  )
}
