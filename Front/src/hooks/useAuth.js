import { useState, useEffect } from 'react'
import { authStore } from '../store/auth'
import { authApi } from '../api/client'

export function useAuth() {
  const [user, setUser] = useState(authStore.getUser())

  useEffect(() => {
    return authStore.subscribe(() => setUser(authStore.getUser()))
  }, [])

  async function login(email, password) {
    const { data } = await authApi.login(email, password)
    authStore.setAuth(data.access_token, {
      id: data.user_id,
      full_name: data.full_name,
      email: data.email,
      role: data.role,
    })
  }

  function logout() {
    authStore.clearAuth()
  }

  return { user, login, logout, isAuthenticated: !!user }
}
