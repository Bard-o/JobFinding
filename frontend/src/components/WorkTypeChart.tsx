import ReactECharts from 'echarts-for-react'

interface WorkTypeChartProps {
  data: Record<string, number>
}

const COLORS: Record<string, string> = {
  remote: '#22c55e',
  hybrid: '#f59e0b',
  onsite: '#ef4444',
  unknown: '#9ca3af',
}

export default function WorkTypeChart({ data }: WorkTypeChartProps) {
  const entries = Object.entries(data).filter(([, v]) => v > 0)

  const option = {
    tooltip: { trigger: 'item' as const },
    series: [
      {
        type: 'pie' as const,
        radius: '60%',
        data: entries.map(([name, value]) => ({
          name,
          value,
          itemStyle: { color: COLORS[name] || '#6b7280' },
        })),
        emphasis: {
          itemStyle: { shadowBlur: 10, shadowOffsetX: 0, shadowColor: 'rgba(0, 0, 0, 0.5)' },
        },
      },
    ],
  }

  return <ReactECharts option={option} style={{ height: 300 }} />
}