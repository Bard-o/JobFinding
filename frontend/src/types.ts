export interface Summary {
  snapshot_date: string
  total_jobs: number
  total_companies: number
  jobs_by_source: Record<string, number>
  jobs_by_seniority: Record<string, number>
  jobs_by_work_type: Record<string, number>
  top_technologies: Technology[]
}

export interface Technology {
  name: string
  category: string
  count: number
}

export interface TechnologyTrends {
  days: number
  trends: Record<string, TrendPoint[]>
}

export interface TrendPoint {
  date: string
  count: number
}

export interface Job {
  id: number
  title: string
  company: string
  country: string | null
  published_at: string
  url: string
  work_type: string | null
  seniority: string | null
}

export interface PaginatedJobs {
  items: Job[]
  total: number
  page: number
  page_size: number
  pages: number
}

export interface SeniorityDistribution {
  distribution: Record<string, number>
  total: number
}