import React from 'react'
import { CheckCircle2, Loader2, XCircle, Clock, FileCheck, Upload, AlertCircle } from 'lucide-react'

const CONFIG = {
  completed: { label: 'Completado', className: 'badge-success', icon: CheckCircle2 },
  running:   { label: 'Ejecutando', className: 'badge-info',    icon: Loader2, spin: true },
  failed:    { label: 'Fallido',    className: 'badge-error',   icon: XCircle },
  pending:   { label: 'Pendiente',  className: 'badge-pending', icon: Clock },
  parsed:    { label: 'Parseado',   className: 'badge-success', icon: FileCheck },
  uploaded:  { label: 'Cargado',    className: 'badge-info',    icon: Upload },
  error:     { label: 'Error',      className: 'badge-error',   icon: AlertCircle },
  warning:   { label: 'Advertencia',className: 'badge-warning', icon: AlertCircle },
}

export default function StatusBadge({ status }) {
  const cfg = CONFIG[status] || { label: status, className: 'badge-pending', icon: Clock }
  const Icon = cfg.icon
  return (
    <span className={cfg.className}>
      <Icon size={10} className={cfg.spin ? 'animate-spin' : ''} />
      {cfg.label}
    </span>
  )
}
