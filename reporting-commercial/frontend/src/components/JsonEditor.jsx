import { useMemo } from 'react'
import CodeMirror from '@uiw/react-codemirror'
import { json } from '@codemirror/lang-json'
import { oneDark } from '@codemirror/theme-one-dark'
import { EditorView } from '@codemirror/view'
import { useTheme } from '../context/ThemeContext'

/**
 * Editeur JSON riche (CodeMirror 6) : coloration syntaxique, numeros de ligne,
 * repli, auto-fermeture des parentheses/crochets et appariement.
 */
export default function JsonEditor({
  value,
  onChange,
  disabled = false,
  minHeight = '180px',
  maxHeight = '400px',
  placeholder = '',
  className = '',
}) {
  const { darkMode } = useTheme()

  const extensions = useMemo(() => [json(), EditorView.lineWrapping], [])

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
