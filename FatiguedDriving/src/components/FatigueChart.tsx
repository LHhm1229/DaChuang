import React from 'react';
import { Card } from './ui/card';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Area, AreaChart } from 'recharts';

interface FatigueChartProps {
  data: Array<{
    time: string;
    fatigueScore: number;
    blinkRate: number;
    eyeMovementSpeed?: number;
    eyeMovement?: {
      speed: number;
    };
    signalQuality: number;
    alertLevel: number | string;
  }>;
}

export function FatigueChart({ data }: FatigueChartProps) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* 疲劳度趋势图 */}
      <Card className="p-6">
        <h3 className="mb-4">疲劳度趋势</h3>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="time" />
              <YAxis domain={[0, 100]} />
              <Tooltip 
                formatter={(value) => [`${value}%`, '疲劳度']}
                labelFormatter={(label) => `时间: ${label}`}
              />
              <Area 
                type="monotone" 
                dataKey="fatigueScore" 
                stroke="#8884d8" 
                fill="#8884d8" 
                fillOpacity={0.3}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </Card>

      {/* 眨眼频率图 */}
      <Card className="p-6">
        <h3 className="mb-4">眨眼频率变化</h3>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="time" />
              <YAxis />
              <Tooltip 
                formatter={(value) => [`${value} 次/分钟`, '眨眼频率']}
                labelFormatter={(label) => `时间: ${label}`}
              />
              <Line 
                type="monotone" 
                dataKey="blinkRate" 
                stroke="#82ca9d" 
                strokeWidth={2}
                dot={{ fill: '#82ca9d' }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </Card>

      {/* 眼睑闭合比例图 */}
      <Card className="p-6">
        <h3 className="mb-4">眼睑闭合比例</h3>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="time" />
              <YAxis domain={[0, 100]} />
              <Tooltip 
                formatter={(value) => [`${value}%`, '闭合比例']}
                labelFormatter={(label) => `时间: ${label}`}
              />
              <Line 
                type="monotone" 
                dataKey="eyeMovementSpeed" 
                stroke="#ff7300" 
                strokeWidth={2}
                dot={{ fill: '#ff7300' }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </Card>

      {/* 传感器信号质量图 */}
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