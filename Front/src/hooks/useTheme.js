import { useState, useEffect } from 'react'
import { themeStore } from '../store/theme'

export function useTheme() {
  const [theme, setTheme] = useState(themeStore.get())

  useEffect(() => {
    return themeStore.subscribe(setTheme)
  }, [])

  return { theme, toggle: themeStore.toggle, isDark: theme === 'dark' }
}
