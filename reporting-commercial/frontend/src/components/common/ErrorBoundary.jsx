import { Component } from 'react'
import { AlertTriangle, RefreshCw } from 'lucide-react'

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  componentDidCatch(error, info) {
    // En production, envoyer vers un service de monitoring (ex: Sentry)
    console.error('[ErrorBoundary]', error, info.componentStack)
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null })
  }

  render() {
    if (!this.state.hasError) return this.props.children

    const { title = 'Une erreur est survenue', compact = false } = this.props

    if (compact) {
      return (
        <div className="flex items-center gap-2 p-3 rounded-lg bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 text-sm">
          <AlertTriangle className="w-4 h-4 flex-shrink-0" />
          <span>{title}</span>
          <button
            onClick={this.handleReset}
            className="ml-auto flex items-center gap-1 hover:text-red-800 dark:hover:text-red-200"
          >
            <RefreshCw className="w-3 h-3" />
            Réessayer
          </button>
        </div>
      )
    }

    return (
      <div className="flex flex-col items-center justify-center min-h-[200px] p-8 text-center">
        <AlertTriangle className="w-12 h-12 text-red-500 mb-4" />
        <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-100 mb-2">{title}</h2>
        {this.state.error && (
          <p className="text-sm text-gray-500 dark:text-gray-400 mb-4 max-w-md font-mono">
            {this.state.error.message}
          </p>
        )}
        <button
          onClick={this.handleReset}
          className="flex items-center gap-2 px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg text-sm transition-colors"
        >
          <RefreshCw className="w-4 h-4" />
          Réessayer
        </button>
      </div>
    )
  }
}
