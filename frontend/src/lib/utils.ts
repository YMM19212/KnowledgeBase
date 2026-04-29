import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(value?: string | null) {
  if (!value) return "N/A";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit"
  }).format(date);
}

export function pageRange(start?: number | null, end?: number | null) {
  if (!start && !end) return "N/A";
  if (start && end && start !== end) return `pp.${start}-${end}`;
  return `p.${start ?? end}`;
}

export function percent(value: number) {
  return `${Math.round(value * 100)}%`;
}

