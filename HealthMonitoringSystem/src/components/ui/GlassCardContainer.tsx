import React, { ReactNode } from 'react';

interface GlassCardContainerProps {
  children: ReactNode;
  className?: string;
  layout?: 'default' | 'large' | 'wide' | 'tall';
}

export const GlassCardContainer: React.FC<GlassCardContainerProps> = ({
  children,
  className = '',
  layout = 'default'
}) => {
  const layoutClasses = {
    default: '',
    large: 'bento-item-large',
    wide: 'bento-item-wide',
    tall: 'bento-item-tall'
  };

  return (
    <div className={`${layoutClasses[layout]} ${className}`}>
      {children}
    </div>
  );
};
