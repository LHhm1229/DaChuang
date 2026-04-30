import React from 'react';
import { Card } from './ui/card';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Area, AreaChart } from 'recharts';

interface SleepChartProps {
  data: Array<{
    time: string;
    sleepScore: number;
    movementIndex: number;
    sleepStability: number;
    sleepStageValue: number;
    sleepStageLabel: string;
    signalQuality: number;
    alertLevel: number | string;
  }>;
}

const stageTickFormatter = (value: number) => {
  switch (value) {
    case 0: return '深睡';
    case 1: return '浅睡';
    case 2: return 'REM';
    case 3: return '清醒';
    default: return '';
  }
};

export function SleepChart({ data }: SleepChartProps) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* 睡眠质量趋势 */}
      <Card className="p-6">
        <h3 className="mb-4">睡眠质量趋势</h3>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="time" />
              <YAxis domain={[0, 100]} />
              <Tooltip 
                formatter={(value) => [`${value}%`, '睡眠质量']}
                labelFormatter={(label) => `时间: ${label}`}
              />
              <Area 
                type="monotone" 
                dataKey="sleepScore" 
                stroke="#8884d8" 
                fill="#8884d8" 
                fillOpacity={0.3}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </Card>

      {/* 睡眠阶段时间轴 */}
      <Card className="p-6">
        <h3 className="mb-4">睡眠阶段时间轴</h3>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="time" />
              <YAxis domain={[0, 3]} ticks={[0, 1, 2, 3]} tickFormatter={stageTickFormatter} />
              <Tooltip 
                formatter={(value) => [stageTickFormatter(value as number), '睡眠阶段']}
                labelFormatter={(label) => `时间: ${label}`}
              />
              <Line 
                type="monotone" 
                dataKey="sleepStageValue" 
                stroke="#ff7300" 
                strokeWidth={2}
                dot={{ fill: '#ff7300' }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </Card>

      {/* 体动指数变化 */}
      <Card className="p-6">
        <h3 className="mb-4">体动指数变化</h3>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="time" />
              <YAxis />
              <Tooltip 
                formatter={(value) => [`${value}`, '体动指数']}
                labelFormatter={(label) => `时间: ${label}`}
              />
              <Line 
                type="monotone" 
                dataKey="movementIndex" 
                stroke="#82ca9d" 
                strokeWidth={2}
                dot={{ fill: '#82ca9d' }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </Card>

      {/* 睡眠稳定性变化 */}
      <Card className="p-6">
        <h3 className="mb-4">睡眠稳定性变化</h3>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="time" />
              <YAxis domain={[0, 100]} />
              <Tooltip 
                formatter={(value) => [`${value}%`, '稳定性']}
                labelFormatter={(label) => `时间: ${label}`}
              />
              <Area 
                type="monotone" 
                dataKey="sleepStability" 
                stroke="#ff7300" 
                fill="#ff7300" 
                fillOpacity={0.3}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </Card>

      {/* 信号质量监控 */}
      <Card className="p-6">
        <h3 className="mb-4">信号质量监控</h3>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="time" />
              <YAxis domain={[0, 100]} />
              <Tooltip 
                formatter={(value) => [`${value}%`, '信号质量']}
                labelFormatter={(label) => `时间: ${label}`}
              />
              <Area 
                type="monotone" 
                dataKey="signalQuality" 
                stroke="#00C49F" 
                fill="#00C49F" 
                fillOpacity={0.3}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </Card>
    </div>
  );
}
