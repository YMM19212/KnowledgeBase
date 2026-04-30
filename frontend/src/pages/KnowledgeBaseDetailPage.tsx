import { FileCheck2, FileUp, Play, RefreshCw, TerminalSquare, Upload } from "lucide-react";
import { ChangeEvent, FormEvent, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { EmptyState, RetryState } from "../components/ui/empty-state";
import { Input } from "../components/ui/input";
import { Select } from "../components/ui/select";
import { Skeleton } from "../components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../components/ui/table";
import { useApi } from "../hooks/useApi";
import { api } from "../lib/api";
import type { LocalMinerUIngestResponse } from "../lib/types";
import { formatDate } from "../lib/utils";

export function KnowledgeBaseDetailPage() {
  const { kbId } = useParams();
  const id = Number(kbId);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [busy, setBusy] = useState(false);
  const [mineruFile, setMineruFile] = useState<File | null>(null);
  const [method, setMethod] = useState("auto");
  const [lang, setLang] = useState("ch");
  const [formula, setFormula] = useState(true);
  const [table, setTable] = useState(true);
  const [mineruError, setMineruError] = useState("");
  const [mineruResult, setMineruResult] = useState<LocalMinerUIngestResponse | null>(null);
  const kb = useApi(() => api.getKnowledgeBase(id), [id]);
  const docs = useApi(() => api.listDocuments(id), [id]);
  const mineruStatus = useApi(api.localMinerUStatus, []);
  const remoteMineruStatus = useApi(api.remoteMinerUStatus, []);

  async function handleIngestMock() {
    setBusy(true);
    try {
      await api.ingestMock(id);
      await Promise.all([kb.refresh(), docs.refresh()]);
    } finally {
      setBusy(false);
    }
  }

  async function handleUpload(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    setBusy(true);
    try {
      await api.uploadDocument(id, file);
      await Promise.all([kb.refresh(), docs.refresh()]);
    } finally {
      setBusy(false);
      event.target.value = "";
    }
  }

  async function handleRebuild() {
    setBusy(true);
    try {
      await api.rebuildIndex(id);
      await kb.refresh();
    } finally {
      setBusy(false);
    }
  }

  async function handleRebuildEvidence() {
    setBusy(true);
    try {
      await api.rebuildEvidence(id);
      await kb.refresh();
    } finally {
      setBusy(false);
    }
  }

  async function handleLocalMinerU(event: FormEvent) {
    event.preventDefault();
    if (!mineruFile) return;
    setBusy(true);
    setMineruError("");
    setMineruResult(null);
    try {
      const result = await api.ingestWithLocalMinerU(id, {
        file: mineruFile,
        method,
        lang,
        formula,
        table
      });
      setMineruResult(result);
      await Promise.all([kb.refresh(), docs.refresh()]);
    } catch (error) {
      setMineruError(error instanceof Error ? error.message : "MinerU 清洗失败");
    } finally {
      setBusy(false);
    }
  }

  async function handleRemoteMinerU() {
    if (!mineruFile) return;
    setBusy(true);
    setMineruError("");
    setMineruResult(null);
    try {
      const result = await api.ingestWithRemoteMinerU(id, {
        file: mineruFile,
        method,
        lang,
        formula,
        table
      });
      setMineruResult(result);
      await Promise.all([kb.refresh(), docs.refresh()]);
    } catch (error) {
      setMineruError(error instanceof Error ? error.message : "远程 MinerU 清洗失败");
    } finally {
      setBusy(false);
    }
  }

  if (kb.loading || docs.loading) return <Skeleton className="h-[520px]" />;
  if (kb.error || docs.error || !kb.data) {
    return <RetryState message={kb.error ?? docs.error ?? "无法加载知识库详情"} onRetry={kb.refresh} />;
  }

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <div className="flex flex-col justify-between gap-4 md:flex-row md:items-start">
            <div>
              <CardTitle>{kb.data.name}</CardTitle>
              <CardDescription className="mt-1">{kb.data.description || "暂无描述"}</CardDescription>
              <div className="mt-3 flex flex-wrap gap-2">
                <Badge variant="success">{kb.data.index_status ?? "ready"}</Badge>
                <Badge variant="outline">{kb.data.document_count ?? 0} documents</Badge>
                <Badge variant="outline">{kb.data.chunk_count ?? 0} chunks</Badge>
                <Badge variant="outline">created {formatDate(kb.data.created_at)}</Badge>
              </div>
            </div>
            <div className="flex flex-wrap gap-2">
              <Button variant="outline" onClick={handleIngestMock} disabled={busy}>
                <FileUp className="h-4 w-4" />
                导入 Mock MinerU
              </Button>
              <Button variant="outline" onClick={() => fileInputRef.current?.click()} disabled={busy}>
                <Upload className="h-4 w-4" />
                上传文档
              </Button>
              <Button onClick={handleRebuild} disabled={busy}>
                <RefreshCw className="h-4 w-4" />
                重建索引
              </Button>
              <Button variant="outline" onClick={handleRebuildEvidence} disabled={busy}>
                <FileCheck2 className="h-4 w-4" />
                重建 Evidence
              </Button>
              <input ref={fileInputRef} type="file" className="hidden" onChange={handleUpload} />
            </div>
          </div>
        </CardHeader>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <TerminalSquare className="h-5 w-5 text-primary" />
            本地 MinerU Pipeline 清洗导入
          </CardTitle>
          <CardDescription>
            上传 PDF 后端会运行 `mineru -p input -o output -b pipeline`，自动解析输出并写入当前知识库。
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form className="grid gap-4 xl:grid-cols-[1fr_360px]" onSubmit={handleLocalMinerU}>
            <div className="space-y-4">
              <div className="rounded-lg border border-dashed border-border p-4">
                <label className="mb-2 block text-sm font-medium">1. 选择待清洗 PDF</label>
                <Input
                  type="file"
                  accept=".pdf,.png,.jpg,.jpeg"
                  onChange={(event) => setMineruFile(event.target.files?.[0] ?? null)}
                />
                <p className="mt-2 text-xs text-muted-foreground">
                  {mineruFile ? `${mineruFile.name} · ${(mineruFile.size / 1024 / 1024).toFixed(2)} MB` : "文件会上传到后端 storage 目录，再交给本地 MinerU CLI 处理。"}
                </p>
              </div>

              <div className="grid gap-3 md:grid-cols-4">
                <div>
                  <label className="mb-2 block text-sm font-medium">Method</label>
                  <Select value={method} onChange={(event) => setMethod(event.target.value)}>
                    <option value="auto">auto</option>
                    <option value="txt">txt</option>
                    <option value="ocr">ocr</option>
                  </Select>
                </div>
                <div>
                  <label className="mb-2 block text-sm font-medium">Language</label>
                  <Select value={lang} onChange={(event) => setLang(event.target.value)}>
                    <option value="ch">ch</option>
                    <option value="en">en</option>
                    <option value="ch_server">ch_server</option>
                    <option value="ch_lite">ch_lite</option>
                  </Select>
                </div>
                <label className="flex items-center gap-2 rounded-md border border-border px-3 py-2 text-sm">
                  <input type="checkbox" checked={formula} onChange={(event) => setFormula(event.target.checked)} />
                  Formula
                </label>
                <label className="flex items-center gap-2 rounded-md border border-border px-3 py-2 text-sm">
                  <input type="checkbox" checked={table} onChange={(event) => setTable(event.target.checked)} />
                  Table
                </label>
              </div>

              {mineruError ? (
                <div className="rounded-lg border border-destructive/40 bg-destructive/10 p-3 text-sm text-destructive">
                  {mineruError}
                </div>
              ) : null}

              {mineruResult ? (
                <div className="space-y-3 rounded-lg border border-border bg-muted/30 p-4">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant="success">清洗完成</Badge>
                    <Badge variant="outline">{mineruResult.mineru.duration_seconds}s</Badge>
                    <Badge variant="outline">{mineruResult.mineru.artifacts.length} artifacts</Badge>
                  </div>
                  <div className="text-sm">
                    已入库文档：
                    <a className="font-medium text-primary" href={`/documents/${mineruResult.document.id}`}>
                      {mineruResult.document.title}
                    </a>
                  </div>
                  <pre className="max-h-44 overflow-auto rounded-md bg-background p-3 text-xs">
                    {mineruResult.mineru.command.join(" ")}
                    {"\n\n"}
                    {mineruResult.mineru.stdout || mineruResult.mineru.stderr || "MinerU 未输出日志"}
                  </pre>
                </div>
              ) : null}
            </div>

            <div className="space-y-3 rounded-lg border border-border bg-card p-4">
              <div className="text-sm font-semibold">本地环境状态</div>
              <div className="flex items-center justify-between text-sm">
                <span>MinerU CLI</span>
                <Badge variant={mineruStatus.data?.available ? "success" : "warning"}>
                  {mineruStatus.loading ? "checking" : mineruStatus.data?.available ? "available" : "unavailable"}
                </Badge>
              </div>
              <div className="break-all text-xs leading-5 text-muted-foreground">
                command: {mineruStatus.data?.command ?? "mineru"}
                <br />
                version: {mineruStatus.data?.version ?? mineruStatus.data?.error ?? "N/A"}
              </div>
              <Button className="w-full" disabled={busy || !mineruFile || mineruStatus.data?.available === false}>
                <Play className="h-4 w-4" />
                {busy ? "MinerU 清洗与入库中..." : "运行 Pipeline 并入库"}
              </Button>
              <div className="mt-4 border-t border-border pt-4">
                <div className="mb-2 flex items-center justify-between text-sm">
                  <span>Remote MinerU</span>
                  <Badge variant={remoteMineruStatus.data?.available ? "success" : "warning"}>
                    {remoteMineruStatus.loading
                      ? "checking"
                      : remoteMineruStatus.data?.available
                        ? "available"
                        : "unavailable"}
                  </Badge>
                </div>
                <div className="break-all text-xs leading-5 text-muted-foreground">
                  command: {remoteMineruStatus.data?.command ?? "ssh remote mineru"}
                  <br />
                  version: {remoteMineruStatus.data?.version ?? remoteMineruStatus.data?.error ?? "N/A"}
                </div>
                <Button
                  type="button"
                  variant="outline"
                  className="mt-3 w-full"
                  disabled={busy || !mineruFile || remoteMineruStatus.data?.available === false}
                  onClick={() => void handleRemoteMinerU()}
                >
                  <Play className="h-4 w-4" />
                  {busy ? "远程清洗与入库中..." : "用远程 MinerU 入库"}
                </Button>
              </div>
              <p className="text-xs leading-5 text-muted-foreground">
                处理完成后，系统会优先读取 MinerU 的 content_list JSON；如果没有 JSON，则回退解析 Markdown。
                远程模式会通过 SSH 上传文件、运行服务器上的 MinerU，再下载解析产物。
              </p>
            </div>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>文档列表</CardTitle>
          <CardDescription>查看解析状态、chunk 数量和文档详情。</CardDescription>
        </CardHeader>
        <CardContent>
          {!docs.data?.length ? (
            <EmptyState
              title="暂无文档"
              description="当前阶段可导入 Mock MinerU 样例，后续接入服务器 MinerU 解析真实 PDF。"
              action={
                <Button onClick={handleIngestMock} disabled={busy}>
                  导入样例
                </Button>
              }
            />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>文档</TableHead>
                  <TableHead>作者</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead>Chunks</TableHead>
                  <TableHead>导入时间</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {docs.data.map((document) => (
                  <TableRow key={document.id}>
                    <TableCell>
                      <Link className="font-medium hover:text-primary" to={`/documents/${document.id}`}>
                        {document.title}
                      </Link>
                      <div className="mt-1 text-xs text-muted-foreground">{document.id}</div>
                    </TableCell>
                    <TableCell className="max-w-48 truncate">{document.authors.join(", ")}</TableCell>
                    <TableCell>
                      <Badge variant="success">{document.parse_status}</Badge>
                    </TableCell>
                    <TableCell>{document.chunk_count ?? 0}</TableCell>
                    <TableCell>{formatDate(document.created_at)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
