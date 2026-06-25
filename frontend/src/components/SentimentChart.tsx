'use client';

import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts';

export default function SentimentChart({ positive, neutral, negative }: { positive: number; neutral: number; negative: number }) {
  const data = [
    { name: 'Positive', value: positive, color: '#10B981' },
    { name: 'Neutral', value: neutral, color: '#6B7280' },
    { name: 'Negative', value: negative, color: '#EF4444' },
  ].filter(item => item.value > 0); // Hide 0 value items

  // Fallback state if no data exists yet
  if (data.length === 0) {
    return (
      <div className="h-48 flex items-center justify-center text-slate-400 text-sm">
        Gathering data points...
      </div>
    );
  }

  return (
    <div className="h-48 relative flex items-center justify-center">
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            innerRadius={60}
            outerRadius={80}
            paddingAngle={4}
            dataKey="value"
          >
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.color} />
            ))}
          </Pie>
          <Tooltip 
            contentStyle={{ backgroundColor: '#1e293b', border: 'none', borderRadius: '8px', color: '#fff' }}
            itemStyle={{ color: '#fff' }}
          />
        </PieChart>
      </ResponsiveContainer>
      
      {/* Legend overlays */}
      <div className="absolute flex flex-col space-y-1 text-xs font-medium right-2 bottom-2 bg-slate-50 p-2 rounded-lg border border-gray-100">
        {data.map((item) => (
          <div key={item.name} className="flex items-center space-x-2">
            <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: item.color }} />
            <span className="text-slate-600">{item.name}: {item.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}