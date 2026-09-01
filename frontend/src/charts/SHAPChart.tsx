import { BarChart, Bar, XAxis, YAxis, Cell, ResponsiveContainer, ReferenceLine, Tooltip } from 'recharts'
import type { ShapContribution } from '@/types'

export function SHAPChart({ contributions }: { contributions: ShapContribution[] }) {
  const sorted = [...contributions].sort((a, b) => Math.abs(b.contribution) - Math.abs(a.contribution))
  const data = sorted.map((c) => ({ name: c.feature, contribution: Number(c.contribution.toFixed(3)) }))

  return (
    <div className="h-72 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} layout="vertical" margin={{ left: 8, right: 24, top: 8, bottom: 8 }}>
          <XAxis type="number" tick={{ fill: 'rgba(255,255,255,0.4)', fontSize: 11 }} axisLine={false} tickLine={false} />
          <YAxis
            type="category"
            dataKey="name"
            width={90}
            tick={{ fill: 'rgba(255,255,255,0.7)', fontSize: 12 }}
            axisLine={false}
            tickLine={false}
          />
          <ReferenceLine x={0} stroke="rgba(255,255,255,0.2)" />
          <Tooltip
            cursor={{ fill: 'rgba(255,255,255,0.04)' }}
            contentStyle={{
              background: '#0b2c1c',
              border: '1px solid rgba(255,255,255,0.1)',
              borderRadius: 12,
              fontSize: 12,
              color: '#fff',
            }}
            formatter={(value) => [typeof value === 'number' ? value.toFixed(3) : String(value), 'SHAP contribution']}
          />
          <Bar dataKey="contribution" radius={[4, 4, 4, 4]}>
            {data.map((entry) => (
              <Cell key={entry.name} fill={entry.contribution >= 0 ? '#34d399' : '#fb7185'} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
