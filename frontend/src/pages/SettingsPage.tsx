import { BrainCircuit, Server, Settings2 } from "lucide-react";
import { FormEvent, useEffect, useState } from "react";

import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { RetryState } from "../components/ui/empty-state";
import { Input } from "../components/ui/input";
import { Select } from "../components/ui/select";
import { Skeleton } from "../components/ui/skeleton";
import { useApi } from "../hooks/useApi";
import { API_BASE_URL, api } from "../lib/api";

export function SettingsPage() {
  const { data, loading, error, refresh } = useApi(api.config, []);
  const embedding = useApi(api.embeddingSettings, []);
  const llm = useApi(api.llmSettings, []);
  const [backend, setBackend] = useState("jina");
  const [model, setModel] = useState("jina-embeddings-v5-text-small");
  const [apiKey, setApiKey] = useState("");
  const [llmProvider, setLlmProvider] = useState("moonshot");
  const [llmBaseUrl, setLlmBaseUrl] = useState("https://api.moonshot.ai/v1");
  const [llmModel, setLlmModel] = useState("kimi-k2.5");
  const [llmApiKey, setLlmApiKey] = useState("");
  const [saving, setSaving] = useState(false);
  const [savingLlm, setSavingLlm] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (embedding.data) {
      setBackend(embedding.data.embedding_backend);
      setModel(embedding.data.embedding_model);
    }
  }, [embedding.data]);

  useEffect(() => {
    if (llm.data) {
      setLlmProvider(llm.data.llm_provider || "moonshot");
      setLlmBaseUrl(llm.data.llm_base_url || "https://api.moonshot.ai/v1");
      setLlmModel(llm.data.llm_model || "kimi-k2.5");
    }
  }, [llm.data]);

  async function handleSaveEmbedding(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setMessage("");
    try {
      await api.updateEmbeddingSettings({
        embedding_backend: backend,
        embedding_model: model,
        jina_api_key: apiKey.trim() || undefined
      });
      setApiKey("");
      setMessage("Embedding 设置已保存。请对已入库知识库执行重建索引，使新模型生效。");
      await Promise.all([embedding.refresh(), refresh()]);
    } finally {
      setSaving(false);
    }
  }

  async function handleSaveLlm(event: FormEvent) {
    event.preventDefault();
    setSavingLlm(true);
    setMessage("");
    try {
      await api.updateLLMSettings({
        llm_provider: llmProvider,
        llm_base_url: llmBaseUrl,
        llm_model: llmModel,
        llm_api_key: llmApiKey.trim() || undefined
      });
      setLlmApiKey("");
      setMessage("Kimi / LLM 设置已保存。后续导入或重建 evidence 时会用于入库阶段证据增强。");
      await Promise.all([llm.refresh(), refresh()]);
    } finally {
      setSavingLlm(false);
    }
  }

  if (loading || embedding.loading || llm.loading) return <Skeleton className="h-[520px]" />;
  if (error || !data) return <RetryState message={error ?? "无法加载系统配置"} onRetry={refresh} />;

  const rows = [
    ["API Base URL", API_BASE_URL],
    ["Embedding Backend", embedding.data?.embedding_backend ?? data.embedding_backend],
    ["Embedding Model", embedding.data?.embedding_model ?? data.embedding_model],
    ["Embedding Source", embedding.data?.embedding_source ?? data.embedding_source ?? "environment"],
    ["Jina API Key", embedding.data?.jina_api_key_masked ?? "not configured"],
    ["Vector Store", data.vector_store],
    ["LLM Provider", llm.data?.llm_provider ?? data.llm_provider],
    ["LLM Model", llm.data?.llm_model ?? data.llm_model ?? "not configured"],
    ["LLM API Key", llm.data?.llm_api_key_masked ?? "not configured"],
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
            `MEDRAG_EMBEDDING_MODEL`、`MEDRAG_MINERU_API_URL` 和 Kimi/OpenAI-compatible LLM 配置。
          </div>
        </CardContent>
      </Card>

      <Card className="lg:col-span-2">
        <CardHeader>
          <CardTitle>Embedding 设置</CardTitle>
          <CardDescription>
            当前支持 Hash、Sentence Transformers 和 Jina Embeddings。修改后需要重建索引。
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form className="grid gap-4 lg:grid-cols-[220px_1fr_1fr_auto]" onSubmit={handleSaveEmbedding}>
            <div>
              <label className="mb-2 block text-sm font-medium">Backend</label>
              <Select value={backend} onChange={(event) => setBackend(event.target.value)}>
                <option value="jina">jina</option>
                <option value="hash">hash</option>
                <option value="sentence-transformers">sentence-transformers</option>
                <option value="auto">auto</option>
              </Select>
            </div>
            <div>
              <label className="mb-2 block text-sm font-medium">Model</label>
              <Input value={model} onChange={(event) => setModel(event.target.value)} />
            </div>
            <div>
              <label className="mb-2 block text-sm font-medium">Jina API Key</label>
              <Input
                type="password"
                value={apiKey}
                onChange={(event) => setApiKey(event.target.value)}
                placeholder={embedding.data?.jina_api_key_masked ?? "输入新 key，留空则不修改"}
              />
            </div>
            <div className="flex items-end">
              <Button className="w-full" disabled={saving}>
                {saving ? "保存中..." : "保存设置"}
              </Button>
            </div>
          </form>
          {message ? (
            <div className="mt-4 rounded-md border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900 dark:border-amber-700 dark:bg-amber-950/40 dark:text-amber-200">
              {message}
            </div>
          ) : null}
          <div className="mt-4 text-xs leading-5 text-muted-foreground">
            Jina 写入数据库后优先级高于 `.env`。API key 只以脱敏形式返回前端，不会进入 Git。
          </div>
        </CardContent>
      </Card>

      <Card className="lg:col-span-2">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <BrainCircuit className="h-4 w-4" />
            Kimi Evidence Enrichment 设置
          </CardTitle>
          <CardDescription>
            Kimi 仅在入库或重建 evidence 时抽取结构化医学证据，不参与每次查询实时抽取。
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form className="grid gap-4 lg:grid-cols-[180px_1fr_220px_1fr_auto]" onSubmit={handleSaveLlm}>
            <div>
              <label className="mb-2 block text-sm font-medium">Provider</label>
              <Select value={llmProvider} onChange={(event) => setLlmProvider(event.target.value)}>
                <option value="moonshot">moonshot</option>
                <option value="kimi">kimi</option>
                <option value="openai-compatible">openai-compatible</option>
                <option value="none">none</option>
              </Select>
            </div>
            <div>
              <label className="mb-2 block text-sm font-medium">Base URL</label>
              <Input value={llmBaseUrl} onChange={(event) => setLlmBaseUrl(event.target.value)} />
            </div>
            <div>
              <label className="mb-2 block text-sm font-medium">Model</label>
              <Input value={llmModel} onChange={(event) => setLlmModel(event.target.value)} />
            </div>
            <div>
              <label className="mb-2 block text-sm font-medium">API Key</label>
              <Input
                type="password"
                value={llmApiKey}
                onChange={(event) => setLlmApiKey(event.target.value)}
                placeholder={llm.data?.llm_api_key_masked ?? "输入新 key，留空则不修改"}
              />
            </div>
            <div className="flex items-end">
              <Button className="w-full" disabled={savingLlm}>
                {savingLlm ? "保存中..." : "保存设置"}
              </Button>
            </div>
          </form>
          <div className="mt-4 text-xs leading-5 text-muted-foreground">
            推荐配置：provider=`moonshot`，base URL=`https://api.moonshot.ai/v1`，
            model=`kimi-k2.5`。API key 只以脱敏形式返回前端。
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
