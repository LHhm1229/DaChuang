import React, { ReactNode } from 'react';

interface GlassCardProps {
  children: ReactNode;
  className?: string;
  onClick?: () => void;
  variant?: 'default' | 'large' | 'small';
  style?: React.CSSProperties;
}

export const GlassCard: React.FC<GlassCardProps> = ({
  children,
  className = '',
  onClick,
  variant = 'default',
  style
}) => {
  const variantClasses = {
    default: 'p-6 rounded-xl',
    large: 'p-8 rounded-2xl',
    small: 'p-4 rounded-lg'
  };

  return (
    <div
      className={`glass-card ${variantClasses[variant]} ${className}`}
      onClick={onClick}
      style={style}
    >
      {children}
    </div>
  );
};
