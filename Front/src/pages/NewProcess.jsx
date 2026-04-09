import React, { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { processApi } from '../api/client'
import { Loader2, ChevronRight, Calendar, Cpu } from 'lucide-react'

const MONTHS = [
  'Enero','Febrero','Marzo','Abril','Mayo','Junio',
  'Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre'
]
const ACQUIRERS = ['OXXOPay', 'Bitso', 'Kushki', 'STP']

const ACQ_COLORS = {
  OXXOPay: '#f59e0b',
  Bitso:   '#10b981',
  Kushki:  '#375DFB',
  STP:     '#8b5cf6',
}

export default function NewProcess() {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const now = new Date()

  const [form, setForm] = useState({
    name: `Cierre ${MONTHS[now.getMonth()]} ${now.getFullYear()}`,
    period_year: now.getFullYear(),
    period_month: now.getMonth() + 1,
    acquirers: [...ACQUIRERS],
  })

  const mutation = useMutation({
    mutationFn: () => processApi.create(form),
    onSuccess: ({ data }) => {
      qc.invalidateQueries(['processes'])
      navigate(`/processes/${data.id}`)
    },
  })

  function toggleAcquirer(a) {
    setForm(f => ({
      ...f,
      acquirers: f.acquirers.includes(a)
        ? f.acquirers.filter(x => x !== a)
        : [...f.acquirers, a],
    }))
  }

  return (
    <div className="min-h-screen" style={{ background: 'var(--tonder-bg)' }}>
      {/* Top bar */}
      <div className="px-8 py-5" style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
        <div className="flex items-center gap-2 text-xs mb-1" style={{ color: '#334155' }}>
          <Link to="/processes" className="hover:text-slate-400 transition-colors">Proceso Contable</Link>
          <ChevronRight size={12} />
          <span style={{ color: '#64748b' }}>Nueva corrida</span>
        </div>
        <h1
          className="text-xl font-bold text-white"
          style={{ fontFamily: "'Plus Jakarta Sans', sans-serif", letterSpacing: '-0.02em' }}
        >
          Nueva corrida contable
        </h1>
        <p className="text-sm mt-0.5" style={{ color: '#475569' }}>
          Configura el período y parámetros del cierre mensual
        </p>
      </div>

      <div className="px-8 py-6 max-w-2xl">
        <div
          className="rounded-2xl p-6 space-y-6"
          style={{ background: 'var(--tonder-surface)', border: '1px solid rgba(255,255,255,0.06)' }}
        >
          {/* Name */}
          <div>
            <label className="label">Nombre de la corrida</label>
            <input
              className="input"
              value={form.name}
              onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
              placeholder="Ej: Cierre Enero 2026"
            />
          </div>

          {/* Period */}
          <div>
            <label className="label flex items-center gap-1.5">
              <Calendar size={12} /> Período contable
            </label>
            <div className="grid grid-cols-2 gap-3">
              <select
                className="input"
                value={form.period_year}
                onChange={e => setForm(f => ({ ...f, period_year: parseInt(e.target.value) }))}
              >
                {[2024, 2025, 2026].map(y => (
                  <option key={y} value={y}>{y}</option>
                ))}
              </select>
              <select
                className="input"
                value={form.period_month}
                onChange={e => setForm(f => ({ ...f, period_month: parseInt(e.target.value) }))}
              >
                {MONTHS.map((m, i) => (
                  <option key={i + 1} value={i + 1}>{m}</option>
                ))}
              </select>
            </div>
            <p className="text-xs mt-2" style={{ color: '#334155' }}>
              Ventana: 1 {MONTHS[form.period_month - 1]} 00:00 UTC-6 → 31 {MONTHS[form.period_month - 1]} 23:59 UTC-6
            </p>
          </div>

          {/* Acquirers */}
          <div>
            <label className="label flex items-center gap-1.5">
              <Cpu size={12} /> Adquirentes a procesar
            </label>
            <div className="flex flex-wrap gap-2 mt-1">
              {ACQUIRERS.map(a => {
                const active = form.acquirers.includes(a)
                const color = ACQ_COLORS[a]
                return (
                  <button
                    key={a}
                    type="button"
                    onClick={() => toggleAcquirer(a)}
                    className="px-3.5 py-2 rounded-xl text-sm font-semibold transition-all"
                    style={active
                      ? { background: color + '18', border: `1px solid ${color}40`, color }
                      : { background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.07)', color: '#475569' }
                    }
                  >
                    {a}
                  </button>
                )
              })}
            </div>
            <p className="text-xs mt-2" style={{ color: '#334155' }}>
              {form.acquirers.length} de {ACQUIRERS.length} adquirentes seleccionados
            </p>
          </div>

          {mutation.error && (
            <div
              className="text-sm px-4 py-3 rounded-xl"
              style={{ background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.2)', color: '#f87171' }}
            >
              {mutation.error.response?.data?.detail || 'Error al crear la corrida'}
            </div>
          )}

          <div className="flex justify-end gap-3 pt-2">
            <button onClick={() => navigate(-1)} className="btn-secondary">
              Cancelar
            </button>
            <button
              onClick={() => mutation.mutate()}
              disabled={mutation.isPending || !form.name || form.acquirers.length === 0}
              className="btn-primary flex items-center gap-2"
            >
              {mutation.isPending
                ? <><Loader2 size={14} className="animate-spin" /> Creando...</>
                : <>Crear y continuar <ChevronRight size={14} /></>
              }
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
