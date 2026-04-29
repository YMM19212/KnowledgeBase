import { Bot, Filter, Link2, Send, ShieldAlert } from "lucide-react";
import { FormEvent, useMemo, useState } from "react";

import { Alert } from "../components/ui/alert";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { RetryState } from "../components/ui/empty-state";
import { Input } from "../components/ui/input";
import { Select } from "../components/ui/select";
import { Skeleton } from "../components/ui/skeleton";
import { Textarea } from "../components/ui/textarea";
import { useApi } from "../hooks/useApi";
import { api } from "../lib/api";
import type { QueryResponse } from "../lib/types";
import { pageRange } from "../lib/utils";

export function RagPage() {
  const kbs = useApi(api.listKnowledgeBases, []);
  const [kbId, setKbId] = useState<number | "">("");
  const [question, setQuestion] = useState("What was the primary outcome at week 24?");
  const [topK, setTopK] = useState(5);
  const [contentType, setContentType] = useState("all");
  const [sectionKeyword, setSectionKeyword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<QueryResponse | null>(null);

  const selectedKb = useMemo(
    () => kbs.data?.find((kb) => kb.id === Number(kbId)),
    [kbs.data, kbId]
  );

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!kbId || !question.trim()) return;
    setLoading(true);
    setError("");
    try {
      const filters: Record<string, unknown> = {};
      if (contentType !== "all") filters.content_type = contentType;
      const data = await api.query({
        knowledge_base_id: Number(kbId),
        query: question.trim(),
        top_k: topK,
        filters
      });
      const filtered =
        sectionKeyword.trim() && data.retrieved_chunks
          ? {
              ...data,
              retrieved_chunks: data.retrieved_chunks.filter((chunk) =>
                (chunk.section_path ?? "").toLowerCase().includes(sectionKeyword.toLowerCase())
              )
            }
          : data;
      setResult(filtered);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "查询失败");
    } finally {
      setLoading(false);
    }
  }

  if (kbs.loading) return <Skeleton className="h-[560px]" />;
  if (kbs.error || !kbs.data) return <RetryState message={kbs.error ?? "无法加载知识库"} onRetry={kbs.refresh} />;

  const insufficient = result?.answer.includes("证据不足");

  return (
    <div className="grid gap-4 xl:grid-cols-[420px_1fr]">
      <Card className="h-fit">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Bot className="h-5 w-5 text-primary" />
            可溯源 RAG 问答
          </CardTitle>
          <CardDescription>
            问答仅依据检索片段生成；无充分证据时返回拒答，便于医学场景审计。
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form className="space-y-4" onSubmit={handleSubmit}>
            <div>
              <label className="mb-2 block text-sm font-medium">知识库</label>
              <Select value={kbId} onChange={(event) => setKbId(Number(event.target.value))}>
                <option value="">选择知识库</option>
                {kbs.data.map((kb) => (
                  <option key={kb.id} value={kb.id}>
                    {kb.name}
                  </option>
                ))}
              </Select>
              {selectedKb ? (
                <div className="mt-2 text-xs text-muted-foreground">
                  {selectedKb.document_count ?? 0} docs · {selectedKb.chunk_count ?? 0} chunks
                </div>
              ) : null}
            </div>
            <div>
              <label className="mb-2 block text-sm font-medium">医学问题</label>
              <Textarea value={question} onChange={(event) => setQuestion(event.target.value)} />
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <div>
                <label className="mb-2 block text-sm font-medium">Top K</label>
                <Input
                  type="number"
                  min={1}
                  max={50}
                  value={topK}
                  onChange={(event) => setTopK(Number(event.target.value))}
                />
              </div>
              <div>
                <label className="mb-2 block text-sm font-medium">Content Type</label>
                <Select value={contentType} onChange={(event) => setContentType(event.target.value)}>
                  <option value="all">全部</option>
                  <option value="text">Text</option>
                  <option value="table">Table</option>
                  <option value="figure_caption">Figure Caption</option>
                </Select>
              </div>
            </div>
            <div>
              <label className="mb-2 flex items-center gap-2 text-sm font-medium">
                <Filter className="h-4 w-4" />
                Metadata Filter
              </label>
              <Input
                value={sectionKeyword}
                onChange={(event) => setSectionKeyword(event.target.value)}
                placeholder="前端过滤 section_path，例如 Primary outcome"
              />
            </div>
            {error ? <Alert variant="danger">{error}</Alert> : null}
            <Button className="w-full" disabled={loading || !kbId || !question.trim()}>
              <Send className="h-4 w-4" />
              {loading ? "检索中..." : "发起检索问答"}
            </Button>
          </form>
        </CardContent>
      </Card>

      <div className="space-y-4">
        <Card>
          <CardHeader>
            <CardTitle>Answer</CardTitle>
            <CardDescription>回答与证据片段严格绑定。</CardDescription>
          </CardHeader>
          <CardContent>
            {!result ? (
              <div className="rounded-lg border border-dashed border-border p-8 text-center text-sm text-muted-foreground">
                选择知识库并输入医学问题后，系统会返回 answer、citations 与 retrieved chunks。
              </div>
            ) : insufficient ? (
              <Alert variant="warning">
                <div className="flex items-start gap-3">
                  <ShieldAlert className="mt-0.5 h-5 w-5" />
                  <div>
                    <div className="font-semibold">证据不足</div>
                    <div className="mt-1 whitespace-pre-wrap">{result.answer}</div>
                  </div>
                </div>
              </Alert>
            ) : (
              <div className="whitespace-pre-wrap rounded-lg border border-border bg-muted/30 p-4 text-sm leading-7">
                {result.answer}
              </div>
            )}
          </CardContent>
        </Card>

        {result ? (
          <>
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Link2 className="h-4 w-4" />
                  Citations
                </CardTitle>
                <CardDescription>可用于答辩展示的 chunk/source 级溯源。</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                {result.citations.length === 0 ? (
                  <p className="text-sm text-muted-foreground">未返回 citations。</p>
                ) : (
                  result.citations.map((citation) => (
                    <div key={citation.chunk_id} className="rounded-lg border border-border p-4">
                      <div className="flex flex-wrap items-center gap-2">
                        <Badge variant="success">score {citation.score.toFixed(3)}</Badge>
                        <Badge variant="outline">{pageRange(citation.page_start, citation.page_end)}</Badge>
                        <span className="text-sm font-medium">{citation.section_path}</span>
                      </div>
                      <div className="mt-2 text-xs text-muted-foreground">
                        {citation.document_id} · {citation.citation_text}
                      </div>
                      <p className="mt-3 text-sm leading-6">{citation.source_text}</p>
                    </div>
                  ))
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Retrieved Chunks</CardTitle>
                <CardDescription>原始检索返回，用于调试召回与排序。</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                {result.retrieved_chunks.map((chunk) => (
                  <div key={chunk.chunk_id} className="rounded-lg border border-border bg-card p-4">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge variant="outline">{chunk.content_type ?? "text"}</Badge>
                      <Badge variant="secondary">score {chunk.score.toFixed(3)}</Badge>
                      <span className="text-sm font-medium">{chunk.section_path}</span>
                    </div>
                    <div className="mt-2 text-xs text-muted-foreground">
                      {chunk.document_id} · {pageRange(chunk.page_start, chunk.page_end)}
                    </div>
                    <p className="mt-3 whitespace-pre-wrap text-sm leading-6">
                      {chunk.source_text ?? chunk.content}
                    </p>
                  </div>
                ))}
              </CardContent>
            </Card>
          </>
        ) : null}
      </div>
    </div>
  );
}
