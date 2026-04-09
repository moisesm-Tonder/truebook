import React, { useState } from 'react'
import { useNavigate, Navigate } from 'react-router-dom'
import { Eye, EyeOff, Loader2, ArrowRight, Shield, Zap, BarChart3 } from 'lucide-react'
import { useAuth } from '../hooks/useAuth'
import { TonderMark, TonderWordmark } from '../components/ui/TonderLogo'
import ThemeToggle from '../components/ui/ThemeToggle'


const FEATURES = [
  { icon: Zap, label: 'Extracción automática', desc: 'Datos en tiempo real desde MongoDB' },
  { icon: BarChart3, label: 'Conciliación inteligente', desc: 'Kushki vs Banregio en segundos' },
  { icon: Shield, label: 'Proceso auditado', desc: 'Log completo de cada corrida' },
]

export default function Login() {
  const { login, isAuthenticated } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({ email: '', password: '' })
  const [showPass, setShowPass] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  if (isAuthenticated) return <Navigate to="/" replace />

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await login(form.email, form.password)
      navigate('/')
    } catch (err) {
      setError(err.response?.data?.detail || 'Credenciales incorrectas')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex" style={{ background: 'var(--tonder-bg)', transition: 'background 0.3s ease' }}>

      {/* ── Left panel — branding ── */}
      <div
        className="hidden lg:flex flex-col justify-between w-[52%] relative overflow-hidden p-12"
        style={{
          background: 'linear-gradient(145deg, #080c18 0%, #0d1530 50%, #0a1245 100%)',
          borderRight: '1px solid rgba(55,93,251,0.12)',
        }}
      >
        {/* Grid overlay */}
        <div className="absolute inset-0 tonder-grid opacity-60" />

        {/* Blue glow orb */}
        <div
          className="absolute rounded-full pointer-events-none"
          style={{
            width: 600,
            height: 600,
            background: 'radial-gradient(circle, rgba(55,93,251,0.18) 0%, transparent 70%)',
            top: '10%',
            left: '-10%',
          }}
        />
        <div
          className="absolute rounded-full pointer-events-none"
          style={{
            width: 400,
            height: 400,
            background: 'radial-gradient(circle, rgba(55,93,251,0.12) 0%, transparent 70%)',
            bottom: '5%',
            right: '-5%',
          }}
        />

        {/* Logo */}
        <div className="relative z-10">
          <TonderWordmark height={84} onDark={true} />
        </div>

        {/* Center headline + animated feature cards */}
        <div className="relative z-10">
          <h1
            className="text-4xl font-bold text-white leading-tight mb-4"
            style={{ fontFamily: "'Plus Jakarta Sans', sans-serif", letterSpacing: '-0.03em' }}
          >
            Infraestructura de pagos{' '}
            <span className="gradient-text">inteligente</span>
          </h1>

          <p className="text-slate-400 text-base leading-relaxed mb-10 max-w-sm">
            Consolida FEES, concilia Kushki y Banregio, y cierra tu mes contable
            con un solo clic.
          </p>

          {/* Animated feature cards */}
          <style>{`
            @keyframes fadeSlideUp {
              from { opacity: 0; transform: translateY(22px); }
              to   { opacity: 1; transform: translateY(0); }
            }
            @keyframes iconPulse {
              0%, 100% { box-shadow: 0 0 0 0 rgba(55,93,251,0.4); }
              50%       { box-shadow: 0 0 0 8px rgba(55,93,251,0); }
            }
            .feature-card {
              animation: fadeSlideUp 0.55s ease both;
            }
            .feature-card:hover .feature-icon {
              animation: iconPulse 1.2s ease infinite;
              background: rgba(55,93,251,0.22) !important;
            }
            .feature-card:hover {
              border-color: rgba(55,93,251,0.35) !important;
              background: rgba(55,93,251,0.07) !important;
            }
          `}</style>

          <div className="space-y-3">
            {FEATURES.map(({ icon: Icon, label, desc }, i) => (
              <div
                key={label}
                className="feature-card flex items-center gap-4 px-4 py-3.5 rounded-2xl transition-all duration-300"
                style={{
                  background: 'rgba(55,93,251,0.04)',
                  border: '1px solid rgba(55,93,251,0.15)',
                  animationDelay: `${i * 0.15}s`,
                  cursor: 'default',
                }}
              >
                <div
                  className="feature-icon w-10 h-10 rounded-xl flex items-center justify-center shrink-0 transition-all duration-300"
                  style={{
                    background: 'rgba(55,93,251,0.12)',
                    border: '1px solid rgba(55,93,251,0.25)',
                  }}
                >
                  <Icon size={18} style={{ color: '#375DFB' }} />
                </div>
                <div>
                  <p className="text-sm font-semibold text-white">{label}</p>
                  <p className="text-xs mt-0.5" style={{ color: '#475569' }}>{desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Bottom */}
        <div className="relative z-10 flex items-center gap-3">
          <div
            className="w-1.5 h-1.5 rounded-full"
            style={{ background: '#375DFB', boxShadow: '0 0 6px #375DFB' }}
          />
          <p className="text-xs" style={{ color: '#334155' }}>
            Plataforma interna · Tonder © {new Date().getFullYear()}
          </p>
        </div>
      </div>

      {/* ── Right panel — form ── */}
      <div className="flex-1 flex items-center justify-center px-6 py-12 relative">

        {/* Theme toggle — top right */}
        <div className="absolute top-5 right-6">
          <ThemeToggle />
        </div>

        <div className="w-full max-w-sm">

          {/* Mobile logo */}
          <div className="mb-10 lg:hidden">
            <TonderWordmark height={40} onDark={true} />
          </div>

          <div className="mb-8">
            <h2
              className="text-2xl font-bold text-white mb-2"
              style={{ fontFamily: "'Plus Jakarta Sans', sans-serif", letterSpacing: '-0.02em' }}
            >
              Bienvenido de nuevo
            </h2>
            <p className="text-slate-400 text-sm">
              Ingresa a tu cuenta para continuar
            </p>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="label">Correo electrónico</label>
              <input
                type="email"
                className="input"
                placeholder="usuario@tonder.io"
                value={form.email}
                onChange={e => setForm(f => ({ ...f, email: e.target.value }))}
                required
                autoComplete="email"
              />
            </div>

            <div>
              <label className="label">Contraseña</label>
              <div className="relative">
                <input
                  type={showPass ? 'text' : 'password'}
                  className="input pr-11"
                  placeholder="••••••••"
                  value={form.password}
                  onChange={e => setForm(f => ({ ...f, password: e.target.value }))}
                  required
                  autoComplete="current-password"
                />
                <button
                  type="button"
                  onClick={() => setShowPass(!showPass)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 transition-colors"
                >
                  {showPass ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            {error && (
              <div
                className="text-sm px-4 py-3 rounded-xl"
                style={{
                  background: 'rgba(239,68,68,0.08)',
                  border: '1px solid rgba(239,68,68,0.2)',
                  color: '#f87171',
                }}
              >
                {error}
              </div>
            )}

            <button
              type="submit"
              className="btn-primary w-full flex items-center justify-center gap-2 py-2.5 mt-2"
              disabled={loading}
            >
              {loading
                ? <><Loader2 size={16} className="animate-spin" /> Verificando...</>
                : <><span>Ingresar</span> <ArrowRight size={16} /></>
              }
            </button>
          </form>

          {/* Divider */}
          <div className="flex items-center gap-3 my-6">
            <div className="flex-1 h-px" style={{ background: 'rgba(255,255,255,0.06)' }} />
            <span className="text-xs text-slate-600">acceso restringido</span>
            <div className="flex-1 h-px" style={{ background: 'rgba(255,255,255,0.06)' }} />
          </div>

          <p className="text-center text-xs text-slate-600">
            Plataforma interna · Tonder © {new Date().getFullYear()}
          </p>
        </div>
      </div>
    </div>
  )
}
