import type { Summary, Technology, TechnologyTrends, Job, PaginatedJobs, SeniorityDistribution } from '@/types'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

async function fetchApi<T>(endpoint: string): Promise<T> {
  const res = await fetch(`${API_BASE}${endpoint}`)
  if (!res.ok) throw new Error(`API error: ${res.status}`)
  return res.json() as Promise<T>
}

export const api = {
  getSummary: (): Promise<Summary> => fetchApi<Summary>('/summary'),
  getTechnologies: (): Promise<Technology[]> => fetchApi<Technology[]>('/technologies'),
  getTechnologyTrends: (days = 30): Promise<TechnologyTrends> =>
    fetchApi<TechnologyTrends>(`/technologies/trends?days=${days}`),
  getJobs: (params: {
    page?: number
    page_size?: number
    tech?: string
    seniority?: string
    work_type?: string
    country?: string
  }): Promise<PaginatedJobs> => {
    const qs = new URLSearchParams(
      Object.entries(params)
        .filter(([, v]) => v !== undefined && v !== '')
        .map(([k, v]) => [k, String(v)])
    ).toString()
    return fetchApi<PaginatedJobs>(`/jobs?${qs}`)
  },
  getJobDetail: (id: number): Promise<Job> => fetchApi<Job>(`/jobs/${id}`),
  getSeniorityDistribution: (): Promise<SeniorityDistribution> =>
    fetchApi<SeniorityDistribution>('/seniority/distribution'),
}