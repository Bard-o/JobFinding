import ReactECharts from 'echarts-for-react'

interface SeniorityPieChartProps {
  data: Record<string, number>
}

const COLORS: Record<string, string> = {
  junior: '#22c55e',
  mid: '#3b82f6',
  senior: '#f59e0b',
  lead: '#ef4444',
  unknown: '#9ca3af',
}

export default function SeniorityPieChart({ data }: SeniorityPieChartProps) {
  const entries = Object.entries(data).filter(([, v]) => v > 0)

  const option = {
    tooltip: { trigger: 'item' as const },
    legend: { orient: 'vertical' as const, left: 'left' as const },
    series: [
      {
        type: 'pie' as const,
        radius: ['40%', '70%'],
        avoidLabelOverlap: false,
        itemStyle: { borderRadius: 10, borderColor: '#fff', borderWidth: 2 },
        label: { show: true, formatter: '{b}: {c}' },
        data: entries.map(([name, value]) => ({
          name,
          value,
          itemStyle: { color: COLORS[name] || '#6b7280' },
        })),
      },
    ],
  }

  return <ReactECharts option={option} style={{ height: 300 }} />
}