import { Plus, Trash2 } from "lucide-react";
import { FormEvent, useState } from "react";
import { Link } from "react-router-dom";

import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { EmptyState, RetryState } from "../components/ui/empty-state";
import { Input } from "../components/ui/input";
import { Skeleton } from "../components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../components/ui/table";
import { useApi } from "../hooks/useApi";
import { api } from "../lib/api";
import { formatDate } from "../lib/utils";

export function KnowledgeBasesPage() {
  const { data, loading, error, refresh } = useApi(api.listKnowledgeBases, []);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleCreate(event: FormEvent) {
    event.preventDefault();
    if (!name.trim()) return;
    setSubmitting(true);
    try {
      await api.createKnowledgeBase({ name: name.trim(), description });
      setName("");
      setDescription("");
      await refresh();
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete(id: number) {
    if (!window.confirm("确认删除该知识库及其文档、chunks 和索引？")) return;
    await api.deleteKnowledgeBase(id);
    await refresh();
  }

  if (loading) return <Skeleton className="h-[520px]" />;
  if (error || !data) return <RetryState message={error ?? "无法加载知识库"} onRetry={refresh} />;

  return (
    <div className="grid gap-4 xl:grid-cols-[1fr_360px]">
      <Card>
        <CardHeader>
          <CardTitle>知识库管理</CardTitle>
          <CardDescription>管理医疗文献主题库、索引状态与文档规模。</CardDescription>
        </CardHeader>
        <CardContent>
          {data.length === 0 ? (
            <EmptyState title="暂无知识库" description="创建一个知识库后即可导入 MinerU 样例结果。" />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>名称</TableHead>
                  <TableHead>文档</TableHead>
                  <TableHead>Chunks</TableHead>
                  <TableHead>索引</TableHead>
                  <TableHead>创建时间</TableHead>
                  <TableHead className="w-28">操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.map((kb) => (
                  <TableRow key={kb.id}>
                    <TableCell>
                      <Link className="font-medium hover:text-primary" to={`/knowledge-bases/${kb.id}`}>
                        {kb.name}
                      </Link>
                      <div className="mt-1 text-xs text-muted-foreground">{kb.description || "无描述"}</div>
                    </TableCell>
                    <TableCell>{kb.document_count ?? 0}</TableCell>
                    <TableCell>{kb.chunk_count ?? 0}</TableCell>
                    <TableCell>
                      <Badge variant="success">{kb.index_status ?? "ready"}</Badge>
                    </TableCell>
                    <TableCell>{formatDate(kb.created_at)}</TableCell>
                    <TableCell>
                      <Button variant="ghost" size="icon" onClick={() => void handleDelete(kb.id)}>
                        <Trash2 className="h-4 w-4 text-destructive" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>创建知识库</CardTitle>
          <CardDescription>建议按疾病、指南、临床试验主题拆分。</CardDescription>
        </CardHeader>
        <CardContent>
          <form className="space-y-3" onSubmit={handleCreate}>
            <Input value={name} onChange={(event) => setName(event.target.value)} placeholder="例如：Heart Failure Trials" />
            <Input
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              placeholder="知识库用途说明"
            />
            <Button className="w-full" disabled={submitting || !name.trim()}>
              <Plus className="h-4 w-4" />
              创建知识库
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
