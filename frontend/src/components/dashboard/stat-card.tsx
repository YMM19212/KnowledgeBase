import type { LucideIcon } from "lucide-react";

import { Card, CardContent } from "../ui/card";

type StatCardProps = {
  title: string;
  value: string | number;
  detail: string;
  icon: LucideIcon;
};

export function StatCard({ title, value, detail, icon: Icon }: StatCardProps) {
  return (
    <Card>
      <CardContent className="flex items-center justify-between p-5">
        <div>
          <p className="text-sm text-muted-foreground">{title}</p>
          <div className="mt-2 text-2xl font-semibold">{value}</div>
          <p className="mt-1 text-xs text-muted-foreground">{detail}</p>
        </div>
        <div className="flex h-10 w-10 items-center justify-center rounded-md bg-accent text-accent-foreground">
          <Icon className="h-5 w-5" />
        </div>
      </CardContent>
    </Card>
  );
}

