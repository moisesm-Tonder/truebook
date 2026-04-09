import React, { useState } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import {
  LayoutDashboard, Calculator, FileSpreadsheet, LogOut,
  ChevronDown, ChevronRight, Activity, Plus,
} from 'lucide-react'
import { useAuth } from '../../hooks/useAuth'
import { TonderMark, TonderWordmark } from '../ui/TonderLogo'
import clsx from 'clsx'
import { Sun, Moon } from 'lucide-react'
import { useTheme } from '../../hooks/useTheme'

function ThemeToggleSidebar() {
  const { isDark, toggle } = useTheme()
  return (
    <button
      onClick={toggle}
      className="w-full flex items-center gap-2.5 px-3 py-2 text-xs rounded-xl transition-all"
      style={{ color: '#475569', border: '1px solid rgba(255,255,255,0.05)' }}
      onMouseEnter={e => { e.currentTarget.style.background = 'rgba(55,93,251,0.08)'; e.currentTarget.style.color = '#7b95fd'; e.currentTarget.style.borderColor = 'rgba(55,93,251,0.2)' }}
      onMouseLeave={e => { e.currentTarget.style.background = ''; e.currentTarget.style.color = '#475569'; e.currentTarget.style.borderColor = 'rgba(255,255,255,0.05)' }}
    >
      {/* Mini track */}
      <span style={{ position:'relative', display:'inline-flex', width:26, height:15, borderRadius:99,
        background: isDark ? 'rgba(55,93,251,0.25)' : 'rgba(55,93,251,0.4)',
        border:'1px solid rgba(55,93,251,0.4)', flexShrink:0 }}>
        <span style={{ position:'absolute', top:2, left: isDark ? 2 : 11, width:9, height:9,
          borderRadius:'50%', background:'#375DFB',
          transition:'left 0.3s cubic-bezier(0.34,1.56,0.64,1)',
          boxShadow:'0 0 5px rgba(55,93,251,0.7)' }} />
      </span>
      {isDark ? <Moon size={12} /> : <Sun size={12} />}
      <span>{isDark ? 'Modo oscuro' : 'Modo claro'}</span>
    </button>
  )
}

const NAV = [
  {
    label: 'Dashboard',
    to: '/',
    icon: LayoutDashboard,
  },
  {
    label: 'Proceso Contable',
    icon: Calculator,
    children: [
      { label: 'Corridas', to: '/processes', icon: Activity },
      { label: 'Nueva corrida', to: '/processes/new', icon: Plus },
    ],
  },
]

function NavItem({ item }) {
  const [open, setOpen] = useState(true)

  if (item.children) {
    return (
      <div>
        <button
          onClick={() => setOpen(!open)}
          className="w-full flex items-center gap-3 px-3 py-2.5 text-sm font-medium rounded-xl transition-all"
          style={{ color: '#64748b' }}
          onMouseEnter={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.04)'; e.currentTarget.style.color = '#94a3b8' }}
          onMouseLeave={e => { e.currentTarget.style.background = ''; e.currentTarget.style.color = '#64748b' }}
        >
          <item.icon size={15} className="shrink-0" />
          <span className="flex-1 text-left">{item.label}</span>
          {open
            ? <ChevronDown size={13} />
            : <ChevronRight size={13} />
          }
        </button>
        {open && (
          <div className="mt-0.5 space-y-0.5 ml-3 pl-3" style={{ borderLeft: '1px solid rgba(255,255,255,0.06)' }}>
            {item.children.map(child => (
              <NavItem key={child.to} item={child} />
            ))}
          </div>
        )}
      </div>
    )
  }

  return (
    <NavLink
      to={item.to}
      end
      className={({ isActive }) =>
        clsx(
          'flex items-center gap-3 px-3 py-2.5 text-sm rounded-xl transition-all',
          isActive ? 'nav-active font-semibold' : 'font-medium'
        )
      }
      style={({ isActive }) => isActive
        ? { color: '#7b95fd', background: 'rgba(55,93,251,0.1)', borderRight: '2px solid #375DFB' }
        : { color: '#64748b' }
      }
      onMouseEnter={e => {
        if (!e.currentTarget.classList.contains('nav-active')) {
          e.currentTarget.style.background = 'rgba(255,255,255,0.04)'
          e.currentTarget.style.color = '#94a3b8'
        }
      }}
      onMouseLeave={e => {
        if (!e.currentTarget.style.borderRight) {
          e.currentTarget.style.background = ''
          e.currentTarget.style.color = '#64748b'
        }
      }}
    >
      <item.icon size={15} className="shrink-0" />
      {item.label}
    </NavLink>
  )
}

export default function Sidebar() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  function handleLogout() {
    logout()
    navigate('/login')
  }

  return (
    <aside
      className="w-60 shrink-0 flex flex-col h-screen sticky top-0"
      style={{
        background: 'var(--tonder-surface)',
        borderRight: '1px solid rgba(255,255,255,0.06)',
      }}
    >
      {/* Logo */}
      <div className="px-4 py-4" style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
        {/* Full logotype inverted white */}
        <TonderWordmark height={52} onDark={true} />
        <div className="flex items-center gap-2 mt-2.5">
          <span
            className="text-xs font-semibold px-1.5 py-0.5 rounded-md"
            style={{
              background: 'rgba(55,93,251,0.15)',
              color: '#7b95fd',
              border: '1px solid rgba(55,93,251,0.25)',
            }}
          >
            FinOps
          </span>
          <p className="text-xs" style={{ color: '#334155' }}>Plataforma Contable</p>
        </div>
      </div>

      {/* Navigation label */}
      <div className="px-4 pt-5 pb-2">
        <p className="text-xs font-semibold uppercase tracking-widest" style={{ color: '#334155' }}>
          Módulos
        </p>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-2 space-y-0.5 overflow-y-auto pb-4">
        {NAV.map(item => (
          <NavItem key={item.label} item={item} />
        ))}
      </nav>

      {/* Bottom section */}
      <div className="px-3 py-4" style={{ borderTop: '1px solid rgba(255,255,255,0.06)' }}>
        {/* User pill */}
        <div
          className="flex items-center gap-3 px-3 py-2.5 rounded-xl mb-2"
          style={{ background: 'rgba(255,255,255,0.03)' }}
        >
          <div
            className="w-7 h-7 rounded-lg flex items-center justify-center text-xs font-bold text-white shrink-0"
            style={{
              background: 'linear-gradient(135deg, #375DFB 0%, #2c4fd4 100%)',
              boxShadow: '0 2px 8px rgba(55,93,251,0.4)',
            }}
          >
            {user?.full_name?.[0]?.toUpperCase() || 'U'}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-xs font-semibold text-slate-200 truncate">{user?.full_name}</p>
            <p className="text-xs truncate" style={{ color: '#475569' }}>{user?.role}</p>
          </div>
        </div>

        {/* Theme toggle */}
        <div className="mb-2">
          <ThemeToggleSidebar />
        </div>

        <button
          onClick={handleLogout}
          className="w-full flex items-center gap-2.5 px-3 py-2 text-xs rounded-xl transition-all"
          style={{ color: '#475569' }}
          onMouseEnter={e => { e.currentTarget.style.background = 'rgba(239,68,68,0.08)'; e.currentTarget.style.color = '#f87171' }}
          onMouseLeave={e => { e.currentTarget.style.background = ''; e.currentTarget.style.color = '#475569' }}
        >
          <LogOut size={13} />
          Cerrar sesión
        </button>
      </div>
    </aside>
  )
}
