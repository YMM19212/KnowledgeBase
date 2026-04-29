import { type HTMLAttributes } from "react";

import { cn } from "../../lib/utils";

type AlertProps = HTMLAttributes<HTMLDivElement> & {
  variant?: "default" | "warning" | "danger";
};

const variants = {
  default: "border-border bg-card",
  warning: "border-amber-300 bg-amber-50 text-amber-900 dark:border-amber-700 dark:bg-amber-950/40 dark:text-amber-200",
  danger: "border-destructive/40 bg-destructive/10 text-destructive"
};

export function Alert({ className, variant = "default", ...props }: AlertProps) {
  return (
    <div
      className={cn("rounded-lg border px-4 py-3 text-sm", variants[variant], className)}
      {...props}
    />
  );
}

