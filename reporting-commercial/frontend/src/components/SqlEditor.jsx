import { useMemo } from 'react'
import CodeMirror from '@uiw/react-codemirror'
import { sql, MSSQL } from '@codemirror/lang-sql'
import { oneDark } from '@codemirror/theme-one-dark'
import { EditorView, Decoration } from '@codemirror/view'
import { RangeSetBuilder } from '@codemirror/state'
import { ViewPlugin } from '@codemirror/view'
import { useTheme } from '../context/ThemeContext'

// Surligne les parametres dynamiques @param (ex: @dateDebut, @societe_filter)
const PARAM_RE = /@[A-Za-z_][A-Za-z0-9_]*/g
const paramMark = Decoration.mark({ class: 'cm-sql-param' })

const paramHighlighter = ViewPlugin.fromClass(
  class {
    constructor(view) {
      this.decorations = this.build(view)
    }
    update(u) {
      if (u.docChanged || u.viewportChanged) this.decorations = this.build(u.view)
    }
    build(view) {
      const builder = new RangeSetBuilder()
      for (const { from, to } of view.visibleRanges) {
        const text = view.state.doc.sliceString(from, to)
        let m
        PARAM_RE.lastIndex = 0
        while ((m = PARAM_RE.exec(text))) {
          builder.add(from + m.index, from + m.index + m[0].length, paramMark)
        }
      }
      return builder.finish()
    }
  },
  { decorations: (v) => v.decorations }
)

const baseTheme = EditorView.baseTheme({
  '.cm-sql-param': {
    color: '#d97706',
    backgroundColor: 'rgba(217, 119, 6, 0.12)',
    borderRadius: '3px',
    fontWeight: '600',
    padding: '0 1px',
  },
  '&dark .cm-sql-param': {
    color: '#fbbf24',
    backgroundColor: 'rgba(251, 191, 36, 0.15)',
  },
})

/**
 * Editeur SQL riche (CodeMirror 6) : coloration syntaxique T-SQL,
 * numeros de ligne, repli de code, auto-completion des mots-cles,
 * appariement des parentheses, et surlignage des parametres @param.
 */
export default function SqlEditor({
  value,
  onChange,
  disabled = false,
  minHeight = '280px',
  maxHeight = '600px',
  height,
  placeholder = '',
  // fill=true : occupe toute la hauteur du conteneur parent (panneaux flex)
  fill = false,
  // forceDark=true : force le theme sombre quel que soit le mode global
  forceDark = false,
  className = '',
}) {
  const { darkMode } = useTheme()

  const extensions = useMemo(
    () => [
      sql({ dialect: MSSQL, upperCaseKeywords: true }),
      paramHighlighter,
      baseTheme,
      EditorView.lineWrapping,
    ],
    []
  )

  const wrapperClass = fill
    ? `cm-sql-editor h-full overflow-hidden ${className}`
    : `cm-sql-editor rounded-lg overflow-hidden border border-primary-300 dark:border-primary-600 focus-within:ring-2 focus-within:ring-primary-500 ${className}`

  const heightProps = fill
    ? { height: '100%' }
    : { height: height || 'auto', minHeight, maxHeight }

  return (
    <div className={wrapperClass}>
      <CodeMirror
        value={value}
        {...heightProps}
        theme={forceDark || darkMode ? oneDark : 'light'}
        extensions={extensions}
        editable={!disabled}
        readOnly={disabled}
        placeholder={placeholder}
        onChange={onChange}
        basicSetup={{
          lineNumbers: true,
          foldGutter: true,
          highlightActiveLine: !disabled,
          highlightActiveLineGutter: !disabled,
          bracketMatching: true,
          closeBrackets: true,
          autocompletion: true,
          indentOnInput: true,
          tabSize: 2,
        }}
        style={{ fontSize: '13px', height: fill ? '100%' : undefined, opacity: disabled ? 0.6 : 1 }}
      />
    </div>
  )
}
