import { BarChart3, Database, FileText, Layers3, SearchCheck } from "lucide-react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { ProcessFlow } from "../components/dashboard/process-flow";
import { StatCard } from "../components/dashboard/stat-card";
import { Badge } from "../components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { RetryState } from "../components/ui/empty-state";
import { Skeleton } from "../components/ui/skeleton";
import { useApi } from "../hooks/useApi";
import { api } from "../lib/api";
import { formatDate } from "../lib/utils";

export function DashboardPage() {
  const { data, loading, error, refresh } = useApi(api.stats, []);

  if (loading) {
    return <Skeleton className="h-[520px]" />;
  }
  if (error || !data) {
    return <RetryState message={error ?? "无法加载统计数据"} onRetry={refresh} />;
  }

  const chartData = [
    { name: "知识库", value: data.knowledge_bases },
    { name: "文档", value: data.documents },
    { name: "Chunks", value: data.chunks },
    { name: "问答", value: data.query_count ?? 0 }
  ];

  return (
    <div className="space-y-6">
      <section className="medical-grid rounded-lg border border-border bg-card p-6">
        <div className="max-w-3xl">
          <Badge variant="success">Mock MinerU 阶段 · 可切换真实解析服务</Badge>
          <h2 className="mt-4 text-2xl font-semibold tracking-normal">
            医疗文献知识库与可溯源 RAG 控制台
          </h2>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">
            面向临床试验、指南与系统综述的结构化处理平台，覆盖 MinerU 解析适配、
            医疗语义切分、向量索引、检索问答和引用审计。
          </p>
        </div>
      </section>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatCard
          title="知识库数量"
          value={data.knowledge_bases}
          detail="已创建的医学主题库"
          icon={Database}
        />
        <StatCard title="文档数量" value={data.documents} detail="已解析/导入文献" icon={FileText} />
        <StatCard title="Chunk 数量" value={data.chunks} detail="语义级证据片段" icon={Layers3} />
        <StatCard
          title="检索/问答次数"
          value={data.query_count ?? 0}
          detail={`索引状态：${data.index_status ?? "ready"}`}
          icon={SearchCheck}
        />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>医疗文献处理流程</CardTitle>
          <CardDescription>从复杂版式 PDF 到带来源证据的医学问答。</CardDescription>
        </CardHeader>
        <CardContent>
          <ProcessFlow />
        </CardContent>
      </Card>

      <div className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BarChart3 className="h-4 w-4" />
              平台运行概览
            </CardTitle>
            <CardDescription>用于答辩演示的本地运行指标。</CardDescription>
          </CardHeader>
          <CardContent className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="name" tickLine={false} axisLine={false} />
                <YAxis allowDecimals={false} tickLine={false} axisLine={false} />
                <Tooltip />
                <Bar dataKey="value" fill="hsl(var(--primary))" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>最近导入文档</CardTitle>
            <CardDescription>快速查看解析状态与导入时间。</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {(data.recent_documents ?? []).length === 0 ? (
              <p className="text-sm text-muted-foreground">暂无导入文档，可在知识库详情中导入样例。</p>
            ) : (
              data.recent_documents?.map((document) => (
                <div key={document.id} className="rounded-md border border-border p-3">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="truncate text-sm font-medium">{document.title}</div>
                      <div className="mt-1 text-xs text-muted-foreground">{document.id}</div>
                    </div>
                    <Badge variant="success">{document.parse_status}</Badge>
                  </div>
                  <div className="mt-2 text-xs text-muted-foreground">
                    {document.chunk_count ?? 0} chunks · {formatDate(document.created_at)}
                  </div>
                </div>
              ))
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
