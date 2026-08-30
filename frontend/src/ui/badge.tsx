import * as React from 'react'
import { cn } from '../lib/utils'

type BadgeVariant = 'default' | 'secondary' | 'outline' | 'accent'

const variantClasses: Record<BadgeVariant, string> = {
  default: 'border-transparent bg-primary text-primary-foreground',
  secondary: 'border-transparent bg-secondary text-secondary-foreground',
  outline: 'border-border text-foreground',
  accent: 'border-transparent bg-accent text-accent-foreground',
}

function Badge({
  className,
  variant = 'default',
  ...props
}: React.HTMLAttributes<HTMLSpanElement> & { variant?: BadgeVariant }) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium transition-colors',
        variantClasses[variant],
        className,
      )}
      {...props}
    />
  )
}

export { Badge }
