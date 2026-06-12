import { useEffect, useState } from 'react'
import { api } from '@/lib/api'
import type { Job, PaginatedJobs } from '@/types'

const TECH_OPTIONS = ['Python', 'JavaScript', 'React', 'Java', 'Go', 'AWS', 'TypeScript', 'Node.js']
const SENIORITY_OPTIONS = ['junior', 'mid', 'senior', 'lead']
const WORK_TYPE_OPTIONS = ['remote', 'hybrid', 'onsite']

interface JobsFilters {
  tech: string
  seniority: string
  work_type: string
}

type BadgeVariant = 'default' | 'accent' | 'muted'

function Badge({ children, variant = 'default' }: { children: React.ReactNode; variant?: BadgeVariant }) {
  const base = 'px-2.5 py-0.5 rounded-full text-xs font-semibold'
  const variants: Record<BadgeVariant, string> = {
    default: 'bg-white/20 text-white',
    accent: 'bg-accent/20 text-accent',
    muted: 'bg-neutral-800 text-neutral-300',
  }
  return <span className={`${base} ${variants[variant]}`}>{children}</span>
}

const SENIORITY_BADGES: Record<string, BadgeVariant> = {
  senior: 'accent',
  lead: 'accent',
  mid: 'default',
  junior: 'default',
}

const WORKTYPE_BADGES: Record<string, BadgeVariant> = {
  remote: 'accent',
  hybrid: 'default',
  onsite: 'muted',
}

export default function JobsTable() {
  const [jobs, setJobs] = useState<Job[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize] = useState(10)
  const [filters, setFilters] = useState<JobsFilters>({ tech: '', seniority: '', work_type: '' })
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    setLoading(true)
    api
      .getJobs({ page, page_size: pageSize, ...filters })
      .then((data: PaginatedJobs) => {
        setJobs(data.items || [])
        setTotal(data.total || 0)
      })
      .finally(() => setLoading(false))
  }, [page, pageSize, filters])

  const totalPages = Math.ceil(total / pageSize)

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <select
          className="bg-card border border-border rounded-lg px-3 py-2 text-sm text-card-foreground focus:outline-none focus:border-accent transition-colors"
          value={filters.tech}
          onChange={(e) => {
            setFilters((f) => ({ ...f, tech: e.target.value }))
            setPage(1)
          }}
        >
          <option value="">Todas las tecnologías</option>
          {TECH_OPTIONS.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>

        <select
          className="bg-card border border-border rounded-lg px-3 py-2 text-sm text-card-foreground focus:outline-none focus:border-accent transition-colors"
          value={filters.seniority}
          onChange={(e) => {
            setFilters((f) => ({ ...f, seniority: e.target.value }))
            setPage(1)
          }}
        >
          <option value="">Todos los niveles</option>
          {SENIORITY_OPTIONS.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>

        <select
          className="bg-card border border-border rounded-lg px-3 py-2 text-sm text-card-foreground focus:outline-none focus:border-accent transition-colors"
          value={filters.work_type}
          onChange={(e) => {
            setFilters((f) => ({ ...f, work_type: e.target.value }))
            setPage(1)
          }}
        >
          <option value="">Todas las modalidades</option>
          {WORK_TYPE_OPTIONS.map((w) => (
            <option key={w} value={w}>
              {w}
            </option>
          ))}
        </select>
      </div>

      {/* List */}
      {loading ? (
        <div className="text-center py-12 text-muted">Cargando...</div>
      ) : jobs.length === 0 ? (
        <div className="text-center py-12 text-muted border border-border rounded-lg">No hay ofertas</div>
      ) : (
        <div className="space-y-2">
          {jobs.map((job) => (
            <div
              key={job.id}
              className="bg-card border border-border rounded-lg p-4 hover:border-orange-500/50 transition-colors cursor-pointer"
              onClick={() => window.open(job.url, '_blank')}
            >
              <div className="flex flex-col sm:flex-row justify-between gap-4">
                {/* Left: title + company */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-sm font-bold text-white tracking-wider truncate">{job.title}</span>
                  </div>
                  <div className="text-xs text-muted font-mono mb-2">{job.company}</div>
                  {/* Tags row */}
                  <div className="flex flex-wrap gap-2">
                    {job.country && <Badge variant="muted">{job.country}</Badge>}
                    {job.work_type && <Badge variant={WORKTYPE_BADGES[job.work_type] || 'muted'}>{job.work_type}</Badge>}
                    {job.seniority && <Badge variant={SENIORITY_BADGES[job.seniority] || 'muted'}>{job.seniority}</Badge>}
                  </div>
                </div>

                {/* Right: metadata */}
                <div className="flex flex-col sm:items-end gap-2 text-xs text-muted">
                  {job.published_at && (
                    <span className="font-mono">{new Date(job.published_at).toLocaleDateString()}</span>
                  )}
                  <span className="text-accent hover:underline">Ver oferta →</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Pagination */}
      <div className="flex items-center justify-between pt-4 border-t border-border">
        <p className="text-sm text-muted">
          Mostrando {(page - 1) * pageSize + 1}-{Math.min(page * pageSize, total)} de {total}
        </p>
        <div className="flex gap-2">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="px-3 py-1.5 border border-border rounded-lg text-sm text-card-foreground disabled:opacity-50 hover:border-accent transition-colors"
          >
            Anterior
          </button>
          <span className="px-3 py-1.5 text-sm text-muted">
            Página {page} de {totalPages}
          </span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page >= totalPages}
            className="px-3 py-1.5 border border-border rounded-lg text-sm text-card-foreground disabled:opacity-50 hover:border-accent transition-colors"
          >
            Siguiente
          </button>
        </div>
      </div>
    </div>
  )
}