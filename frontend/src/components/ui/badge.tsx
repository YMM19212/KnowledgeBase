import { type HTMLAttributes } from "react";

import { cn } from "../../lib/utils";

type BadgeProps = HTMLAttributes<HTMLSpanElement> & {
  variant?: "default" | "secondary" | "outline" | "success" | "warning" | "danger";
};

const variants = {
  default: "bg-primary text-primary-foreground",
  secondary: "bg-secondary text-secondary-foreground",
  outline: "border border-border bg-transparent",
  success: "bg-emerald-500/12 text-emerald-700 dark:text-emerald-300",
  warning: "bg-amber-500/14 text-amber-700 dark:text-amber-300",
  danger: "bg-destructive/12 text-destructive"
};

export function Badge({ className, variant = "secondary", ...props }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium",
        variants[variant],
        className
      )}
      {...props}
    />
  );
}

