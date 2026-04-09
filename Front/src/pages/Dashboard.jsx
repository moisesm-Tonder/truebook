import React from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { processApi } from '../api/client'
import {
  Activity, Plus, CheckCircle2, XCircle, Loader2,
  TrendingUp, ArrowRight, Calendar, Clock,
  BarChart3, Layers,
} from 'lucide-react'
import StatusBadge from '../components/ui/StatusBadge'
import { TonderWordmark } from '../components/ui/TonderLogo'
import { format } from 'date-fns'
import { es } from 'date-fns/locale'
import { useAuth } from '../hooks/useAuth'
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer,
} from 'recharts'

const MONTH_NAMES = [
  'Ene','Feb','Mar','Abr','May','Jun',
  'Jul','Ago','Sep','Oct','Nov','Dic'
]

function StatCard({ label, value, icon: Icon, color, sub }) {
  return (
    <div
      className="relative overflow-hidden rounded-2xl p-5 flex items-start gap-4"
      style={{
        background: 'var(--tonder-surface)',
        border: '1px solid rgba(255,255,255,0.06)',
      }}
    >
      <div
        className="w-11 h-11 rounded-xl flex items-center justify-center shrink-0"
        style={{ background: color + '18', border: `1px solid ${color}28` }}
      >
        <Icon size={20} style={{ color }} />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-2xl font-bold text-white" style={{ fontFamily: "'Plus Jakarta Sans', sans-serif" }}>
          {value}
        </p>
        <p className="text-sm mt-0.5" style={{ color: '#64748b' }}>{label}</p>
        {sub && <p className="text-xs mt-1" style={{ color: '#374151' }}>{sub}</p>}
      </div>
      {/* Glow corner */}
      <div
        className="absolute -bottom-6 -right-6 w-20 h-20 rounded-full pointer-events-none"
        style={{ background: `radial-gradient(circle, ${color}15 0%, transparent 70%)` }}
      />
    </div>
  )
}

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  return (
    <div
      className="px-3 py-2 rounded-xl text-xs"
      style={{ background: '#111827', border: '1px solid rgba(55,93,251,0.2)', color: '#e2e8f0' }}
    >
      <p className="font-semibold mb-1">{label}</p>
      {payload.map(p => (
        <p key={p.dataKey} style={{ color: p.color }}>
          {p.name}: {p.value}
        </p>
      ))}
    </div>
  )
}

export default function Dashboard() {
  const { user } = useAuth()
  const { data: processes = [], isLoading } = useQuery({
    queryKey: ['processes'],
    queryFn: () => processApi.list().then(r => r.data),
    refetchInterval: 10_000,
  })

  const stats = {
    total: processes.length,
    completed: processes.filter(p => p.status === 'completed').length,
    running: processes.filter(p => p.status === 'running').length,
    failed: processes.filter(p => p.status === 'failed').length,
  }

  // Activity chart data (last 6 months from available processes)
  const chartData = MONTH_NAMES.map((month, i) => ({
    month,
    corridas: processes.filter(p => new Date(p.created_at).getMonth() === i).length,
  })).slice(0, new Date().getMonth() + 1)

  const recent = processes.slice(0, 6)
  const now = new Date()
  const greeting = now.getHours() < 12 ? 'Buenos días' : now.getHours() < 18 ? 'Buenas tardes' : 'Buenas noches'

  return (
    <div className="min-h-screen" style={{ background: 'var(--tonder-bg)' }}>

      {/* ── Top bar ── */}
      <div
        className="px-8 py-5 flex items-center justify-between"
        style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}
      >
        <div>
          <p className="text-sm" style={{ color: '#475569' }}>
            {greeting}, <span className="text-slate-300 font-medium">{user?.full_name?.split(' ')[0]}</span>
          </p>
          <h1
            className="text-xl font-bold text-white mt-0.5"
            style={{ fontFamily: "'Plus Jakarta Sans', sans-serif", letterSpacing: '-0.02em' }}
          >
            Dashboard
          </h1>
        </div>

        <div className="flex items-center gap-3">
          {/* Today's date pill */}
          <div
            className="flex items-center gap-2 px-3 py-1.5 rounded-xl text-xs font-medium"
            style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.07)', color: '#64748b' }}
          >
            <Calendar size={12} />
            {format(now, "dd MMM yyyy", { locale: es })}
          </div>

          <Link to="/processes/new" className="btn-primary flex items-center gap-2 text-sm">
            <Plus size={15} />
            Nueva corrida
          </Link>
        </div>
      </div>

      <div className="px-8 py-6 space-y-6">

        {/* ── Stats grid ── */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard label="Total corridas" value={stats.total} icon={Layers} color="#375DFB"
            sub={stats.total > 0 ? `Período activo` : 'Sin corridas aún'} />
          <StatCard label="Completadas" value={stats.completed} icon={CheckCircle2} color="#10b981"
            sub={stats.total > 0 ? `${Math.round(stats.completed / stats.total * 100)}% del total` : ''} />
          <StatCard label="En ejecución" value={stats.running} icon={Loader2} color="#375DFB"
            sub={stats.running > 0 ? 'En proceso ahora' : 'Ninguna activa'} />
          <StatCard label="Con error" value={stats.failed} icon={XCircle} color="#ef4444"
            sub={stats.failed > 0 ? 'Requieren revisión' : 'Sin errores'} />
        </div>

        <div className="grid grid-cols-3 gap-6">

          {/* ── Activity chart ── */}
          <div
            className="col-span-2 rounded-2xl p-5"
            style={{ background: 'var(--tonder-surface)', border: '1px solid rgba(255,255,255,0.06)' }}
          >
            <div className="flex items-center justify-between mb-5">
              <div>
                <h2
                  className="text-sm font-semibold text-white"
                  style={{ fontFamily: "'Plus Jakarta Sans', sans-serif" }}
                >
                  Actividad mensual
                </h2>
                <p className="text-xs mt-0.5" style={{ color: '#475569' }}>
                  Corridas ejecutadas por mes
                </p>
              </div>
              <BarChart3 size={16} style={{ color: '#334155' }} />
            </div>

            {chartData.length > 0 && chartData.some(d => d.corridas > 0) ? (
              <ResponsiveContainer width="100%" height={160}>
                <AreaChart data={chartData} margin={{ top: 5, right: 0, left: -20, bottom: 0 }}>
                  <defs>
                    <linearGradient id="colorCorridas" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#375DFB" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#375DFB" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                  <XAxis dataKey="month" tick={{ fill: '#334155', fontSize: 11 }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fill: '#334155', fontSize: 11 }} axisLine={false} tickLine={false} allowDecimals={false} />
                  <Tooltip content={<CustomTooltip />} />
                  <Area
                    type="monotone"
                    dataKey="corridas"
                    stroke="#375DFB"
                    strokeWidth={2}
                    fill="url(#colorCorridas)"
                    name="Corridas"
                    dot={{ fill: '#375DFB', strokeWidth: 0, r: 3 }}
                    activeDot={{ fill: '#375DFB', r: 5, strokeWidth: 0 }}
                  />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex flex-col items-center justify-center h-40">
                <BarChart3 size={32} style={{ color: '#1e293b' }} className="mb-3" />
                <p className="text-sm" style={{ color: '#334155' }}>Sin actividad aún</p>
              </div>
            )}
          </div>

          {/* ── Quick actions ── */}
          <div
            className="rounded-2xl p-5 flex flex-col"
            style={{ background: 'var(--tonder-surface)', border: '1px solid rgba(255,255,255,0.06)' }}
          >
            <h2
              className="text-sm font-semibold text-white mb-4"
              style={{ fontFamily: "'Plus Jakarta Sans', sans-serif" }}
            >
              Acciones rápidas
            </h2>

            <div className="flex-1 space-y-2">
              {[
                { label: 'Nueva corrida', desc: 'Iniciar cierre mensual', to: '/processes/new', icon: Plus },
                { label: 'Ver corridas', desc: 'Historial completo', to: '/processes', icon: Activity },
              ].map(a => (
                <Link
                  key={a.label}
                  to={a.to}
                  className="flex items-center gap-3 p-3 rounded-xl transition-all group"
                  style={{ border: '1px solid rgba(255,255,255,0.05)' }}
                  onMouseEnter={e => {
                    e.currentTarget.style.background = 'rgba(55,93,251,0.08)'
                    e.currentTarget.style.borderColor = 'rgba(55,93,251,0.2)'
                  }}
                  onMouseLeave={e => {
                    e.currentTarget.style.background = ''
                    e.currentTarget.style.borderColor = 'rgba(255,255,255,0.05)'
                  }}
                >
                  <div
                    className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0"
                    style={{ background: 'rgba(55,93,251,0.1)', border: '1px solid rgba(55,93,251,0.2)' }}
                  >
                    <a.icon size={14} style={{ color: '#375DFB' }} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-slate-200">{a.label}</p>
                    <p className="text-xs" style={{ color: '#475569' }}>{a.desc}</p>
                  </div>
                  <ArrowRight size={13} style={{ color: '#334155' }} />
                </Link>
              ))}
            </div>

            {/* Tonder branding pill */}
            <div
              className="mt-5 p-3 rounded-xl"
              style={{ background: 'rgba(55,93,251,0.06)', border: '1px solid rgba(55,93,251,0.12)' }}
            >
              <TonderWordmark height={28} onDark={true} />
              <p className="text-xs mt-1.5" style={{ color: '#334155' }}>v1.0 · Uso interno</p>
            </div>
          </div>
        </div>

        {/* ── Recent processes table ── */}
        <div
          className="rounded-2xl overflow-hidden"
          style={{ background: 'var(--tonder-surface)', border: '1px solid rgba(255,255,255,0.06)' }}
        >
          <div
            className="px-6 py-4 flex items-center justify-between"
            style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}
          >
            <div className="flex items-center gap-2.5">
              <Activity size={15} style={{ color: '#375DFB' }} />
              <h2
                className="text-sm font-semibold text-white"
                style={{ fontFamily: "'Plus Jakarta Sans', sans-serif" }}
              >
                Corridas recientes
              </h2>
            </div>
            <Link
              to="/processes"
              className="text-xs font-medium flex items-center gap-1 transition-colors"
              style={{ color: '#475569' }}
              onMouseEnter={e => e.currentTarget.style.color = '#7b95fd'}
              onMouseLeave={e => e.currentTarget.style.color = '#475569'}
            >
              Ver todas <ArrowRight size={11} />
            </Link>
          </div>

          {isLoading ? (
            <div className="flex items-center justify-center py-14">
              <Loader2 size={22} className="animate-spin" style={{ color: '#334155' }} />
            </div>
          ) : recent.length === 0 ? (
            <div className="text-center py-14">
              <div
                className="w-12 h-12 rounded-2xl flex items-center justify-center mx-auto mb-3"
                style={{ background: 'rgba(55,93,251,0.08)', border: '1px solid rgba(55,93,251,0.15)' }}
              >
                <TrendingUp size={20} style={{ color: '#375DFB' }} />
              </div>
              <p className="text-sm font-medium text-slate-400 mb-1">Sin corridas registradas</p>
              <p className="text-xs mb-4" style={{ color: '#334155' }}>Crea tu primera corrida contable</p>
              <Link to="/processes/new" className="btn-primary text-xs">
                Comenzar ahora
              </Link>
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                  {['Nombre', 'Período', 'Estado', 'Progreso', 'Creado', ''].map(h => (
                    <th
                      key={h}
                      className="text-left px-6 py-3 text-xs font-semibold uppercase tracking-wider"
                      style={{ color: '#334155' }}
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {recent.map((p, i) => (
                  <tr
                    key={p.id}
                    className="transition-colors table-row-hover"
                    style={{ borderBottom: i < recent.length - 1 ? '1px solid rgba(255,255,255,0.03)' : 'none' }}
                  >
                    <td className="px-6 py-3.5">
                      <p className="font-semibold text-slate-200 text-sm">{p.name}</p>
                    </td>
                    <td className="px-6 py-3.5">
                      <div
                        className="inline-flex items-center gap-1.5 px-2 py-1 rounded-lg text-xs font-medium"
                        style={{ background: 'rgba(255,255,255,0.04)', color: '#64748b' }}
                      >
                        <Calendar size={11} />
                        {p.period_year}-{String(p.period_month).padStart(2, '0')}
                      </div>
                    </td>
                    <td className="px-6 py-3.5">
                      <StatusBadge status={p.status} />
                    </td>
                    <td className="px-6 py-3.5">
                      <div className="flex items-center gap-2.5">
                        <div
                          className="w-24 h-1.5 rounded-full overflow-hidden"
                          style={{ background: 'rgba(255,255,255,0.06)' }}
                        >
                          <div
                            className="h-full rounded-full transition-all duration-500"
                            style={{
                              width: `${p.progress}%`,
                              background: p.status === 'failed'
                                ? '#ef4444'
                                : p.status === 'completed'
                                ? '#10b981'
                                : 'linear-gradient(90deg, #375DFB, #818cf8)',
                            }}
                          />
                        </div>
                        <span className="text-xs font-medium" style={{ color: '#475569' }}>
                          {p.progress}%
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-3.5">
                      <div className="flex items-center gap-1.5 text-xs" style={{ color: '#334155' }}>
                        <Clock size={11} />
                        {format(new Date(p.created_at), 'dd MMM, HH:mm', { locale: es })}
                      </div>
                    </td>
                    <td className="px-6 py-3.5">
                      <Link
                        to={`/processes/${p.id}`}
                        className="flex items-center gap-1 text-xs font-medium transition-colors"
                        style={{ color: '#475569' }}
                        onMouseEnter={e => e.currentTarget.style.color = '#7b95fd'}
                        onMouseLeave={e => e.currentTarget.style.color = '#475569'}
                      >
                        Abrir <ArrowRight size={11} />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  )
}
