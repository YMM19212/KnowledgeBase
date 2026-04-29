import { Link } from "react-router-dom";

import { Badge } from "../components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { EmptyState, RetryState } from "../components/ui/empty-state";
import { Skeleton } from "../components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../components/ui/table";
import { useApi } from "../hooks/useApi";
import { api } from "../lib/api";
import { formatDate } from "../lib/utils";

export function DocumentsPage() {
  const kbs = useApi(api.listKnowledgeBases, []);

  if (kbs.loading) return <Skeleton className="h-[520px]" />;
  if (kbs.error || !kbs.data) return <RetryState message={kbs.error ?? "无法加载知识库"} onRetry={kbs.refresh} />;

  return (
    <Card>
      <CardHeader>
        <CardTitle>文档管理</CardTitle>
        <CardDescription>按知识库入口查看导入文档。文档详情页包含章节结构与 chunk 检索。</CardDescription>
      </CardHeader>
      <CardContent>
        {kbs.data.length === 0 ? (
          <EmptyState title="暂无知识库" description="请先创建知识库，再导入文档。" />
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>知识库</TableHead>
                <TableHead>文档数</TableHead>
                <TableHead>Chunks</TableHead>
                <TableHead>索引状态</TableHead>
                <TableHead>创建时间</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {kbs.data.map((kb) => (
                <TableRow key={kb.id}>
                  <TableCell>
                    <Link className="font-medium hover:text-primary" to={`/knowledge-bases/${kb.id}`}>
                      {kb.name}
                    </Link>
                    <div className="mt-1 text-xs text-muted-foreground">{kb.description}</div>
                  </TableCell>
                  <TableCell>{kb.document_count ?? 0}</TableCell>
                  <TableCell>{kb.chunk_count ?? 0}</TableCell>
                  <TableCell>
                    <Badge variant="success">{kb.index_status ?? "ready"}</Badge>
                  </TableCell>
                  <TableCell>{formatDate(kb.created_at)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  );
}
