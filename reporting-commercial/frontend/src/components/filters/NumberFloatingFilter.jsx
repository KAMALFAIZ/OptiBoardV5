import { forwardRef, useImperativeHandle, useState } from 'react'

const NumberFloatingFilter = forwardRef((props, ref) => {
  const [value, setValue] = useState('')
  const colId = props.column?.getColId?.() || props.colDef?.field

  useImperativeHandle(ref, () => ({
    onParentModelChanged(parentModel) {
      if (!parentModel || parentModel.filterType !== 'numberCondition') {
        setValue('')
      } else {
        setValue(parentModel.val1 || '')
      }
    }
  }))

  const onChange = (e) => {
    const v = e.target.value
    setValue(v)
    const model = v.trim() === ''
      ? null
      : { filterType: 'numberCondition', operator: 'equals', val1: v, val2: '' }
    const all = { ...props.api.getFilterModel() }
    if (model === null) delete all[colId]
    else all[colId] = model
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
        type="number"
        value={value}
        onChange={onChange}
        placeholder="= ..."
        style={inputStyle}
      />
      {value && (
        <span onClick={onClear} style={clearBtn} title="Effacer">✕</span>
      )}
    </div>
  )
})

NumberFloatingFilter.displayName = 'NumberFloatingFilter'
export default NumberFloatingFilter

const inputStyle = {
  flex: 1, minWidth: 0, height: 22, padding: '1px 4px',
  border: '1px solid #d0d0d0', borderRadius: 3,
  fontSize: 11, outline: 'none', boxSizing: 'border-box',
  background: '#fff', textAlign: 'right',
}
const clearBtn = {
  marginLeft: 3, cursor: 'pointer', color: '#999',
  fontSize: 10, flexShrink: 0, lineHeight: 1,
  userSelect: 'none',
}
