import ReactECharts from 'echarts-for-react'
import type { Technology } from '@/types'

interface TopTechnologiesChartProps {
  data: Technology[]
}

export default function TopTechnologiesChart({ data }: TopTechnologiesChartProps) {
  const top10 = data.slice(0, 10)

  const option = {
    tooltip: { trigger: 'axis' as const },
    xAxis: {
      type: 'category' as const,
      data: top10.map((d) => d.name),
      axisLabel: { rotate: 30, fontSize: 10 },
    },
    yAxis: { type: 'value' as const, name: 'Ofertas' },
    series: [
      {
        type: 'bar' as const,
        data: top10.map((d) => d.count),
        itemStyle: { color: '#3b82f6' },
      },
    ],
    grid: { left: '3%', right: '4%', bottom: '15%', containLabel: true },
  }

  return <ReactECharts option={option} style={{ height: 300 }} />
}