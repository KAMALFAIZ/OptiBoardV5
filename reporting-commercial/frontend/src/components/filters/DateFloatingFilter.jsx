import { forwardRef, useImperativeHandle, useState } from 'react'

// Floating filter date : champ texte libre (jj/mm/aaaa ou aaaa ou mm/aaaa)
// Filtre les lignes dont la date formatée contient la saisie
const DateFloatingFilter = forwardRef((props, ref) => {
  const [value, setValue] = useState('')
  const colId = props.column?.getColId?.() || props.colDef?.field

  useImperativeHandle(ref, () => ({
    onParentModelChanged(parentModel) {
      // Si filtre posé depuis le popup arbre, on affiche une description courte
      if (!parentModel) { setValue(''); return }
      // On ne peut pas reconstruire la saisie depuis le modèle arbre → laisser vide
      setValue('')
    }
  }))

  const onChange = (e) => {
    const v = e.target.value
    setValue(v)

    if (v.trim() === '') {
      const all = { ...props.api.getFilterModel() }
      delete all[colId]
      props.api.setFilterModel(all)
      return
    }

    // Filtre maison : on parcourt les lignes et on sélectionne celles dont
    // la date formatée (jj/mm/aaaa) contient la saisie
    const matchingDates = new Set()
    props.api.forEachNode(node => {
      if (!node.data) return
      const raw = node.data[colId]
      if (!raw) return
      const d = new Date(raw)
      if (isNaN(d.getTime())) return
      const formatted = `${String(d.getDate()).padStart(2,'0')}/${String(d.getMonth()+1).padStart(2,'0')}/${d.getFullYear()}`
      if (formatted.includes(v.trim())) matchingDates.add(raw)
    })

    // Construire un modèle arbre qui ne contient que les dates correspondantes
    const tree = {}
    matchingDates.forEach(raw => {
      const d = new Date(raw)
      const y = String(d.getFullYear())
      const m = String(d.getMonth())
      const day = d.getDate()
      if (!tree[y]) tree[y] = {}
      if (!tree[y][m]) tree[y][m] = []
      if (!tree[y][m].includes(day)) tree[y][m].push(day)
    })

    const all = { ...props.api.getFilterModel() }
    if (Object.keys(tree).length === 0) {
      // Aucun résultat → on pose un modèle vide qui bloque tout
      all[colId] = { filterType: 'dateTree', selected: {} }
    } else {
      all[colId] = { filterType: 'dateTree', selected: tree }
    }
    props.api.setFilterModel(all)
  }

  const onClear = () => {
    setValue('')
    const all = { ...props.api.getFilterModel() }
    delete all[colId]
    props.api.setFilterModel(all)
  }

  return (
    <div style={{ display: 'flex', alignItems: 'center', width: '100%', padding: '0 2px', boxSizing: 'border-box' }}>
      <input
        value={value}
        onChange={onChange}
        placeholder="jj/mm/aaaa"
        style={inputStyle}
      />
      {value && (
        <span onClick={onClear} style={clearBtn} title="Effacer">✕</span>
      )}
    </div>
  )
})

DateFloatingFilter.displayName = 'DateFloatingFilter'
export default DateFloatingFilter

const inputStyle = {
  flex: 1, minWidth: 0, height: 22, padding: '1px 4px',
  border: '1px solid #d0d0d0', borderRadius: 3,
  fontSize: 11, outline: 'none', boxSizing: 'border-box',
  background: '#fff',
}
const clearBtn = {
  marginLeft: 3, cursor: 'pointer', color: '#999',
  fontSize: 10, flexShrink: 0, lineHeight: 1,
  userSelect: 'none',
}
