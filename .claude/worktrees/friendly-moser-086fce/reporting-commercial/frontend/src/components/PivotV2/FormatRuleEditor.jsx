import { useState } from 'react'
import { X, Plus, Palette } from 'lucide-react'

const RULE_TYPES = [
  { value: 'heatmap', label: 'Heatmap', desc: 'Gradient 2 couleurs (min -> max)' },
  { value: 'data_bars', label: 'Barres de donnees', desc: 'Barre proportionnelle dans la cellule' },
  { value: 'icons', label: 'Icones', desc: 'Fleches haut/bas/neutre' },
  { value: 'thresholds', label: 'Seuils', desc: '3 niveaux avec couleurs personnalisees' },
  { value: 'negative_red', label: 'Negatifs en rouge', desc: 'Colore les valeurs negatives' },
]

const DEFAULT_CONFIGS = {
  heatmap: { colorMin: '#ef4444', colorMax: '#22c55e' },
  data_bars: { color: '#3b82f6', maxWidth: 100 },
  icons: { positiveThreshold: 0, negativeThreshold: 0 },
  thresholds: {
    levels: [
      { max: 0, color: '#ef4444', label: 'Bas' },
      { max: 50, color: '#f59e0b', label: 'Moyen' },
      { max: Infinity, color: '#22c55e', label: 'Haut' },
    ]
  },
  negative_red: { color: '#ef4444' },
}

function RuleItem({ rule, valueFields = [], onChange, onRemove }) {
  const handleChange = (key, value) => {
    onChange?.({ ...rule, [key]: value })
  }

  const handleConfigChange = (key, value) => {
    onChange?.({ ...rule, config: { ...rule.config, [key]: value } })
  }

  return (
    <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-3 space-y-3">
      <div className="flex items-center gap-3">
        <Palette size={16} className="text-gray-400 flex-shrink-0" />

        {/* Champ cible */}
        <select
          value={rule.field || ''}
          onChange={(e) => handleChange('field', e.target.value)}
          className="text-sm bg-gray-50 dark:bg-gray-700 border border-primary-300 dark:border-primary-600 rounded px-2 py-1.5 focus:ring-2 focus:ring-blue-500 outline-none"
        >
          <option value="">Choisir un champ...</option>
          {valueFields.map(vf => (
            <option key={vf.field} value={vf.field}>{vf.label || vf.field}</option>
          ))}
        </select>

        {/* Type de regle */}
        <select
          value={rule.type || 'heatmap'}
          onChange={(e) => {
            const newType = e.target.value
            handleChange('type', newType)
            handleChange('config', DEFAULT_CONFIGS[newType] || {})
          }}
          className="text-sm bg-gray-50 dark:bg-gray-700 border border-primary-300 dark:border-primary-600 rounded px-2 py-1.5 focus:ring-2 focus:ring-blue-500 outline-none"
        >
          {RULE_TYPES.map(rt => (
            <option key={rt.value} value={rt.value}>{rt.label}</option>
          ))}
        </select>

        <button
          onClick={onRemove}
          className="ml-auto p-1 text-gray-400 hover:text-red-500 transition-colors"
        >
          <X size={16} />
        </button>
      </div>

      {/* Config specifique au type */}
      {rule.type === 'heatmap' && (
        <div className="flex items-center gap-3 pl-7">
          <div className="flex items-center gap-2">
            <span className="text-xs text-gray-500">Min:</span>
            <input
              type="color"
              value={rule.config?.colorMin || '#ef4444'}
              onChange={(e) => handleConfigChange('colorMin', e.target.value)}
              className="w-8 h-8 rounded cursor-pointer border-0"
            />
          </div>
          <div className="flex-1 h-3 rounded-full bg-gradient-to-r"
            style={{
              backgroundImage: `linear-gradient(to right, ${rule.config?.colorMin || '#ef4444'}, ${rule.config?.colorMax || '#22c55e'})`
            }}
          />
          <div className="flex items-center gap-2">
            <span className="text-xs text-gray-500">Max:</span>
            <input
              type="color"
              value={rule.config?.colorMax || '#22c55e'}
              onChange={(e) => handleConfigChange('colorMax', e.target.value)}
              className="w-8 h-8 rounded cursor-pointer border-0"
            />
          </div>
        </div>
      )}

      {rule.type === 'thresholds' && (
        <div className="pl-7 space-y-2">
          {(rule.config?.levels || []).map((level, i) => (
            <div key={i} className="flex items-center gap-2">
              <input
                type="color"
                value={level.color}
                onChange={(e) => {
                  const newLevels = [...(rule.config?.levels || [])]
                  newLevels[i] = { ...newLevels[i], color: e.target.value }
                  handleConfigChange('levels', newLevels)
                }}
                className="w-6 h-6 rounded cursor-pointer border-0"
              />
              <span className="text-xs text-gray-500 w-8">{i === 0 ? '<' : i === 2 ? '>' : ''}</span>
              {i < 2 && (
                <input
                  type="number"
                  value={level.max === Infinity ? '' : level.max}
                  onChange={(e) => {
                    const newLevels = [...(rule.config?.levels || [])]
                    newLevels[i] = { ...newLevels[i], max: parseFloat(e.target.value) || 0 }
                    handleConfigChange('levels', newLevels)
                  }}
                  placeholder="Seuil"
                  className="w-24 text-sm bg-gray-50 dark:bg-gray-700 border border-primary-300 dark:border-primary-600 rounded px-2 py-1 focus:ring-2 focus:ring-blue-500 outline-none"
                />
              )}
              <input
                type="text"
                value={level.label || ''}
                onChange={(e) => {
                  const newLevels = [...(rule.config?.levels || [])]
                  newLevels[i] = { ...newLevels[i], label: e.target.value }
                  handleConfigChange('levels', newLevels)
                }}
                placeholder="Label"
                className="w-20 text-sm bg-gray-50 dark:bg-gray-700 border border-primary-300 dark:border-primary-600 rounded px-2 py-1 focus:ring-2 focus:ring-blue-500 outline-none"
              />
            </div>
          ))}
        </div>
      )}

      {rule.type === 'data_bars' && (
        <div className="flex items-center gap-3 pl-7">
          <span className="text-xs text-gray-500">Couleur:</span>
          <input
            type="color"
            value={rule.config?.color || '#3b82f6'}
            onChange={(e) => handleConfigChange('color', e.target.value)}
            className="w-8 h-8 rounded cursor-pointer border-0"
          />
          <div className="flex-1 bg-gray-100 dark:bg-gray-700 rounded-full h-3 overflow-hidden">
            <div
              className="h-full rounded-full transition-all"
              style={{ width: '65%', backgroundColor: rule.config?.color || '#3b82f6' }}
            />
          </div>
        </div>
      )}
    </div>
  )
}

export default function FormatRuleEditor({
  rules = [],
  valueFields = [],
  onChange,
  className = '',
}) {
  const handleAdd = () => {
    const newRule = {
      field: valueFields[0]?.field || '',
      type: 'heatmap',
      config: DEFAULT_CONFIGS.heatmap,
    }
    onChange?.([...rules, newRule])
  }

  const handleRuleChange = (index, updatedRule) => {
    const newRules = [...rules]
    newRules[index] = updatedRule
    onChange?.(newRules)
  }

  const handleRemove = (index) => {
    onChange?.(rules.filter((_, i) => i !== index))
  }

  return (
    <div className={`space-y-3 ${className}`}>
      {rules.map((rule, i) => (
        <RuleItem
          key={i}
          rule={rule}
          valueFields={valueFields}
          onChange={(r) => handleRuleChange(i, r)}
          onRemove={() => handleRemove(i)}
        />
      ))}

      <button
        onClick={handleAdd}
        className="flex items-center gap-2 w-full px-3 py-2 text-sm text-gray-500 dark:text-gray-400 border border-dashed border-primary-300 dark:border-primary-600 rounded-lg hover:border-blue-400 hover:text-blue-500 transition-colors"
      >
        <Plus size={16} />
        Ajouter une regle de formatage
      </button>
    </div>
  )
}
