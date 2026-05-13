import { forwardRef, useImperativeHandle, useState, useEffect, useRef } from 'react'
import { useGridFilter } from 'ag-grid-react'

const OPERATORS = [
  { value: 'equals',   label: 'Égal à',             inputs: 1 },
  { value: 'notEqual', label: 'Différent de',        inputs: 1 },
  { value: 'gt',       label: 'Supérieur à',         inputs: 1 },
  { value: 'gte',      label: 'Supérieur ou égal à', inputs: 1 },
  { value: 'lt',       label: 'Inférieur à',         inputs: 1 },
  { value: 'lte',      label: 'Inférieur ou égal à', inputs: 1 },
  { value: 'between',  label: 'Entre',               inputs: 2 },
  { value: 'blank',    label: 'Est vide',            inputs: 0 },
  { value: 'notBlank', label: "N'est pas vide",      inputs: 0 },
]

function toNum(v) {
  if (v == null || v === '') return null
  const n = typeof v === 'number' ? v : parseFloat(String(v).replace(/\s/g, '').replace(',', '.'))
  return isNaN(n) ? null : n
}

function testOperator(op, cellNum, a, b) {
  if (op === 'blank')    return cellNum == null
  if (op === 'notBlank') return cellNum != null
  if (cellNum == null)   return false
  switch (op) {
    case 'equals':   return cellNum === a
    case 'notEqual': return cellNum !== a
    case 'gt':       return cellNum > a
    case 'gte':      return cellNum >= a
    case 'lt':       return cellNum < a
    case 'lte':      return cellNum <= a
    case 'between':  return a != null && b != null && cellNum >= a && cellNum <= b
    default:         return true
  }
}

function buildValues(api, colId) {
  const set = new Set()
  api.forEachNode(node => {
    if (!node.data) return
    const v = toNum(node.data[colId])
    if (v != null) set.add(v)
  })
  return [...set].sort((a, b) => a - b)
}

function fmtNum(n) {
  if (n == null) return ''
  return n.toLocaleString('fr-FR', { maximumFractionDigits: 4 })
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

const NumberFilter = forwardRef((props, ref) => {
  const colId = props.colDef?.field || props.column?.getColId?.()

  const allValuesRef = useRef([])
  const selRef       = useRef(new Set())
  const modeRef      = useRef('values')
  const opRef        = useRef('equals')
  const val1Ref      = useRef('')
  const val2Ref      = useRef('')
  const hidePopupRef = useRef(null)
  const prevModelRef = useRef(null)

  const [allValues, setAllValues] = useState([])
  const [sel, setSel]             = useState(new Set())
  const [search, setSearch]       = useState('')
  const [mode, setMode]           = useState('values')
  const [operator, setOperator]   = useState('equals')
  const [val1, setVal1]           = useState('')
  const [val2, setVal2]           = useState('')

  const updateSel  = (s) => { selRef.current = s;   setSel(new Set(s)) }
  const updateMode = (m) => { modeRef.current = m;  setMode(m) }
  const updateOp   = (o) => { opRef.current = o;    setOperator(o) }
  const updateV1   = (v) => { val1Ref.current = v;  setVal1(v) }
  const updateV2   = (v) => { val2Ref.current = v;  setVal2(v) }

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
      const inputs = OPERATORS.find(o => o.value === opRef.current)?.inputs ?? 1
      if (inputs === 0) return true
      return val1Ref.current.trim() !== ''
    }
    return allValuesRef.current.some(v => !selRef.current.has(v))
  }

  const buildModel = () => {
    if (!isActive()) return null
    return modeRef.current === 'condition'
      ? { filterType: 'numberCondition', operator: opRef.current, val1: val1Ref.current, val2: val2Ref.current }
      : { filterType: 'numberSet', values: [...selRef.current] }
  }

  useGridFilter({
    doesFilterPass(params) {
      const cellNum = toNum(params.data?.[colId])
      if (modeRef.current === 'condition') {
        const inputs = OPERATORS.find(o => o.value === opRef.current)?.inputs ?? 1
        if (inputs > 0 && val1Ref.current.trim() === '') return true
        return testOperator(opRef.current, cellNum, toNum(val1Ref.current), toNum(val2Ref.current))
      }
      return selRef.current.has(cellNum)
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
        updateSel(new Set(allValuesRef.current)); updateMode('values')
        updateOp('equals'); updateV1(''); updateV2('')
        return
      }
      if (model.filterType === 'numberCondition') {
        updateMode('condition'); updateOp(model.operator || 'equals')
        updateV1(model.val1 || ''); updateV2(model.val2 || '')
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
  }), [allValues, sel, mode, operator, val1, val2])

  const q = search.trim()
  const visible = allValues.filter(v => !q || fmtNum(v).includes(q) || String(v).includes(q))
  const selCount = visible.filter(v => sel.has(v)).length
  const globalState = selCount === 0 ? 'none' : selCount === visible.length ? 'all' : 'some'

  const handleAll = (checked) => {
    const next = new Set(sel)
    visible.forEach(v => checked ? next.add(v) : next.delete(v))
    updateSel(next)
  }
  const handleOne = (v, checked) => {
    const next = new Set(sel); checked ? next.add(v) : next.delete(v); updateSel(next)
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

  const opDef = OPERATORS.find(o => o.value === operator) || OPERATORS[0]
  const preview = (() => {
    if (opDef.inputs === 0) return opDef.label
    if (!val1) return opDef.label
    if (opDef.inputs === 2 && val2) return `${val1} ≤ valeur ≤ ${val2}`
    return `${opDef.label} ${val1}`
  })()

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
          <div style={{ position: 'relative' }}>
            <span style={{ position: 'absolute', left: 8, top: '50%', transform: 'translateY(-50%)', color: '#bbb', fontSize: 13 }}>🔍</span>
            <input value={search} onChange={e => setSearch(e.target.value)}
              placeholder="Rechercher..."
              style={inputStyle}
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
                <span style={{ textAlign: 'right', flex: 1, fontVariantNumeric: 'tabular-nums' }}>{fmtNum(v)}</span>
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
          {opDef.inputs >= 1 && (
            <input type="number" value={val1} onChange={e => updateV1(e.target.value)}
              placeholder={opDef.inputs === 2 ? 'Valeur min' : 'Valeur'}
              style={{ ...inputStyle, paddingLeft: 10, textAlign: 'right' }}
            />
          )}
          {opDef.inputs === 2 && (
            <>
              <div style={{ textAlign: 'center', fontSize: 12, color: '#888' }}>et</div>
              <input type="number" value={val2} onChange={e => updateV2(e.target.value)}
                placeholder="Valeur max"
                style={{ ...inputStyle, paddingLeft: 10, textAlign: 'right' }}
              />
            </>
          )}
          <div style={{ fontSize: 11, color: '#888', fontStyle: 'italic', minHeight: 16 }}>{preview}</div>
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

NumberFilter.displayName = 'NumberFilter'
export default NumberFilter

const wrapStyle   = { padding: '12px', minWidth: '240px', maxWidth: '300px', display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '13px', fontFamily: 'inherit', background: '#fff', userSelect: 'none' }
const tabBtn      = { flex: 1, padding: '6px 4px', background: 'none', border: 'none', cursor: 'pointer', fontSize: 12, transition: 'color .15s' }
const rowStyle    = { display: 'flex', alignItems: 'center', gap: 8, padding: '4px 6px', cursor: 'pointer', borderRadius: 3 }
const inputStyle  = { width: '100%', padding: '5px 8px 5px 28px', border: '1px solid #d5d5d5', borderRadius: 4, fontSize: 12, outline: 'none', boxSizing: 'border-box' }
const selectStyle = { width: '100%', padding: '6px 8px', border: '1px solid #d5d5d5', borderRadius: 4, fontSize: 13, background: '#fff', cursor: 'pointer', outline: 'none' }
const btnCancel   = { flex: 1, padding: '6px 0', border: '1px solid #ccc', borderRadius: 4, background: '#fff', cursor: 'pointer', fontSize: 13 }
const btnApply    = { flex: 1, padding: '6px 0', border: 'none', borderRadius: 4, background: '#1976d2', color: '#fff', cursor: 'pointer', fontSize: 13 }
