import { useMemo, useEffect } from 'react'
import CodeMirror from '@uiw/react-codemirror'
import { json, jsonParseLinter } from '@codemirror/lang-json'
import { oneDark } from '@codemirror/theme-one-dark'
import { EditorView } from '@codemirror/view'
import { linter, lintGutter } from '@codemirror/lint'
import { useTheme } from '../context/ThemeContext'

/**
 * Editeur JSON riche (CodeMirror 6) : coloration syntaxique, numeros de ligne,
 * repli, auto-fermeture des parentheses/crochets, appariement et VALIDATION
 * en direct (erreurs soulignees + marge de lint). onValidityChange(bool) notifie
 * le parent de la validite du JSON.
 */
export default function JsonEditor({
  value,
  onChange,
  disabled = false,
  minHeight = '180px',
  maxHeight = '400px',
  placeholder = '',
  className = '',
  onValidityChange = null,
}) {
  const { darkMode } = useTheme()

  const extensions = useMemo(
    () => [json(), linter(jsonParseLinter()), lintGutter(), EditorView.lineWrapping],
    []
  )

  // Notifier la validite du JSON au parent (vide = valide)
  useEffect(() => {
    if (!onValidityChange) return
    const v = (value || '').trim()
    if (!v) { onValidityChange(true); return }
    try { JSON.parse(v); onValidityChange(true) } catch { onValidityChange(false) }
  }, [value, onValidityChange])

  return (
    <div
      className={`cm-json-editor rounded-lg overflow-hidden border border-primary-300 dark:border-primary-600 focus-within:ring-2 focus-within:ring-primary-500 ${className}`}
    >
      <CodeMirror
        value={value}
        height="auto"
        minHeight={minHeight}
        maxHeight={maxHeight}
        theme={darkMode ? oneDark : 'light'}
        extensions={extensions}
        editable={!disabled}
        readOnly={disabled}
        placeholder={placeholder}
        onChange={onChange}
        basicSetup={{
          lineNumbers: true,
          foldGutter: true,
          highlightActiveLine: !disabled,
          bracketMatching: true,
          closeBrackets: true,
          autocompletion: true,
          indentOnInput: true,
          tabSize: 2,
        }}
        style={{ fontSize: '13px', opacity: disabled ? 0.6 : 1 }}
      />
    </div>
  )
}
