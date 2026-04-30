import React, { useState, useEffect, useRef } from 'react';
import { GlassCard } from './ui/GlassCard';
import { Eye, Moon, Car } from 'lucide-react';

interface GatewayProps {
  onSelectModule: (module: 'dry-eye' | 'sleep' | 'fatigue') => void;
}

export const Gateway: React.FC<GatewayProps> = ({ onSelectModule }) => {
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 });
  const [activeCard, setActiveCard] = useState<string | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (containerRef.current) {
        const rect = containerRef.current.getBoundingClientRect();
        setMousePos({
          x: e.clientX - rect.left,
          y: e.clientY - rect.top
        });
      }
    };

    window.addEventListener('mousemove', handleMouseMove);
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, []);

  const modules = [
    {
      id: 'dry-eye',
      title: '干眼症风险监测',
      description: '实时监测眨眼频率和眼部状态，评估干眼风险',
      icon: Eye,
      color: '#16C79E',
      hoverGradient: 'from-white/[0.05] to-[#16C79E]/10'
    },
    {
      id: 'sleep',
      title: '睡眠质量分析',
      description: '分析睡眠阶段和眼动情况，评估睡眠质量',
      icon: Moon,
      color: '#6C5CE7',
      hoverGradient: 'from-white/[0.05] to-[#6C5CE7]/10'
    },
    {
      id: 'fatigue',
      title: '疲劳驾驶预警',
      description: '监测驾驶过程中的疲劳状态，及时发出预警',
      icon: Car,
      color: '#E86830',
      hoverGradient: 'from-white/[0.05] to-[#E86830]/10'
    }
  ];

  return (
    <div 
      ref={containerRef}
      className="min-h-screen relative overflow-hidden"
      style={{ backgroundColor: '#0B0F19' }}
    >
      {/* 动态环境光晕 */}
      <div className="absolute inset-0 overflow-hidden">
        <div 
          className="absolute w-[500px] h-[500px] rounded-full opacity-20 blur-[120px]"
          style={{ 
            backgroundColor: '#16C79E',
            top: '-10%',
            left: '-10%',
            animation: 'float1 20s ease-in-out infinite'
          }}
        ></div>
        <div 
          className="absolute w-[500px] h-[500px] rounded-full opacity-20 blur-[120px]"
          style={{ 
            backgroundColor: '#4F1091',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            animation: 'float2 25s ease-in-out infinite'
          }}
        ></div>
        <div 
          className="absolute w-[500px] h-[500px] rounded-full opacity-20 blur-[120px]"
          style={{ 
            backgroundColor: '#E86830',
            bottom: '-10%',
            right: '-10%',
            animation: 'float3 22s ease-in-out infinite'
          }}
        ></div>
      </div>

      {/* 主内容 */}
      <div className="relative z-10 container mx-auto px-4 py-12">
        {/* 标题区域 */}
        <div className="text-center mb-16">
          <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold mb-6">
            <span className="bg-gradient-to-b from-white to-slate-400 bg-clip-text text-transparent">
              健康与生理状态实时监测系统
            </span>
          </h1>
          <p className="text-lg text-slate-400 font-light tracking-wide max-w-2xl mx-auto">
            选择监测模块，开启您的智能健康守护
          </p>
        </div>

        {/* 卡片区域 */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-6xl mx-auto">
          {modules.map((module) => {
            const Icon = module.icon;
            return (
              <div 
                key={module.id} 
                className="relative"
                onMouseEnter={() => setActiveCard(module.id)}
                onMouseLeave={() => setActiveCard(null)}
              >
                <GlassCard
                  className={`
                    cursor-pointer transition-all duration-500 ease-out
                    bg-white/[0.02] backdrop-blur-2xl border border-white/10 
                    shadow-2xl shadow-black/50 rounded-3xl p-8
                    hover:-translate-y-2 hover:shadow-3xl hover:shadow-black/60
                    ${activeCard === module.id ? 'scale-[1.02]' : ''}
                  `}
                  onClick={() => onSelectModule(module.id as 'dry-eye' | 'sleep' | 'fatigue')}
                  style={{
                    background: activeCard === module.id 
                      ? `linear-gradient(to bottom, rgba(255,255,255,0.05), ${module.color}20)`
                      : 'rgba(255,255,255,0.02)',
                    borderColor: activeCard === module.id 
                      ? `${module.color}60`
                      : 'rgba(255,255,255,0.1)'
                  }}
                >
                  {/* 鼠标跟踪高光效果 */}
                  {activeCard === module.id && (
                    <div 
                      className="absolute inset-0 rounded-3xl pointer-events-none transition-opacity duration-300"
                      style={{
                        background: `radial-gradient(circle at ${mousePos.x}px ${mousePos.y}px, rgba(255,255,255,0.08) 0%, transparent 50%)`
                      }}
                    ></div>
                  )}

                  {/* 图标 */}
                  <div 
                    className="w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-6 transition-all duration-500"
                    style={{
                      backgroundColor: activeCard === module.id ? `${module.color}30` : 'rgba(255,255,255,0.05)',
                      boxShadow: activeCard === module.id ? `0 0 30px ${module.color}40` : 'none'
                    }}
                  >
                    <Icon 
                      size={32} 
                      className="transition-all duration-500"
                      style={{ 
                        color: module.color,
                        transform: activeCard === module.id ? 'scale(1.1)' : 'scale(1)'
                      }} 
                    />
                  </div>

                  {/* 标题 */}
                  <h2 className="text-xl font-bold text-white mb-3 text-center">
                    {module.title}
                  </h2>

                  {/* 描述 */}
                  <p className="text-slate-400 text-center mb-8 text-sm">
                    {module.description}
                  </p>

                  {/* 按钮 */}
                  <button
                    className="w-full py-3 px-6 rounded-xl font-medium transition-all duration-300 border"
                    style={{
                      backgroundColor: activeCard === module.id ? module.color : 'transparent',
                      borderColor: activeCard === module.id ? module.color : 'rgba(255,255,255,0.2)',
                      color: activeCard === module.id ? '#fff' : '#fff'
                    }}
                    onClick={(e) => {
                      e.stopPropagation();
                      onSelectModule(module.id as 'dry-eye' | 'sleep' | 'fatigue');
                    }}
                  >
                    开始监测
                  </button>
                </GlassCard>
              </div>
            );
          })}
        </div>

        {/* 版权声明 */}
        <div className="mt-20 text-center">
          <p className="text-white/30 text-xs">
            © 2026 健康与生理状态实时监测系统
          </p>
        </div>
      </div>

      {/* CSS 动画 */}
      <style>{`
        @keyframes float1 {
          0%, 100% { transform: translate(0, 0) scale(1); }
          33% { transform: translate(50px, 30px) scale(1.05); }
          66% { transform: translate(-30px, 50px) scale(0.95); }
        }
        @keyframes float2 {
          0%, 100% { transform: translate(-50%, -50%) scale(1); }
          33% { transform: translate(-40%, -60%) scale(1.1); }
          66% { transform: translate(-60%, -40%) scale(0.9); }
        }
        @keyframes float3 {
          0%, 100% { transform: translate(0, 0) scale(1); }
          33% { transform: translate(-40px, -30px) scale(1.05); }
          66% { transform: translate(30px, -50px) scale(0.95); }
        }
      `}</style>
    </div>
  );
};
