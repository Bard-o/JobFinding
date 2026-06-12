import { useState, useEffect } from 'react'
import type { Summary } from '@/types'
import { api } from '@/lib/api'
import SummaryCards from '@/components/SummaryCards'
import TopTechnologiesChart from '@/components/TopTechnologiesChart'
import SeniorityPieChart from '@/components/SeniorityPieChart'
import WorkTypeChart from '@/components/WorkTypeChart'
import TrendsChart from '@/components/TrendsChart'
import JobsTable from '@/components/JobsTable'

function App() {
  const [summary, setSummary] = useState<Summary | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api
      .getSummary()
      .then(setSummary)
      .catch(() => setError('No se pudo cargar el dashboard'))
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-lg text-gray-500">Cargando dashboard...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-lg text-red-500">{error}</div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <header className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">JobFinding Dashboard</h1>
        <p className="text-gray-500">Mercado laboral tech en LATAM</p>
      </header>

      <div className="space-y-6">
        {/* Summary Cards */}
        <SummaryCards data={summary} />

        {/* Charts Row */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          <div className="bg-white rounded-lg shadow p-4">
            <h2 className="text-lg font-semibold mb-4">Top Tecnologías</h2>
            <TopTechnologiesChart data={summary?.top_technologies ?? []} />
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <h2 className="text-lg font-semibold mb-4">Seniority</h2>
            <SeniorityPieChart data={summary?.jobs_by_seniority ?? {}} />
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <h2 className="text-lg font-semibold mb-4">Modalidad</h2>
            <WorkTypeChart data={summary?.jobs_by_work_type ?? {}} />
          </div>
        </div>

        {/* Trends Chart */}
        <div className="bg-white rounded-lg shadow p-4">
          <h2 className="text-lg font-semibold mb-4">Tendencias</h2>
          <TrendsChart />
        </div>

        {/* Jobs Table */}
        <div className="bg-white rounded-lg shadow p-4">
          <h2 className="text-lg font-semibold mb-4">Ofertas de Empleo</h2>
          <JobsTable />
        </div>
      </div>
    </div>
  )
}

export default App