import { createContext, useContext, useState, useEffect } from 'react'
import { useAuth } from './AuthContext'

const ThemeContext = createContext(null)

// Thèmes prédéfinis
export const themes = {
  default: {
    id: 'default',
    name: 'Bleu Classique',
    description: 'Thème par défaut avec des tons bleus professionnels',
    colors: {
      primary: {
        50: '#eff6ff',
        100: '#dbeafe',
        200: '#bfdbfe',
        300: '#93c5fd',
        400: '#60a5fa',
        500: '#3b82f6',
        600: '#2563eb',
        700: '#1d4ed8',
        800: '#1e40af',
        900: '#1e3a8a',
      },
      accent: '#10b981',
      sidebar: {
        bg: '#2563eb',
        text: '#ffffff',
        hover: '#1d4ed8',
      }
    }
  },
  emerald: {
    id: 'emerald',
    name: 'Vert Emeraude',
    description: 'Thème vert frais et moderne',
    colors: {
      primary: {
        50: '#ecfdf5',
        100: '#d1fae5',
        200: '#a7f3d0',
        300: '#6ee7b7',
        400: '#34d399',
        500: '#10b981',
        600: '#059669',
        700: '#047857',
        800: '#065f46',
        900: '#064e3b',
      },
      accent: '#3b82f6',
      sidebar: {
        bg: '#059669',
        text: '#ffffff',
        hover: '#047857',
      }
    }
  },
  purple: {
    id: 'purple',
    name: 'Violet Royal',
    description: 'Thème élégant avec des tons violets',
    colors: {
      primary: {
        50: '#faf5ff',
        100: '#f3e8ff',
        200: '#e9d5ff',
        300: '#d8b4fe',
        400: '#c084fc',
        500: '#a855f7',
        600: '#9333ea',
        700: '#7e22ce',
        800: '#6b21a8',
        900: '#581c87',
      },
      accent: '#f59e0b',
      sidebar: {
        bg: '#7e22ce',
        text: '#ffffff',
        hover: '#6b21a8',
      }
    }
  },
  orange: {
    id: 'orange',
    name: 'Orange Dynamique',
    description: 'Thème chaleureux et énergique',
    colors: {
      primary: {
        50: '#fff7ed',
        100: '#ffedd5',
        200: '#fed7aa',
        300: '#fdba74',
        400: '#fb923c',
        500: '#f97316',
        600: '#ea580c',
        700: '#c2410c',
        800: '#9a3412',
        900: '#7c2d12',
      },
      accent: '#0ea5e9',
      sidebar: {
        bg: '#ea580c',
        text: '#ffffff',
        hover: '#c2410c',
      }
    }
  },
  slate: {
    id: 'slate',
    name: 'Gris Professionnel',
    description: 'Thème sobre et professionnel',
    colors: {
      primary: {
        50: '#f8fafc',
        100: '#f1f5f9',
        200: '#e2e8f0',
        300: '#cbd5e1',
        400: '#94a3b8',
        500: '#64748b',
        600: '#475569',
        700: '#334155',
        800: '#1e293b',
        900: '#0f172a',
      },
      accent: '#3b82f6',
      sidebar: {
        bg: '#334155',
        text: '#ffffff',
        hover: '#1e293b',
      }
    }
  },
  rose: {
    id: 'rose',
    name: 'Rose Moderne',
    description: 'Thème rose élégant et moderne',
    colors: {
      primary: {
        50: '#fff1f2',
        100: '#ffe4e6',
        200: '#fecdd3',
        300: '#fda4af',
        400: '#fb7185',
        500: '#f43f5e',
        600: '#e11d48',
        700: '#be123c',
        800: '#9f1239',
        900: '#881337',
      },
      accent: '#8b5cf6',
      sidebar: {
        bg: '#e11d48',
        text: '#ffffff',
        hover: '#be123c',
      }
    }
  },
  teal: {
    id: 'teal',
    name: 'Turquoise',
    description: 'Thème bleu-vert apaisant',
    colors: {
      primary: {
        50: '#f0fdfa',
        100: '#ccfbf1',
        200: '#99f6e4',
        300: '#5eead4',
        400: '#2dd4bf',
        500: '#14b8a6',
        600: '#0d9488',
        700: '#0f766e',
        800: '#115e59',
        900: '#134e4a',
      },
      accent: '#f59e0b',
      sidebar: {
        bg: '#0d9488',
        text: '#ffffff',
        hover: '#0f766e',
      }
    }
  },
  indigo: {
    id: 'indigo',
    name: 'Indigo Nuit',
    description: 'Thème indigo profond et sophistiqué',
    colors: {
      primary: {
        50: '#eef2ff',
        100: '#e0e7ff',
        200: '#c7d2fe',
        300: '#a5b4fc',
        400: '#818cf8',
        500: '#6366f1',
        600: '#4f46e5',
        700: '#4338ca',
        800: '#3730a3',
        900: '#312e81',
      },
      accent: '#10b981',
      sidebar: {
        bg: '#4338ca',
        text: '#ffffff',
        hover: '#3730a3',
      }
    }
  }
}

export function ThemeProvider({ children }) {
  const { user } = useAuth()
  const [currentTheme, setCurrentTheme] = useState('default')
  const [darkMode, setDarkMode] = useState(false)
  const [compactMode, setCompactMode] = useState(false)

  // Charger le thème de l'utilisateur au démarrage
  useEffect(() => {
    if (user) {
      const savedTheme = localStorage.getItem(`theme_${user.id}`)
      const savedDarkMode = localStorage.getItem(`darkMode_${user.id}`)
      const savedCompactMode = localStorage.getItem(`compactMode_${user.id}`)

      if (savedTheme && themes[savedTheme]) {
        setCurrentTheme(savedTheme)
      }
      if (savedDarkMode !== null) {
        setDarkMode(savedDarkMode === 'true')
      }
      if (savedCompactMode !== null) {
        setCompactMode(savedCompactMode === 'true')
      }
    } else {
      // Thème par défaut si pas d'utilisateur
      const savedTheme = localStorage.getItem('theme_default')
      const savedDarkMode = localStorage.getItem('darkMode_default')
      const savedCompactMode = localStorage.getItem('compactMode_default')

      if (savedTheme && themes[savedTheme]) {
        setCurrentTheme(savedTheme)
      }
      if (savedDarkMode !== null) {
        setDarkMode(savedDarkMode === 'true')
      }
      if (savedCompactMode !== null) {
        setCompactMode(savedCompactMode === 'true')
      }
    }
  }, [user])

  // Appliquer le thème
  useEffect(() => {
    const theme = themes[currentTheme]
    if (theme) {
      const root = document.documentElement

      // Appliquer les couleurs primaires comme variables CSS
      Object.entries(theme.colors.primary).forEach(([key, value]) => {
        root.style.setProperty(`--color-primary-${key}`, value)
      })

      // Appliquer la couleur accent
      root.style.setProperty('--color-accent', theme.colors.accent)

      // Appliquer les couleurs de sidebar
      root.style.setProperty('--sidebar-bg', theme.colors.sidebar.bg)
      root.style.setProperty('--sidebar-text', theme.colors.sidebar.text)
      root.style.setProperty('--sidebar-hover', theme.colors.sidebar.hover)
    }
  }, [currentTheme])

  // Appliquer le mode sombre
  useEffect(() => {
    if (darkMode) {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
  }, [darkMode])

  // Appliquer le mode compact
  useEffect(() => {
    if (compactMode) {
      document.documentElement.classList.add('compact')
    } else {
      document.documentElement.classList.remove('compact')
    }
  }, [compactMode])

  const changeTheme = (themeId) => {
    if (themes[themeId]) {
      setCurrentTheme(themeId)
      const key = user ? `theme_${user.id}` : 'theme_default'
      localStorage.setItem(key, themeId)
    }
  }

  const toggleDarkMode = () => {
    const newDarkMode = !darkMode
    setDarkMode(newDarkMode)
    const key = user ? `darkMode_${user.id}` : 'darkMode_default'
    localStorage.setItem(key, String(newDarkMode))
  }

  const setDarkModeValue = (value) => {
    setDarkMode(value)
    const key = user ? `darkMode_${user.id}` : 'darkMode_default'
    localStorage.setItem(key, String(value))
  }

  const setCompactModeValue = (value) => {
    setCompactMode(value)
    const key = user ? `compactMode_${user.id}` : 'compactMode_default'
    localStorage.setItem(key, String(value))
  }

  return (
    <ThemeContext.Provider value={{
      currentTheme,
      theme: themes[currentTheme],
      themes,
      changeTheme,
      darkMode,
      toggleDarkMode,
      setDarkMode: setDarkModeValue,
      compactMode,
      setCompactMode: setCompactModeValue
    }}>
      {children}
    </ThemeContext.Provider>
  )
}

export function useTheme() {
  const context = useContext(ThemeContext)
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider')
  }
  return context
}
