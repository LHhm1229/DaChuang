import React, { ReactNode } from 'react';

interface GlassBadgeProps {
  children: ReactNode;
  className?: string;
  variant?: 'primary' | 'secondary' | 'success' | 'warning' | 'danger';
  size?: 'sm' | 'md' | 'lg';
}

export const GlassBadge: React.FC<GlassBadgeProps> = ({
  children,
  className = '',
  variant = 'primary',
  size = 'md'
}) => {
  const variantClasses = {
    primary: 'bg-primary/80 text-white',
    secondary: 'bg-secondary/80 text-white',
    success: 'bg-green-500/80 text-white',
    warning: 'bg-yellow-500/80 text-white',
    danger: 'bg-red-500/80 text-white'
  };

  const sizeClasses = {
    sm: 'px-2 py-0.5 text-xs',
    md: 'px-3 py-1 text-sm',
    lg: 'px-4 py-1.5 text-base'
  };

  return (
    <span className={`glass-card rounded-full font-medium ${variantClasses[variant]} ${sizeClasses[size]} ${className}`}>
      {children}
    </span>
  );
};
