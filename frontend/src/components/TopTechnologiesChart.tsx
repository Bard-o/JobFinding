import type { Technology } from '@/types'

interface TopTechnologiesChartProps {
  data: Technology[]
}

export default function TopTechnologiesChart({ data }: TopTechnologiesChartProps) {
  const top10 = data.slice(0, 10)
  const maxCount = Math.max(...top10.map((d) => d.count), 1)

  if (top10.length === 0) {
    return (
      <div className="h-[300px] flex items-center justify-center text-muted">
        No hay datos
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {top10.map((tech) => {
        const pct = (tech.count / maxCount) * 100
        return (
          <div key={tech.name} className="space-y-1">
            <div className="flex justify-between text-xs">
              <span className="text-muted font-medium tracking-wide uppercase">{tech.name}</span>
              <span className="text-white font-mono">{tech.count}</span>
            </div>
            <div className="w-full bg-neutral-800 rounded-full h-2">
              <div
                className="bg-accent h-2 rounded-full transition-all duration-300"
                style={{ width: `${pct}%` }}
              />
            </div>
          </div>
        )
      })}
    </div>
  )
}