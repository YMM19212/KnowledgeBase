import { Server, Settings2 } from "lucide-react";

import { Badge } from "../components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { RetryState } from "../components/ui/empty-state";
import { Skeleton } from "../components/ui/skeleton";
import { useApi } from "../hooks/useApi";
import { API_BASE_URL, api } from "../lib/api";

export function SettingsPage() {
  const { data, loading, error, refresh } = useApi(api.config, []);

  if (loading) return <Skeleton className="h-[520px]" />;
  if (error || !data) return <RetryState message={error ?? "无法加载系统配置"} onRetry={refresh} />;

  const rows = [
    ["API Base URL", API_BASE_URL],
    ["Embedding Backend", data.embedding_backend],
    ["Embedding Model", data.embedding_model],
    ["Vector Store", data.vector_store],
    ["LLM Provider", data.llm_provider],
    ["Environment", data.env]
  ];

  return (
    <div className="grid gap-4 lg:grid-cols-[1fr_360px]">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Settings2 className="h-5 w-5 text-primary" />
            系统设置
          </CardTitle>
          <CardDescription>运行时配置来自前端 Vite 环境变量与后端 `.env`。</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {rows.map(([label, value]) => (
            <div key={label} className="grid gap-2 rounded-md border border-border p-3 md:grid-cols-[180px_1fr]">
              <div className="text-sm font-medium">{label}</div>
              <div className="break-all text-sm text-muted-foreground">{value || "not configured"}</div>
            </div>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Server className="h-4 w-4" />
            运行状态
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-sm">Parser</span>
            <Badge variant={data.parser_mode === "mock" ? "warning" : "success"}>{data.parser_mode}</Badge>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm">LLM</span>
            <Badge variant={data.llm_configured ? "success" : "outline"}>
              {data.llm_configured ? "configured" : "retrieval-only"}
            </Badge>
          </div>
          <div className="rounded-md bg-muted p-3 text-xs leading-5 text-muted-foreground">
            前端读取 `VITE_API_BASE_URL`。后端读取 `MEDRAG_DATABASE_URL`、`MEDRAG_VECTOR_STORE`、
            `MEDRAG_EMBEDDING_MODEL`、`MEDRAG_MINERU_API_URL` 和 OpenAI-compatible LLM 配置。
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
