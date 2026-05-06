import { forwardRef, useImperativeHandle, useState, useEffect, useRef } from 'react'

const MONTHS_FR = [
  'Janvier','Février','Mars','Avril','Mai','Juin',
  'Juillet','Août','Septembre','Octobre','Novembre','Décembre'
]

function buildDateTree(api, colId) {
  const map = {}
  api.forEachNode(node => {
    if (!node.data) return
    const raw = node.data[colId]
    if (!raw) return
    const d = new Date(raw)
    if (isNaN(d.getTime())) return
    const y = String(d.getFullYear())
    const m = String(d.getMonth())
    const day = d.getDate()
    if (!map[y]) map[y] = {}
    if (!map[y][m]) map[y][m] = new Set()
    map[y][m].add(day)
  })
  const tree = {}
  Object.keys(map).sort().forEach(y => {
    tree[y] = {}
    Object.keys(map[y]).sort((a, b) => +a - +b).forEach(m => {
      tree[y][m] = [...map[y][m]].sort((a, b) => a - b)
    })
  })
  return tree
}

function cloneTree(tree) {
  const s = {}
  Object.keys(tree).forEach(y => {
    s[y] = {}
    Object.keys(tree[y]).forEach(m => { s[y][m] = [...tree[y][m]] })
  })
  return s
}

function emptyTree(tree) {
  const s = {}
  Object.keys(tree).forEach(y => {
    s[y] = {}
    Object.keys(tree[y]).forEach(m => { s[y][m] = [] })
  })
  return s
}

function isAllSelected(sel, tree) {
  for (const y of Object.keys(tree)) {
    for (const m of Object.keys(tree[y])) {
      if ((sel[y]?.[m] || []).length !== (tree[y][m] || []).length) return false
    }
  }
  return true
}

// 'all' | 'some' | 'none'
function yearState(sel, tree, y) {
  const months = Object.keys(tree[y] || {})
  if (!months.length) return 'none'
  const allFull = months.every(m => (sel[y]?.[m] || []).length === tree[y][m].length)
  const allEmpty = months.every(m => !(sel[y]?.[m] || []).length)
  return allFull ? 'all' : allEmpty ? 'none' : 'some'
}

function monthState(sel, tree, y, m) {
  const days = tree[y]?.[m] || []
  const n = (sel[y]?.[m] || []).length
  return n === days.length ? 'all' : n === 0 ? 'none' : 'some'
}

function allState(sel, tree) {
  const ys = Object.keys(tree)
  if (!ys.length) return 'all'
  const states = ys.map(y => yearState(sel, tree, y))
  return states.every(s => s === 'all') ? 'all' : states.every(s => s === 'none') ? 'none' : 'some'
}

// Checkbox with indeterminate support
function Cbx({ state, onChange }) {
  const ref = useRef(null)
  useEffect(() => {
    if (ref.current) ref.current.indeterminate = state === 'some'
  }, [state])
  return (
    <input
      ref={ref}
      type="checkbox"
      checked={state === 'all'}
      onChange={e => onChange(e.target.checked)}
      style={{ cursor: 'pointer', margin: 0, accentColor: '#1976d2' }}
    />
  )
}

const DateTreeFilter = forwardRef((props, ref) => {
  const colId = props.colDef?.field || props.column?.getColId?.()

  const treeRef      = useRef({})
  const selRef       = useRef({})
  const hidePopupRef = useRef(null)

  const [tree, setTree]         = useState({})
  const [sel, setSel]           = useState({})
  const [expanded, setExpanded] = useState({})
  const [search, setSearch]     = useState('')

  const updateSel = (next) => {
    selRef.current = next
    setSel(next)
  }

  useEffect(() => {
    const t = buildDateTree(props.api, colId)
    treeRef.current = t
    const s = cloneTree(t)
    selRef.current = s
    setTree(t)
    setSel(s)
    // Expand years by default
    const exp = {}
    Object.keys(t).forEach(y => { exp[y] = true })
    setExpanded(exp)
  }, [])

  useImperativeHandle(ref, () => ({
    afterGuiAttached(params) {
      if (params?.hidePopup) hidePopupRef.current = params.hidePopup
    },
    isFilterActive() {
      return !isAllSelected(selRef.current, treeRef.current)
    },
    doesFilterPass(params) {
      const raw = params.data?.[colId]
      if (!raw) return false
      const d = new Date(raw)
      if (isNaN(d.getTime())) return false
      const y = String(d.getFullYear())
      const m = String(d.getMonth())
      const day = d.getDate()
      return (selRef.current[y]?.[m] || []).includes(day)
    },
    getModel() {
      if (isAllSelected(selRef.current, treeRef.current)) return null
      return { filterType: 'dateTree', selected: selRef.current }
    },
    setModel(model) {
      const t = treeRef.current
      updateSel(model ? (model.selected || cloneTree(t)) : cloneTree(t))
    },
    onNewRowsLoaded() {
      const t = buildDateTree(props.api, colId)
      treeRef.current = t
      setTree(t)
      if (isAllSelected(selRef.current, t)) {
        updateSel(cloneTree(t))
      }
    }
  }), [tree, sel])

  // Handlers
  const handleAll = (v) => updateSel(v ? cloneTree(treeRef.current) : emptyTree(treeRef.current))

  const handleYear = (y, v) => {
    const next = { ...selRef.current }
    next[y] = {}
    Object.keys(treeRef.current[y] || {}).forEach(m => {
      next[y][m] = v ? [...treeRef.current[y][m]] : []
    })
    updateSel(next)
  }

  const handleMonth = (y, m, v) => {
    const next = { ...selRef.current, [y]: { ...selRef.current[y] } }
    next[y][m] = v ? [...treeRef.current[y][m]] : []
    updateSel(next)
  }

  const handleDay = (y, m, day, v) => {
    const next = { ...selRef.current, [y]: { ...selRef.current[y] } }
    const days = [...(selRef.current[y]?.[m] || [])]
    if (v) { if (!days.includes(day)) days.push(day) }
    else { const i = days.indexOf(day); if (i !== -1) days.splice(i, 1) }
    next[y][m] = days.sort((a, b) => a - b)
    updateSel(next)
  }

  const applyFilter  = () => { props.filterChangedCallback?.(); hidePopupRef.current?.() }
  const cancelFilter = () => { hidePopupRef.current?.() }

  // Search filter
  const q = search.toLowerCase()
  const visYears = Object.keys(tree).filter(y => {
    if (!q) return true
    if (y.includes(q)) return true
    return Object.keys(tree[y]).some(m => MONTHS_FR[+m].toLowerCase().includes(q))
  })

  const globalState = allState(sel, tree)

  return (
    <div style={{
      padding: '12px',
      minWidth: '230px',
      maxWidth: '280px',
      display: 'flex',
      flexDirection: 'column',
      gap: '8px',
      fontSize: '13px',
      fontFamily: 'inherit',
      background: '#fff',
      userSelect: 'none',
    }}>
      {/* Title */}
      <div style={{ fontWeight: 600, fontSize: '14px', marginBottom: 2 }}>Filtrer par date</div>

      {/* Search */}
      <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
        <span style={{ position: 'absolute', left: 8, color: '#bbb', fontSize: 13 }}>🔍</span>
        <input
          value={search}
          onChange={e => setSearch(e.target.value)}
          placeholder="Rechercher..."
          style={{
            width: '100%', padding: '5px 8px 5px 28px',
            border: '1px solid #d5d5d5', borderRadius: 4,
            fontSize: 12, outline: 'none', boxSizing: 'border-box',
          }}
        />
      </div>

      {/* Tree */}
      <div style={{ overflowY: 'auto', maxHeight: 230, display: 'flex', flexDirection: 'column' }}>
        {/* Select All */}
        <label style={rowStyle}>
          <span style={{ width: 16 }} />
          <Cbx state={globalState} onChange={handleAll} />
          <span style={{ fontWeight: 500 }}>Tout sélectionner</span>
        </label>

        {visYears.map(y => {
          const yExp = !!expanded[y]
          const ySt = yearState(sel, tree, y)
          const visMths = Object.keys(tree[y]).filter(m =>
            !q || y.includes(q) || MONTHS_FR[+m].toLowerCase().includes(q)
          )
          return (
            <div key={y}>
              {/* Year row */}
              <div style={rowStyle}>
                <span
                  onClick={() => setExpanded(p => ({ ...p, [y]: !p[y] }))}
                  style={chevronStyle}
                >
                  {yExp ? '▾' : '›'}
                </span>
                <label style={labelStyle}>
                  <Cbx state={ySt} onChange={v => handleYear(y, v)} />
                  <span>{y}</span>
                </label>
              </div>

              {/* Months */}
              {yExp && visMths.map(m => {
                const mKey = `${y}-${m}`
                const mExp = !!expanded[mKey]
                const mSt = monthState(sel, tree, y, m)
                return (
                  <div key={m} style={{ paddingLeft: 18 }}>
                    {/* Month row */}
                    <div style={rowStyle}>
                      <span
                        onClick={() => setExpanded(p => ({ ...p, [mKey]: !p[mKey] }))}
                        style={chevronStyle}
                      >
                        {mExp ? '▾' : '›'}
                      </span>
                      <label style={labelStyle}>
                        <Cbx state={mSt} onChange={v => handleMonth(y, m, v)} />
                        <span>{MONTHS_FR[+m]}</span>
                      </label>
                    </div>

                    {/* Days */}
                    {mExp && (tree[y][m] || []).map(day => (
                      <div key={day} style={{ ...rowStyle, paddingLeft: 36 }}>
                        <span style={{ width: 16 }} />
                        <label style={labelStyle}>
                          <Cbx
                            state={(sel[y]?.[m] || []).includes(day) ? 'all' : 'none'}
                            onChange={v => handleDay(y, m, day, v)}
                          />
                          <span>{String(day).padStart(2, '0')}</span>
                        </label>
                      </div>
                    ))}
                  </div>
                )
              })}
            </div>
          )
        })}
      </div>

      {/* Buttons */}
      <div style={{ display: 'flex', gap: 8, borderTop: '1px solid #eee', paddingTop: 8 }}>
        <button onClick={cancelFilter} style={btnCancel}>Annuler</button>
        <button onClick={applyFilter}  style={btnApply}>Appliquer</button>
      </div>
    </div>
  )
})

DateTreeFilter.displayName = 'DateTreeFilter'
export default DateTreeFilter

// Styles
const rowStyle = {
  display: 'flex', alignItems: 'center', gap: 6,
  padding: '3px 2px', cursor: 'default',
}
const labelStyle = {
  display: 'flex', alignItems: 'center', gap: 8,
  cursor: 'pointer', flex: 1,
}
const chevronStyle = {
  width: 16, display: 'inline-flex', alignItems: 'center',
  justifyContent: 'center', cursor: 'pointer',
  color: '#555', fontSize: 11, fontWeight: 'bold', flexShrink: 0,
}
const btnCancel = {
  flex: 1, padding: '6px 0',
  border: '1px solid #ccc', borderRadius: 4,
  background: '#fff', cursor: 'pointer', fontSize: 13,
}
const btnApply = {
  flex: 1, padding: '6px 0',
  border: 'none', borderRadius: 4,
  background: '#1976d2', color: '#fff',
  cursor: 'pointer', fontSize: 13,
}
