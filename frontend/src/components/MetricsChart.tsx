import React from 'react';
import { BarChart, Bar, XAxis, Tooltip, ResponsiveContainer, AreaChart, Area, LineChart, Line, YAxis } from 'recharts';

interface MetricsChartProps {
  nodeLoad: Array<{ name: string; keys: number }>;
  trafficHistory: Array<{ time: string; hits: number; misses: number }>;
  latencyHistory: Array<{ time: string; latency: number }>;
  hitRate: number;
  totalRequests: number;
}

const MetricsChart: React.FC<MetricsChartProps> = ({ 
  nodeLoad, 
  trafficHistory, 
  latencyHistory,
  hitRate, 
  totalRequests 
}) => {
  // Custom dark tooltip
  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-zinc-900 border border-zinc-800 px-3 py-2 rounded shadow-lg">
          <p className="text-zinc-200 text-xs font-mono mb-1">{label}</p>
          {payload.map((entry: any, index: number) => (
            <p key={index} className="text-xs" style={{ color: entry.color }}>
              {entry.name}: {entry.value}
            </p>
          ))}
        </div>
      );
    }
    return null;
  };

  return (
    <div className="bg-zinc-900 rounded-md border border-zinc-800 p-5 h-full space-y-4">
      {/* Header */}
      <div className="flex justify-between items-baseline">
        <div className="text-[10px] uppercase tracking-widest text-zinc-600 font-medium">Performance</div>
        <div className="text-right">
          <div className="text-2xl font-bold text-white font-mono">{hitRate.toFixed(0)}%</div>
          <div className="text-[10px] text-zinc-500">{totalRequests.toLocaleString()} requests</div>
        </div>
      </div>

      {/* Traffic Monitor (Area Chart) */}
      <div>
        <div className="text-[10px] text-zinc-500 mb-2 uppercase tracking-wider">Traffic Monitor</div>
        <ResponsiveContainer width="100%" height={80}>
          <AreaChart data={trafficHistory}>
            <defs>
              <linearGradient id="colorHits" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#10b981" stopOpacity={0.3}/>
                <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
              </linearGradient>
              <linearGradient id="colorMisses" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3}/>
                <stop offset="95%" stopColor="#ef4444" stopOpacity={0}/>
              </linearGradient>
            </defs>
            <XAxis 
              dataKey="time" 
              stroke="#71717a" 
              style={{ fontSize: 9, fontFamily: 'monospace' }}
              tickLine={false}
              axisLine={false}
            />
            <Tooltip content={<CustomTooltip />} />
            <Area 
              type="monotone" 
              dataKey="hits" 
              stroke="#10b981" 
              fillOpacity={1} 
              fill="url(#colorHits)"
              strokeWidth={1.5}
            />
            <Area 
              type="monotone" 
              dataKey="misses" 
              stroke="#ef4444" 
              fillOpacity={1} 
              fill="url(#colorMisses)"
              strokeWidth={1.5}
            />
          </AreaChart>
        </ResponsiveContainer>
        <div className="flex gap-3 mt-2 text-[10px] font-mono">
          <div className="flex items-center gap-1">
            <div className="w-2 h-2 bg-emerald-500 rounded-full"></div>
            <span className="text-zinc-500">Hits</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-2 h-2 bg-red-500 rounded-full"></div>
            <span className="text-zinc-500">Misses</span>
          </div>
        </div>
      </div>

      {/* Load Distribution (Bar Chart) */}
      <div className="pt-3 border-t border-zinc-800">
        <div className="text-[10px] text-zinc-500 mb-2 uppercase tracking-wider">Node Load</div>
        <ResponsiveContainer width="100%" height={100}>
          <BarChart data={nodeLoad}>
            <XAxis 
              dataKey="name" 
              stroke="#71717a" 
              style={{ fontSize: 10, fontFamily: 'monospace' }}
              tickLine={false}
              axisLine={false}
            />
            <Tooltip content={<CustomTooltip />} />
            <Bar dataKey="keys" fill="#e4e4e7" radius={[2, 2, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Latency Monitor (Line Chart) */}
      {latencyHistory.length > 0 && (
        <div className="pt-3 border-t border-zinc-800">
          <div className="text-[10px] text-zinc-500 mb-2 uppercase tracking-wider">Response Latency</div>
          <ResponsiveContainer width="100%" height={80}>
            <LineChart data={latencyHistory}>
              <XAxis 
                dataKey="time" 
                stroke="#71717a" 
                style={{ fontSize: 9, fontFamily: 'monospace' }}
                tickLine={false}
                axisLine={false}
              />
              <YAxis 
                stroke="#71717a" 
                style={{ fontSize: 9, fontFamily: 'monospace' }}
                tickLine={false}
                axisLine={false}
                width={35}
              />
              <Tooltip content={<CustomTooltip />} />
              <Line 
                type="monotone" 
                dataKey="latency" 
                stroke="#3b82f6" 
                strokeWidth={2}
                dot={false}
                name="Latency (ms)"
              />
            </LineChart>
          </ResponsiveContainer>
          <div className="flex items-center gap-1 mt-2 text-[10px] font-mono">
            <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
            <span className="text-zinc-500">Response Time (ms)</span>
          </div>
        </div>
      )}
    </div>
  );
};

export default MetricsChart;
