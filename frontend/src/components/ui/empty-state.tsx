import { FileSearch } from "lucide-react";
import type { ReactNode } from "react";

import { Button } from "./button";

type EmptyStateProps = {
  title: string;
  description: string;
  action?: ReactNode;
};

export function EmptyState({ title, description, action }: EmptyStateProps) {
  return (
    <div className="flex min-h-52 flex-col items-center justify-center rounded-lg border border-dashed border-border bg-card p-8 text-center">
      <FileSearch className="mb-3 h-8 w-8 text-muted-foreground" />
      <h3 className="text-sm font-semibold">{title}</h3>
      <p className="mt-1 max-w-md text-sm text-muted-foreground">{description}</p>
      {action ? <div className="mt-4">{action}</div> : null}
    </div>
  );
}

export function RetryState({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <EmptyState
      title="加载失败"
      description={message}
      action={
        <Button variant="outline" onClick={onRetry}>
          重试
        </Button>
      }
    />
  );
}

