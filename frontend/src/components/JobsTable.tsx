import { useEffect, useState } from 'react'
import { api } from '@/lib/api'
import type { Job, PaginatedJobs } from '@/types'

const TECH_OPTIONS = ['Python', 'JavaScript', 'React', 'Java', 'Go', 'AWS']
const SENIORITY_OPTIONS = ['junior', 'mid', 'senior', 'lead']
const WORK_TYPE_OPTIONS = ['remote', 'hybrid', 'onsite']

interface JobsFilters {
  tech: string
  seniority: string
  work_type: string
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
      <div className="flex flex-wrap gap-4">
        <select
          className="border rounded px-3 py-2"
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
          className="border rounded px-3 py-2"
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
          className="border rounded px-3 py-2"
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

      {/* Table */}
      {loading ? (
        <div className="text-center py-8 text-gray-500">Cargando...</div>
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-2 text-left text-sm font-medium text-gray-500">Título</th>
                <th className="px-4 py-2 text-left text-sm font-medium text-gray-500">Empresa</th>
                <th className="px-4 py-2 text-left text-sm font-medium text-gray-500">País</th>
                <th className="px-4 py-2 text-left text-sm font-medium text-gray-500">Seniority</th>
                <th className="px-4 py-2 text-left text-sm font-medium text-gray-500">Modalidad</th>
                <th className="px-4 py-2 text-left text-sm font-medium text-gray-500">Ver</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {jobs.map((job) => (
                <tr key={job.id} className="hover:bg-gray-50">
                  <td className="px-4 py-2 text-sm">{job.title}</td>
                  <td className="px-4 py-2 text-sm">{job.company}</td>
                  <td className="px-4 py-2 text-sm">{job.country || '-'}</td>
                  <td className="px-4 py-2 text-sm">
                    <span
                      className={`px-2 py-1 rounded text-xs ${
                        job.seniority === 'senior'
                          ? 'bg-blue-100 text-blue-800'
                          : job.seniority === 'mid'
                            ? 'bg-green-100 text-green-800'
                            : job.seniority === 'junior'
                              ? 'bg-yellow-100 text-yellow-800'
                              : 'bg-gray-100 text-gray-800'
                      }`}
                    >
                      {job.seniority || 'unknown'}
                    </span>
                  </td>
                  <td className="px-4 py-2 text-sm">{job.work_type || '-'}</td>
                  <td className="px-4 py-2 text-sm">
                    <a
                      href={job.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-600 hover:underline"
                    >
                      Ver
                    </a>
                  </td>
                </tr>
              ))}
              {jobs.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-gray-500">
                    No hay ofertas
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Pagination */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-gray-500">
          Mostrando {(page - 1) * pageSize + 1}-{Math.min(page * pageSize, total)} de {total}
        </p>
        <div className="flex gap-2">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="px-3 py-1 border rounded disabled:opacity-50"
          >
            Anterior
          </button>
          <span className="px-3 py-1">
            Página {page} de {totalPages}
          </span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page >= totalPages}
            className="px-3 py-1 border rounded disabled:opacity-50"
          >
            Siguiente
          </button>
        </div>
      </div>
    </div>
  )
}