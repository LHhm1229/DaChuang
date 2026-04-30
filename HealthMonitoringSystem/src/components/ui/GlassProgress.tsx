import React from 'react';

interface GlassProgressProps {
  value: number;
  max?: number;
  className?: string;
  label?: string;
  showPercentage?: boolean;
  style?: React.CSSProperties;
}

export const GlassProgress: React.FC<GlassProgressProps> = ({
  value,
  max = 100,
  className = '',
  label,
  showPercentage = true,
  style
}) => {
  const percentage = Math.min((value / max) * 100, 100);

  return (
    <div className={`glass-card p-4 rounded-lg ${className}`} style={style}>
      {label && <div className="text-sm mb-2 opacity-80">{label}</div>}
      <div className="relative h-2 bg-white/20 rounded-full overflow-hidden">
        <div
          className="absolute top-0 left-0 h-full bg-primary rounded-full transition-all duration-500 ease-out"
          style={{ width: `${percentage}%`, backgroundColor: style?.backgroundColor }}
        />
      </div>
      {showPercentage && (
        <div className="mt-2 text-sm font-medium">{Math.round(percentage)}%</div>
      )}
    </div>
  );
};
