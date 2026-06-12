import { api } from '@/lib/api'
import { useEffect, useState } from 'react'
import type { Summary } from '@/types'

interface SummaryCardsProps {
  data: Summary | null
}

export default function SummaryCards({ data }: SummaryCardsProps) {
  const [techCount, setTechCount] = useState(0)

  useEffect(() => {
    api.getTechnologies().then((techs) => setTechCount(techs.length))
  }, [])

  const cards = [
    {
      label: 'Total Ofertas',
      value: data?.total_jobs ?? 0,
      icon: '💼',
    },
    {
      label: 'Empresas',
      value: data?.total_companies ?? 0,
      icon: '🏢',
    },
    {
      label: 'Tecnologías',
      value: techCount,
      icon: '🛠️',
    },
  ]

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
      {cards.map((card) => (
        <div key={card.label} className="bg-white rounded-lg shadow p-6 flex items-center gap-4">
          <span className="text-4xl">{card.icon}</span>
          <div>
            <p className="text-sm text-gray-500">{card.label}</p>
            <p className="text-3xl font-bold">{card.value.toLocaleString()}</p>
          </div>
        </div>
      ))}
    </div>
  )
}