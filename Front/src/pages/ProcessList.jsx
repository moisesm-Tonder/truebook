import React, { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { processApi } from '../api/client'
import { Plus, Loader2, Trash2, AlertTriangle } from 'lucide-react'
import StatusBadge from '../components/ui/StatusBadge'
import { format } from 'date-fns'
import { es } from 'date-fns/locale'

function getConciliationView(process) {
  const parsedPercent = Number(process?.conciliation_percent)
  const fallback = process?.status === 'completed'
    ? 0
    : Number(process?.progress || 0)
  const percent = Number.isFinite(parsedPercent)
    ? Math.max(0, Math.min(100, parsedPercent))
    : Math.max(0, Math.min(100, fallback))

  const state = process?.conciliation_state || (
    process?.status === 'completed'
      ? (percent >= 100 ? 'success' : 'warning')
      : 'processing'
  )
  const message = process?.conciliation_message || (
    state === 'success'
      ? 'Conciliado'
      : state === 'warning'
      ? 'Validando conciliación'
      : 'En proceso'
  )

  const barClass = state === 'success'
    ? 'bg-emerald-500'
    : state === 'warning'
    ? 'bg-amber-400'
    : 'bg-brand-500'

  const textClass = state === 'success'
    ? 'text-emerald-400'
    : state === 'warning'
    ? 'text-amber-400'
    : 'text-slate-400'

  const percentLabel = Number.isInteger(percent) ? `${percent}%` : `${percent.toFixed(1)}%`

  return { percent, state, message, barClass, textClass, percentLabel }
}

export default function ProcessList() {
  const qc = useQueryClient()
  const [confirmId, setConfirmId] = useState(null)

  const { data: processes = [], isLoading } = useQuery({
    queryKey: ['processes'],
    queryFn: () => processApi.list().then(r => r.data),
    refetchInterval: 8_000,
  })

  const deleteMutation = useMutation({
    mutationFn: (id) => processApi.delete(id),
    onSuccess: () => {
      qc.invalidateQueries(['processes'])
      setConfirmId(null)
    },
  })

  return (
    <div className="p-8 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Proceso Contable</h1>
          <p className="text-slate-400 text-sm mt-1">Historial de corridas de cierre mensual</p>
        </div>
        <Link to="/processes/new" className="btn-primary flex items-center gap-2">
          <Plus size={16} />
          Nueva corrida
        </Link>
      </div>

      <div className="card p-0 overflow-hidden">
        {isLoading ? (
          <div className="flex items-center justify-center py-16">
            <Loader2 size={24} className="animate-spin text-slate-500" />
          </div>
        ) : processes.length === 0 ? (
          <div className="text-center py-16">
            <p className="text-slate-500">No hay corridas registradas.</p>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead className="border-b border-slate-800 bg-slate-900/50">
              <tr>
                {['ID', 'Nombre', 'Período', 'Adquirentes', 'Estado', 'Conciliación', 'Creado', ''].map(h => (
                  <th key={h} className="text-left px-5 py-3 text-slate-400 font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {processes.map(p => {
                const conc = getConciliationView(p)
                return (
                <tr key={p.id} className="border-b border-slate-800/50 hover:bg-slate-800/20 transition-colors">
                  <td className="px-5 py-3 text-slate-500">#{p.id}</td>
                  <td className="px-5 py-3 text-slate-200 font-medium">{p.name}</td>
                  <td className="px-5 py-3 text-slate-300">
                    {p.period_year}-{String(p.period_month).padStart(2, '0')}
                  </td>
                  <td className="px-5 py-3">
                    <div className="flex flex-wrap gap-1">
                      {(p.acquirers || []).map(a => (
                        <span key={a} className="text-xs bg-slate-800 text-slate-400 px-1.5 py-0.5 rounded">
                          {a}
                        </span>
                      ))}
                    </div>
                  </td>
                  <td className="px-5 py-3"><StatusBadge status={p.status} /></td>
                  <td className="px-5 py-3">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <div className="w-24 h-1.5 bg-slate-800 rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full ${conc.barClass}`}
                            style={{ width: `${conc.percent}%` }}
                          />
                        </div>
                        <span className={`text-xs ${conc.textClass}`}>{conc.percentLabel}</span>
                      </div>
                      {conc.state === 'warning' && (
                        <div className="flex items-center gap-1 text-[11px] text-amber-400">
                          <AlertTriangle size={11} />
                          <span>{conc.message}</span>
                        </div>
                      )}
                    </div>
                  </td>
                  <td className="px-5 py-3 text-slate-500 text-xs">
                    {format(new Date(p.created_at), 'dd/MM/yyyy HH:mm', { locale: es })}
                  </td>
                  <td className="px-5 py-3">
                    <div className="flex items-center gap-3">
                      <Link to={`/processes/${p.id}`} className="text-brand-400 hover:text-brand-300 text-xs font-medium">
                        Abrir →
                      </Link>
                      {p.status !== 'running' && (
                        confirmId === p.id ? (
                          <div className="flex items-center gap-1">
                            <button
                              onClick={() => deleteMutation.mutate(p.id)}
                              disabled={deleteMutation.isPending}
                              className="text-xs text-red-400 hover:text-red-300 font-medium"
                            >
                              {deleteMutation.isPending ? <Loader2 size={12} className="animate-spin" /> : 'Confirmar'}
                            </button>
                            <span className="text-slate-700">·</span>
                            <button
                              onClick={() => setConfirmId(null)}
                              className="text-xs text-slate-500 hover:text-slate-400"
                            >
                              Cancelar
                            </button>
                          </div>
                        ) : (
                          <button
                            onClick={() => setConfirmId(p.id)}
                            className="text-slate-600 hover:text-red-400 transition-colors"
                          >
                            <Trash2 size={14} />
                          </button>
                        )
                      )}
                    </div>
                  </td>
                </tr>
              )})}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
