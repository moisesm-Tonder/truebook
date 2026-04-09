// Simple theme store — persists in localStorage
const listeners = new Set()

function get() {
  return localStorage.getItem('theme') || 'dark'
}

function set(theme) {
  localStorage.setItem('theme', theme)
  document.documentElement.setAttribute('data-theme', theme)
  listeners.forEach(fn => fn(theme))
}

function toggle() {
  set(get() === 'dark' ? 'light' : 'dark')
}

function init() {
  document.documentElement.setAttribute('data-theme', get())
}

function subscribe(fn) {
  listeners.add(fn)
  return () => listeners.delete(fn)
}

export const themeStore = { get, set, toggle, init, subscribe }
