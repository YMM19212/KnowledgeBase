import { FileCheck2, Search, Trash2 } from "lucide-react";
import { useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { Alert } from "../components/ui/alert";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { RetryState } from "../components/ui/empty-state";
import { Input } from "../components/ui/input";
import { Select } from "../components/ui/select";
import { Skeleton } from "../components/ui/skeleton";
import { useApi } from "../hooks/useApi";
import { api } from "../lib/api";
import { pageRange } from "../lib/utils";

export function DocumentDetailPage() {
  const { documentId } = useParams();
  const navigate = useNavigate();
  const id = documentId ?? "";
  const document = useApi(() => api.getDocument(id), [id]);
  const chunks = useApi(() => api.listChunks(id), [id]);
  const evidence = useApi(() => api.listEvidenceUnits(id), [id]);
  const [search, setSearch] = useState("");
  const [type, setType] = useState("all");

  const filteredChunks = useMemo(() => {
    const keyword = search.trim().toLowerCase();
    return (chunks.data ?? []).filter((chunk) => {
      const matchesType = type === "all" || chunk.content_type === type;
      const haystack = `${chunk.section_path} ${chunk.content} ${chunk.metadata?.citation_text ?? ""}`.toLowerCase();
      return matchesType && (!keyword || haystack.includes(keyword));
    });
  }, [chunks.data, search, type]);

  const sectionTree = useMemo(() => {
    const paths = Array.from(new Set((chunks.data ?? []).map((chunk) => chunk.section_path)));
    return paths;
  }, [chunks.data]);

  async function handleDelete() {
    if (!window.confirm("确认删除该文档及其索引？")) return;
    await api.deleteDocument(id);
    navigate("/documents");
  }

  if (document.loading || chunks.loading || evidence.loading) return <Skeleton className="h-[520px]" />;
  if (document.error || chunks.error || !document.data) {
    return <RetryState message={document.error ?? chunks.error ?? "无法加载文档"} onRetry={document.refresh} />;
  }

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <div className="flex flex-col justify-between gap-4 md:flex-row">
            <div>
              <CardTitle>{document.data.title}</CardTitle>
              <CardDescription className="mt-2">
                {document.data.authors.join(", ") || "Unknown authors"}
              </CardDescription>
              <div className="mt-3 flex flex-wrap gap-2">
                <Badge variant="success">{document.data.parse_status}</Badge>
                <Badge variant="outline">{document.data.id}</Badge>
                <Badge variant="outline">{chunks.data?.length ?? 0} chunks</Badge>
                <Badge variant="secondary">{evidence.data?.length ?? 0} evidence units</Badge>
              </div>
            </div>
            <Button variant="destructive" onClick={() => void handleDelete()}>
              <Trash2 className="h-4 w-4" />
              删除文档
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <Alert>
            <div className="font-medium">摘要</div>
            <div className="mt-1 text-muted-foreground">{document.data.abstract || "暂无摘要"}</div>
          </Alert>
        </CardContent>
      </Card>

      <div className="grid gap-4 xl:grid-cols-[320px_1fr]">
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>章节结构</CardTitle>
              <CardDescription>由 chunk 的 section_path 汇总。</CardDescription>
            </CardHeader>
            <CardContent className="space-y-2">
              {sectionTree.map((section) => (
                <div key={section} className="rounded-md border border-border px-3 py-2 text-sm">
                  {section}
                </div>
              ))}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <FileCheck2 className="h-4 w-4" />
                Evidence Units
              </CardTitle>
              <CardDescription>入库阶段生成的医学证据单元。</CardDescription>
            </CardHeader>
            <CardContent className="space-y-2">
              {(evidence.data ?? []).slice(0, 12).map((unit) => (
                <div key={unit.id} className="rounded-md border border-border p-3 text-sm">
                  <div className="mb-2 flex flex-wrap gap-2">
                    <Badge variant="secondary">{unit.evidence_type}</Badge>
                    <Badge variant="outline">{unit.canonical_section}</Badge>
                  </div>
                  <div className="line-clamp-4 text-muted-foreground">{unit.claim_text}</div>
                </div>
              ))}
              {(evidence.data ?? []).length === 0 ? (
                <div className="text-sm text-muted-foreground">暂无 evidence units。</div>
              ) : null}
            </CardContent>
          </Card>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Chunk 列表</CardTitle>
            <CardDescription>搜索正文、表格、图注，并查看可溯源 metadata。</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="mb-4 grid gap-3 md:grid-cols-[1fr_220px]">
              <div className="relative">
                <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input
                  className="pl-9"
                  value={search}
                  onChange={(event) => setSearch(event.target.value)}
                  placeholder="搜索 section、citation 或 source text"
                />
              </div>
              <Select value={type} onChange={(event) => setType(event.target.value)}>
                <option value="all">全部类型</option>
                <option value="text">Text</option>
                <option value="table">Table</option>
                <option value="figure_caption">Figure Caption</option>
                <option value="mixed">Mixed</option>
              </Select>
            </div>
            <div className="space-y-3">
              {filteredChunks.map((chunk) => (
                <div key={chunk.chunk_id} className="rounded-lg border border-border bg-card p-4">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant="outline">{chunk.content_type}</Badge>
                    <span className="text-sm font-medium">{chunk.section_path}</span>
                    <span className="text-xs text-muted-foreground">
                      {pageRange(chunk.page_start, chunk.page_end)}
                    </span>
                  </div>
                  <div className="mt-2 text-xs text-muted-foreground">
                    {String(chunk.metadata?.citation_text ?? chunk.chunk_id)}
                  </div>
                  <p className="mt-3 whitespace-pre-wrap text-sm leading-6">{chunk.content}</p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
