// Simple auth store (no external lib needed)
const listeners = new Set()

function getUser() {
  try { return JSON.parse(localStorage.getItem('user') || 'null') } catch { return null }
}

function getToken() { return localStorage.getItem('token') }

function setAuth(token, user) {
  localStorage.setItem('token', token)
  localStorage.setItem('user', JSON.stringify(user))
  listeners.forEach(fn => fn())
}

function clearAuth() {
  localStorage.removeItem('token')
  localStorage.removeItem('user')
  listeners.forEach(fn => fn())
}

function subscribe(fn) {
  listeners.add(fn)
  return () => listeners.delete(fn)
}

export const authStore = { getUser, getToken, setAuth, clearAuth, subscribe }
