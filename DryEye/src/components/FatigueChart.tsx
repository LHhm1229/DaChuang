import React from 'react';
import { Card } from './ui/card';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Area, AreaChart } from 'recharts';

interface DryEyeChartProps {
  data: Array<{
    time: string;
    eyeHealthScore: number;
    blinkRate: number;
    eyeClosureRatio: number;
    signalQuality: number;
    alertLevel: number | string;
  }>;
}

export function DryEyeChart({ data }: DryEyeChartProps) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* 眼部健康趋势 */}
      <Card className="p-6">
        <h3 className="mb-4 font-semibold">眼部健康趋势</h3>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis 
                dataKey="time" 
                tick={{ fontSize: 12 }}
                tickLine={false}
                axisLine={false}
              />
              <YAxis 
                domain={[0, 100]} 
                tick={{ fontSize: 12 }}
                tickLine={false}
                axisLine={false}
              />
              <Tooltip 
                contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }}
                formatter={(value) => [`${value} 分`, '健康评分']}
                labelFormatter={(label) => `时间: ${label}`}
              />
              <Area 
                type="monotone" 
                dataKey="eyeHealthScore" 
                stroke="#8884d8" 
                fill="#8884d8" 
                fillOpacity={0.2}
                strokeWidth={2}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </Card>

      {/* 眨眼频率趋势 */}
      <Card className="p-6">
        <h3 className="mb-4 font-semibold">眨眼频率趋势</h3>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis 
                dataKey="time" 
                tick={{ fontSize: 12 }}
                tickLine={false}
                axisLine={false}
              />
              <YAxis 
                tick={{ fontSize: 12 }}
                tickLine={false}
                axisLine={false}
              />
              <Tooltip 
                contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }}
                formatter={(value) => [`${value} 次/分钟`, '眨眼频率']}
                labelFormatter={(label) => `时间: ${label}`}
              />
              <Line 
                type="monotone" 
                dataKey="blinkRate" 
                stroke="#ff7300" 
                strokeWidth={3}
                dot={{ fill: '#ff7300', r: 4 }}
                activeDot={{ r: 6 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </Card>

      {/* 眼部稳定性变化 */}
      <Card className="p-6">
        <h3 className="mb-4 font-semibold">眼部稳定性变化 (稳定性)</h3>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis 
                dataKey="time" 
                tick={{ fontSize: 12 }}
                tickLine={false}
                axisLine={false}
              />
              <YAxis 
                domain={[0, 100]} 
                tick={{ fontSize: 12 }}
                tickLine={false}
                axisLine={false}
              />
              <Tooltip 
                contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }}
                formatter={(value) => [`${value}%`, '稳定性']}
                labelFormatter={(label) => `时间: ${label}`}
              />
              <Line 
                type="monotone" 
                dataKey="eyeClosureRatio" 
                stroke="#82ca9d" 
                strokeWidth={3}
                dot={{ fill: '#82ca9d', r: 4 }}
                activeDot={{ r: 6 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </Card>

      {/* 传感器信号质量图 */}
      <Card className="p-6">
        <h3 className="mb-4 font-semibold">信号质量监控</h3>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis 
                dataKey="time" 
                tick={{ fontSize: 12 }}
                tickLine={false}
                axisLine={false}
              />
              <YAxis 
                domain={[0, 100]} 
                tick={{ fontSize: 12 }}
                tickLine={false}
                axisLine={false}
              />
              <Tooltip 
                contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }}
                formatter={(value) => [`${value}%`, '信号质量']}
                labelFormatter={(label) => `时间: ${label}`}
              />
              <Area 
                type="monotone" 
                dataKey="signalQuality" 
                stroke="#00C49F" 
                fill="#00C49F" 
                fillOpacity={0.2}
                strokeWidth={2}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </Card>
    </div>
  );
}
