import type { HTMLAttributes, ReactNode } from 'react'
import clsx from 'clsx'

interface GlassCardProps extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode
  hover?: boolean
}

export function GlassCard({ children, className, hover = true, ...rest }: GlassCardProps) {
  return (
    <div className={clsx('glass-card p-6', hover && 'glass-card-hover', className)} {...rest}>
      {children}
    </div>
  )
}
