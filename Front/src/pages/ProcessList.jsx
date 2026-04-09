import React from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { processApi } from '../api/client'
import { Plus, Loader2 } from 'lucide-react'
import StatusBadge from '../components/ui/StatusBadge'
import { format } from 'date-fns'
import { es } from 'date-fns/locale'

export default function ProcessList() {
  const { data: processes = [], isLoading } = useQuery({
    queryKey: ['processes'],
    queryFn: () => processApi.list().then(r => r.data),
    refetchInterval: 8_000,
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
                {['ID', 'Nombre', 'Período', 'Adquirentes', 'Estado', 'Progreso', 'Creado', ''].map(h => (
                  <th key={h} className="text-left px-5 py-3 text-slate-400 font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {processes.map(p => (
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
                    <div className="flex items-center gap-2">
                      <div className="w-24 h-1.5 bg-slate-800 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-brand-500 rounded-full"
                          style={{ width: `${p.progress}%` }}
                        />
                      </div>
                      <span className="text-xs text-slate-400">{p.progress}%</span>
                    </div>
                  </td>
                  <td className="px-5 py-3 text-slate-500 text-xs">
                    {format(new Date(p.created_at), 'dd/MM/yyyy HH:mm', { locale: es })}
                  </td>
                  <td className="px-5 py-3">
                    <Link to={`/processes/${p.id}`} className="text-brand-400 hover:text-brand-300 text-xs font-medium">
                      Abrir →
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
