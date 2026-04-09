import React from 'react'
import { Sun, Moon } from 'lucide-react'
import { useTheme } from '../../hooks/useTheme'

export default function ThemeToggle({ className = '' }) {
  const { isDark, toggle } = useTheme()

  return (
    <button
      onClick={toggle}
      aria-label={isDark ? 'Cambiar a modo claro' : 'Cambiar a modo oscuro'}
      className={className}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 6,
        padding: '6px 12px',
        borderRadius: 99,
        fontSize: 12,
        fontWeight: 600,
        cursor: 'pointer',
        transition: 'all 0.25s ease',
        background: isDark
          ? 'rgba(255,255,255,0.06)'
          : 'rgba(255,255,255,0.25)',
        border: isDark
          ? '1px solid rgba(255,255,255,0.1)'
          : '1px solid rgba(255,255,255,0.4)',
        color: isDark ? '#94a3b8' : '#ffffff',
        backdropFilter: 'blur(8px)',
        WebkitBackdropFilter: 'blur(8px)',
      }}
      onMouseEnter={e => {
        e.currentTarget.style.background = isDark
          ? 'rgba(255,255,255,0.1)'
          : 'rgba(255,255,255,0.35)'
        e.currentTarget.style.color = isDark ? '#e2e8f0' : '#ffffff'
        e.currentTarget.style.transform = 'scale(1.04)'
      }}
      onMouseLeave={e => {
        e.currentTarget.style.background = isDark
          ? 'rgba(255,255,255,0.06)'
          : 'rgba(255,255,255,0.25)'
        e.currentTarget.style.color = isDark ? '#94a3b8' : '#ffffff'
        e.currentTarget.style.transform = 'scale(1)'
      }}
    >
      {/* Track */}
      <span
        style={{
          position: 'relative',
          display: 'inline-flex',
          width: 32,
          height: 18,
          borderRadius: 99,
          background: isDark
            ? 'rgba(55,93,251,0.3)'
            : 'rgba(255,255,255,0.5)',
          border: isDark
            ? '1px solid rgba(55,93,251,0.5)'
            : '1px solid rgba(255,255,255,0.6)',
          transition: 'all 0.3s ease',
          flexShrink: 0,
        }}
      >
        {/* Thumb */}
        <span
          style={{
            position: 'absolute',
            top: 2,
            left: isDark ? 2 : 14,
            width: 12,
            height: 12,
            borderRadius: '50%',
            background: isDark ? '#375DFB' : '#ffffff',
            transition: 'left 0.3s cubic-bezier(0.34,1.56,0.64,1)',
            boxShadow: isDark
              ? '0 0 6px rgba(55,93,251,0.8)'
              : '0 1px 4px rgba(0,0,0,0.2)',
          }}
        />
      </span>

      {isDark ? <Moon size={13} /> : <Sun size={13} />}
      <span>{isDark ? 'Dark' : 'Light'}</span>
    </button>
  )
}
