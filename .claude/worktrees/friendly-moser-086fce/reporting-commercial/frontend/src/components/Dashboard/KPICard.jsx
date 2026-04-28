import { TrendingUp, TrendingDown, Minus } from 'lucide-react'
import { useSettings } from '../../context/SettingsContext'

export default function KPICard({
  title,
  value,
  formattedValue,
  evolution,
  tendance,
  icon: Icon,
  color = 'primary',
  onClick,
  clickable = false
}) {
  const colorStyles = {
    primary: { backgroundColor: 'var(--color-primary-500)' },
    green: { backgroundColor: '#10b981' },
    yellow: { backgroundColor: '#f59e0b' },
    red: { backgroundColor: '#ef4444' },
    blue: { backgroundColor: '#3b82f6' },
    purple: { backgroundColor: '#8b5cf6' }
  }

  const getTendanceIcon = () => {
    if (tendance === 'hausse') return <TrendingUp className="w-3 h-3 text-emerald-500" />
    if (tendance === 'baisse') return <TrendingDown className="w-3 h-3 text-red-500" />
    return <Minus className="w-3 h-3 text-gray-400" />
  }

  const getTendanceColor = () => {
    if (tendance === 'hausse') return 'text-emerald-500'
    if (tendance === 'baisse') return 'text-red-500'
    return 'text-gray-500'
  }

  const { formatNumber, settings } = useSettings()

  // Utiliser les paramètres pour formater la valeur
  const displayValue = value !== undefined && value !== null
    ? formatNumber(value, { showCurrency: false })
    : (formattedValue || '-').replace(/\s*MAD\s*/gi, '')

  return (
    <div
      onClick={clickable && onClick ? onClick : undefined}
      className={`
        card p-3
        ${clickable ? 'cursor-pointer hover:shadow-md hover:border-primary-400 transition-all' : ''}
      `}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <p className="text-xs font-medium text-gray-500 dark:text-gray-400 truncate">{title}</p>
          <p className="mt-1 text-lg font-bold text-gray-900 dark:text-white truncate">
            {displayValue}
          </p>

          {evolution !== undefined && (
            <div className="mt-1 flex items-center gap-1">
              {getTendanceIcon()}
              <span className={`text-xs font-medium ${getTendanceColor()}`}>
                {evolution > 0 ? '+' : ''}{evolution}%
              </span>
            </div>
          )}
        </div>

        {Icon && (
          <div className="p-1.5 rounded-md flex-shrink-0" style={colorStyles[color]}>
            <Icon className="w-4 h-4 text-white" />
          </div>
        )}
      </div>
    </div>
  )
}
