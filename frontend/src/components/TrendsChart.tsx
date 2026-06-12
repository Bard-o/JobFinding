import { useEffect, useState } from 'react'
import ReactECharts from 'echarts-for-react'
import { api } from '@/lib/api'
import type { TrendPoint } from '@/types'

export default function TrendsChart() {
  const [trends, setTrends] = useState<Record<string, TrendPoint[]>>({})

  useEffect(() => {
    api.getTechnologyTrends(30).then((data) => {
      setTrends(data.trends || {})
    })
  }, [])

  // Get top 5 technologies with most data points
  const topTechs = Object.entries(trends)
    .sort((a, b) => b[1].length - a[1].length)
    .slice(0, 5)

  if (topTechs.length === 0) {
    return (
      <div className="h-[300px] flex items-center justify-center text-muted">
        Cargando tendencias...
      </div>
    )
  }

  const dates = [...new Set(topTechs.flatMap((t) => t[1].map((d) => d.date)))].sort()

  const option = {
    tooltip: { trigger: 'axis' as const },
    legend: {
      data: topTechs.map((t) => t[0]),
      textStyle: { color: '#a3a3a3' },
    },
    xAxis: {
      type: 'category' as const,
      data: dates,
      boundaryGap: false,
      axisLabel: { color: '#a3a3a3' },
      axisLine: { lineStyle: { color: '#262626' } },
    },
    yAxis: {
      type: 'value' as const,
      name: 'Ofertas',
      nameTextStyle: { color: '#a3a3a3' },
      axisLabel: { color: '#a3a3a3' },
      splitLine: { lineStyle: { color: '#262626' } },
    },
    series: topTechs.map(([name, points]) => ({
      name,
      type: 'line' as const,
      data: dates.map((date) => {
        const p = points.find((pt) => pt.date === date)
        return p ? p.count : 0
      }),
      smooth: true,
    })),
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
  }

  return <ReactECharts option={option} style={{ height: 300 }} />
}