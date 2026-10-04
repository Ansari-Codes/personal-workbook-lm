import { ref } from 'vue'

export type Theme = 'light' | 'dark' | 'system'

const theme = ref<Theme>('system')

function preferredTheme(): 'light' | 'dark' {
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

function applyTheme(value: Theme) {
  theme.value = value
  const resolved = value === 'system' ? preferredTheme() : value
  document.documentElement.classList.toggle('dark', resolved === 'dark')
  document.documentElement.dataset.theme = value
  localStorage.setItem('theme', value)
}

export function useTheme() {
  if (typeof window !== 'undefined' && !document.documentElement.dataset.theme) {
    applyTheme((localStorage.getItem('theme') as Theme | null) ?? 'system')
  }

  return { theme, setTheme: applyTheme }
}