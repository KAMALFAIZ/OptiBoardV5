import { forwardRef, useImperativeHandle, useState, useEffect, useRef } from 'react'
import { useGridFilter } from 'ag-grid-react'

// ─── Opérateurs texte ─────────────────────────────────────────────────────────
const OPERATORS = [
  { value: 'contains',    label: 'Contient' },
  { value: 'notContains', label: 'Ne contient pas' },
  { value: 'equals',      label: 'Égal à' },
  { value: 'notEqual',    label: 'Différent de' },
  { value: 'startsWith',  label: 'Commence par' },
  { value: 'endsWith',    label: 'Finit par' },
  { value: 'blank',       label: 'Est vide' },
  { value: 'notBlank',    label: "N'est pas vide" },
]

function testOperator(op, cellStr, filterStr) {
  const c = cellStr.toLowerCase()
  const f = filterStr.toLowerCase()
  switch (op) {
    case 'contains':    return c.includes(f)
    case 'notContains': return !c.includes(f)
    case 'equals':      return c === f
    case 'notEqual':    return c !== f
    case 'startsWith':  return c.startsWith(f)
    case 'endsWith':    return c.endsWith(f)
    case 'blank':       return cellStr.trim() === ''
    case 'notBlank':    return cellStr.trim() !== ''
    default:            return true
  }
}

function buildValues(api, colId) {
  const set = new Set()
  api.forEachNode(node => {
    if (!node.data) return
    const v = node.data[colId]
    if (v != null && v !== '') set.add(String(v))
  })
  return [...set].sort((a, b) => a.localeCompare(b, 'fr', { sensitivity: 'base' }))
}

function Cbx({ state, onChange }) {
  const ref = useRef(null)
  useEffect(() => { if (ref.current) ref.current.indeterminate = state === 'some' }, [state])
  return (
    <input ref={ref} type="checkbox"
      checked={state === 'all'}
      onChange={e => onChange(e.target.checked)}
      style={{ cursor: 'pointer', margin: 0, accentColor: '#1976d2', flexShrink: 0 }}
    />
  )
}

const SetValueFilter = forwardRef((props, ref) => {
  const colId = props.colDef?.field || props.column?.getColId?.()

  const allValuesRef = useRef([])
  const selRef       = useRef(new Set())
  const modeRef      = useRef('values')
  const opRef        = useRef('contains')
  const filterValRef = useRef('')
  const hidePopupRef  = useRef(null)
  const prevModelRef  = useRef(null)

  const [allValues, setAllValues] = useState([])
  const [sel, setSel]             = useState(new Set())
  const [search, setSearch]       = useState('')
  const [mode, setMode]           = useState('values')
  const [operator, setOperator]   = useState('contains')
  const [filterVal, setFilterVal] = useState('')

  const updateSel  = (s) => { selRef.current = s;        setSel(new Set(s)) }
  const updateMode = (m) => { modeRef.current = m;       setMode(m) }
  const updateOp   = (o) => { opRef.current = o;         setOperator(o) }
  const updateFV   = (v) => { filterValRef.current = v;  setFilterVal(v) }

  useEffect(() => {
    const vals = buildValues(props.api, colId)
    allValuesRef.current = vals
    const s = new Set(vals)
    selRef.current = s
    setAllValues(vals)
    setSel(new Set(vals))
  }, [])

  const isActive = () => {
    if (modeRef.current === 'condition') {
      const op = opRef.current
      if (op === 'blank' || op === 'notBlank') return true
      return filterValRef.current.trim() !== ''
    }
    return allValuesRef.current.some(v => !selRef.current.has(v))
  }

  const buildModel = () => {
    if (!isActive()) return null
    return modeRef.current === 'condition'
      ? { filterType: 'condition', operator: opRef.current, value: filterValRef.current }
      : { filterType: 'set', values: [...selRef.current] }
  }

  useGridFilter({
    doesFilterPass(params) {
      const raw = params.data?.[colId]
      const cellStr = raw == null ? '' : String(raw)
      if (modeRef.current === 'condition') {
        const op = opRef.current
        const needs = op === 'blank' || op === 'notBlank'
        if (!needs && filterValRef.current.trim() === '') return true
        return testOperator(op, cellStr, filterValRef.current)
      }
      return selRef.current.has(cellStr)
    }
  })

  useImperativeHandle(ref, () => ({
    afterGuiAttached(params) {
      if (params?.hidePopup) hidePopupRef.current = params.hidePopup
      prevModelRef.current = buildModel()
    },
    isFilterActive: isActive,
    getModel: buildModel,
    setModel(model) {
      if (!model) {
        updateSel(new Set(allValuesRef.current))
        updateMode('values'); updateOp('contains'); updateFV('')
        return
      }
      if (model.filterType === 'condition') {
        updateMode('condition')
        updateOp(model.operator || 'contains')
        updateFV(model.value || '')
      } else {
        updateMode('values')
        updateSel(new Set(model.values || allValuesRef.current))
      }
    },
    onNewRowsLoaded() {
      const vals = buildValues(props.api, colId)
      allValuesRef.current = vals
      setAllValues(vals)
      const next = new Set(selRef.current)
      vals.forEach(v => { if (!next.has(v)) next.add(v) })
      updateSel(next)
    }
  }), [allValues, sel, mode, operator, filterVal])

  const q = search.toLowerCase()
  const visible = allValues.filter(v => !q || v.toLowerCase().includes(q))
  const selCount = visible.filter(v => sel.has(v)).length
  const globalState = selCount === 0 ? 'none' : selCount === visible.length ? 'all' : 'some'

  const handleAll = (checked) => {
    const next = new Set(sel)
    visible.forEach(v => checked ? next.add(v) : next.delete(v))
    updateSel(next)
  }
  const handleOne = (v, checked) => {
    const next = new Set(sel)
    checked ? next.add(v) : next.delete(v)
    updateSel(next)
  }

  const applyFilter = () => {
    const model = buildModel()
    props.onModelChange?.(model)
    props.filterChangedCallback?.()
    hidePopupRef.current?.()
  }
  const cancelFilter = () => {
    props.onModelChange?.(prevModelRef.current ?? null)
    hidePopupRef.current?.()
  }
  const needsInput   = operator !== 'blank' && operator !== 'notBlank'

  return (
    <div style={wrapStyle}>
      <div style={{ fontWeight: 600, fontSize: 14, marginBottom: 2 }}>Filtrer</div>

      {/* Onglets */}
      <div style={{ display: 'flex', borderBottom: '1px solid #e0e0e0', marginBottom: 4 }}>
        {['values', 'condition'].map(m => (
          <button key={m} onClick={() => updateMode(m)} style={{
            ...tabBtn,
            borderBottom: mode === m ? '2px solid #1976d2' : '2px solid transparent',
            color: mode === m ? '#1976d2' : '#666',
            fontWeight: mode === m ? 600 : 400,
          }}>
            {m === 'values' ? 'Valeurs' : 'Condition'}
          </button>
        ))}
      </div>

      {/* ── MODE VALEURS ── */}
      {mode === 'values' && (
        <>
          <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
            <span style={{ position: 'absolute', left: 8, color: '#bbb', fontSize: 13 }}>🔍</span>
            <input value={search} onChange={e => setSearch(e.target.value)}
              placeholder="Rechercher..."
              style={searchInput}
            />
          </div>
          <div style={{ overflowY: 'auto', maxHeight: 220, display: 'flex', flexDirection: 'column' }}>
            <label style={rowStyle}>
              <Cbx state={globalState} onChange={handleAll} />
              <span style={{ fontWeight: 500 }}>Tout sélectionner</span>
            </label>
            {visible.map(v => (
              <label key={v} style={rowStyle}
                onMouseEnter={e => e.currentTarget.style.background = '#f5f5f5'}
                onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
              >
                <Cbx state={sel.has(v) ? 'all' : 'none'} onChange={c => handleOne(v, c)} />
                <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{v}</span>
              </label>
            ))}
            {visible.length === 0 && (
              <div style={{ color: '#aaa', fontSize: 12, padding: '8px 4px' }}>Aucun résultat</div>
            )}
          </div>
        </>
      )}

      {/* ── MODE CONDITION ── */}
      {mode === 'condition' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8, paddingTop: 4 }}>
          <select value={operator} onChange={e => updateOp(e.target.value)} style={selectStyle}>
            {OPERATORS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
          {needsInput && (
            <input value={filterVal} onChange={e => updateFV(e.target.value)}
              placeholder="Valeur..."
              style={{ ...searchInput, paddingLeft: 10 }}
            />
          )}
          <div style={{ fontSize: 11, color: '#888', fontStyle: 'italic' }}>
            {OPERATORS.find(o => o.value === operator)?.label}
            {needsInput && filterVal ? ` : "${filterVal}"` : ''}
          </div>
        </div>
      )}

      {/* Boutons */}
      <div style={{ display: 'flex', gap: 8, borderTop: '1px solid #eee', paddingTop: 8, marginTop: 4 }}>
        <button onClick={cancelFilter} style={btnCancel}>Annuler</button>
        <button onClick={applyFilter}  style={btnApply}>Appliquer</button>
      </div>
    </div>
  )
})

SetValueFilter.displayName = 'SetValueFilter'
export default SetValueFilter

const wrapStyle   = { padding: '12px', minWidth: '240px', maxWidth: '310px', display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '13px', fontFamily: 'inherit', background: '#fff', userSelect: 'none' }
const tabBtn      = { flex: 1, padding: '6px 4px', background: 'none', border: 'none', cursor: 'pointer', fontSize: 12, transition: 'color .15s' }
const rowStyle    = { display: 'flex', alignItems: 'center', gap: 8, padding: '4px 6px', cursor: 'pointer', borderRadius: 3 }
const searchInput = { width: '100%', padding: '5px 8px 5px 28px', border: '1px solid #d5d5d5', borderRadius: 4, fontSize: 12, outline: 'none', boxSizing: 'border-box' }
const selectStyle = { width: '100%', padding: '6px 8px', border: '1px solid #d5d5d5', borderRadius: 4, fontSize: 13, background: '#fff', cursor: 'pointer', outline: 'none' }
const btnCancel   = { flex: 1, padding: '6px 0', border: '1px solid #ccc', borderRadius: 4, background: '#fff', cursor: 'pointer', fontSize: 13 }
const btnApply    = { flex: 1, padding: '6px 0', border: 'none', borderRadius: 4, background: '#1976d2', color: '#fff', cursor: 'pointer', fontSize: 13 }
