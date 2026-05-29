import { useEffect, useMemo, useState } from "react";
import {
  ArrowRight,
  CheckCircle2,
  CircleDot,
  KeyRound,
  Loader2,
  PlayCircle,
  Save,
  ServerCog,
  ShieldCheck,
  UploadCloud,
  Workflow,
  XCircle
} from "lucide-react";

import { Alert } from "../components/ui/alert";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { RetryState } from "../components/ui/empty-state";
import { Input } from "../components/ui/input";
import { Skeleton } from "../components/ui/skeleton";
import { useApi } from "../hooks/useApi";
import { API_BASE_URL, api } from "../lib/api";

type MinerUMode = "local-cli" | "remote-ssh";

type RemoteForm = {
  host: string;
  port: string;
  user: string;
  password: string;
  keyPath: string;
  workDir: string;
  outputDir: string;
};

const defaultForm: RemoteForm = {
  host: "",
  port: "22",
  user: "root",
  password: "",
  keyPath: "",
  workDir: "/tmp/medrag_mineru",
  outputDir: "./data/mineru_remote_outputs"
};

function normalizeMode(source?: string | null): MinerUMode {
  return source === "local-cli" ? "local-cli" : "remote-ssh";
}

export function MinerUConfigPage() {
  const config = useApi(api.config, []);
  const mineruSettings = useApi(api.mineruSettings, []);
  const localStatus = useApi(api.localMinerUStatus, []);
  const remoteStatus = useApi(api.remoteMinerUStatus, []);
  const [form, setForm] = useState<RemoteForm>(defaultForm);
  const [sourceMode, setSourceMode] = useState<MinerUMode>("remote-ssh");
  const [saving, setSaving] = useState(false);
  const [switching, setSwitching] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [messageType, setMessageType] = useState<"default" | "warning" | "danger">("default");

  const sourceSeed = mineruSettings.data?.mineru_source ?? config.data?.mineru_source;
  const remoteSeed = mineruSettings.data ?? config.data;
  const recommendedEndpoint =
    mineruSettings.data?.recommended_upload_endpoint ?? "/api/v1/knowledge-bases/{kb_id}/documents/ingest";
  const examples = mineruSettings.data?.examples ?? [];

  useEffect(() => {
    setSourceMode(normalizeMode(sourceSeed));
  }, [sourceSeed]);

  useEffect(() => {
    if (!remoteSeed) return;
    setForm({
      host: remoteSeed.mineru_remote_host ?? "",
      port: String(remoteSeed.mineru_remote_port ?? 22),
      user: remoteSeed.mineru_remote_user ?? "root",
      password: "",
      keyPath: remoteSeed.mineru_remote_key_path ?? "",
      workDir: remoteSeed.mineru_remote_work_dir ?? "/tmp/medrag_mineru",
      outputDir: remoteSeed.mineru_remote_output_dir ?? "./data/mineru_remote_outputs"
    });
  }, [remoteSeed]);

  const localAvailable = Boolean(localStatus.data?.available);
  const remoteConfigured = Boolean(
    mineruSettings.data?.mineru_remote_configured ?? config.data?.mineru_remote_configured
  );
  const remoteAvailable = Boolean(remoteStatus.data?.available);
  const passwordLabel =
    mineruSettings.data?.mineru_remote_password_configured || config.data?.mineru_remote_password_configured
      ? `已保存：${
          mineruSettings.data?.mineru_remote_password_masked ??
          config.data?.mineru_remote_password_masked ??
          "已脱敏"
        }`
      : "未保存密码，可填写 SSH 密码";

  const checks = useMemo(() => {
    if (sourceMode === "local-cli") {
      return [
        {
          label: "当前来源",
          state: "本地 MinerU",
          ok: true
        },
        {
          label: "mineru --version",
          state: localAvailable ? "可用" : localStatus.loading ? "检测中" : "待检测",
          ok: localAvailable
        },
        {
          label: "本地输出目录",
          state: mineruSettings.data?.mineru_local_output_dir ?? config.data?.mineru_local_output_dir ?? "未配置",
          ok: Boolean(mineruSettings.data?.mineru_local_output_dir ?? config.data?.mineru_local_output_dir)
        },
        {
          label: "知识库上传 PDF",
          state: "统一入库接口或本地 MinerU 入库接口",
          ok: true
        }
      ];
    }
    return [
      {
        label: "连接信息",
        state: remoteConfigured ? "已配置" : "待配置",
        ok: remoteConfigured
      },
      {
        label: "SSH + mineru --version",
        state: remoteAvailable ? "可用" : remoteStatus.loading ? "检测中" : "待检测",
        ok: remoteAvailable
      },
      {
        label: "PDF 上传到服务器",
        state: remoteConfigured ? "入库时自动执行" : "配置后启用",
        ok: remoteConfigured
      },
      {
        label: "MinerU 输出下载并入库",
        state: "已接入知识库流程",
        ok: true
      }
    ];
  }, [
    config.data?.mineru_local_output_dir,
    localAvailable,
    localStatus.loading,
    mineruSettings.data?.mineru_local_output_dir,
    remoteAvailable,
    remoteConfigured,
    remoteStatus.loading,
    sourceMode
  ]);

  if (config.loading && !config.data) return <Skeleton className="h-[720px]" />;
  if (config.error || !config.data) {
    return <RetryState message={config.error ?? "无法加载配置"} onRetry={config.refresh} />;
  }

  const update = (key: keyof RemoteForm, value: string) => {
    setForm((current) => ({ ...current, [key]: value }));
  };

  const refreshAll = async () => {
    await Promise.all([config.refresh(), mineruSettings.refresh()]);
  };

  const handleSelectMode = async (mode: MinerUMode) => {
    if (mode === sourceMode) return;
    const previousMode = sourceMode;
    setSourceMode(mode);
    setSwitching(true);
    setMessage(null);
    try {
      await api.updateMineruSettings({ mineru_source: mode });
      await refreshAll();
      setMessage(
        mode === "local-cli"
          ? "已切换到本地 MinerU。上传 PDF 时可以直接在当前机器运行 MinerU pipeline。"
          : "已切换到远程 MinerU。上传 PDF 时会优先走 SSH 服务器解析链路。"
      );
      setMessageType("default");
    } catch (error) {
      setSourceMode(previousMode);
      setMessage(error instanceof Error ? error.message : "切换失败");
      setMessageType("danger");
    } finally {
      setSwitching(false);
    }
  };

  const handleSaveRemote = async () => {
    setSaving(true);
    setMessage(null);
    try {
      const port = Number.parseInt(form.port, 10);
      if (!form.host.trim()) throw new Error("请填写服务器 Host");
      if (!form.user.trim()) throw new Error("请填写 SSH 用户名");
      if (!Number.isInteger(port) || port < 1 || port > 65535) {
        throw new Error("端口必须在 1 到 65535 之间");
      }
      await api.updateMineruSettings({
        mineru_source: "remote-ssh",
        mineru_remote_host: form.host.trim(),
        mineru_remote_port: port,
        mineru_remote_user: form.user.trim(),
        mineru_remote_password: form.password.trim(),
        mineru_remote_key_path: form.keyPath.trim(),
        mineru_remote_work_dir: form.workDir.trim(),
        mineru_remote_output_dir: form.outputDir.trim()
      });
      setMessage("远程 MinerU 配置已保存。现在可以点击测试连接，确认服务器上的 mineru 命令可用。");
      setMessageType("default");
      setForm((current) => ({ ...current, password: "" }));
      await refreshAll();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "保存失败");
      setMessageType("danger");
    } finally {
      setSaving(false);
    }
  };

  const handleTestLocal = async () => {
    setMessage("正在测试本地 MinerU，请稍等。");
    setMessageType("warning");
    await localStatus.refresh();
    setMessage(null);
  };

  const handleTestRemote = async () => {
    setMessage("正在通过 SSH 测试远程 MinerU，请稍等。");
    setMessageType("warning");
    await remoteStatus.refresh();
    setMessage(null);
  };

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="space-y-3">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <CardTitle className="flex items-center gap-2">
                <ServerCog className="h-5 w-5 text-primary" />
                MinerU 来源配置
              </CardTitle>
              <CardDescription>
                先选择 MinerU 运行位置，再配置对应来源。知识库入库会按照当前来源执行
                PDF → MinerU pipeline → 医学语义切分 → Evidence Unit → 向量索引。
              </CardDescription>
            </div>
            <Badge variant={sourceMode === "local-cli" ? "outline" : remoteConfigured ? "success" : "warning"}>
              {sourceMode === "local-cli" ? "Local MinerU" : remoteConfigured ? "Remote MinerU Ready" : "需要配置"}
            </Badge>
          </div>

          <div className="flex flex-wrap gap-2">
            <Button
              variant={sourceMode === "local-cli" ? "default" : "outline"}
              onClick={() => void handleSelectMode("local-cli")}
              disabled={switching}
            >
              {switching && sourceMode !== "local-cli" ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <UploadCloud className="h-4 w-4" />
              )}
              本地 MinerU
            </Button>
            <Button
              variant={sourceMode === "remote-ssh" ? "default" : "outline"}
              onClick={() => void handleSelectMode("remote-ssh")}
              disabled={switching}
            >
              {switching && sourceMode !== "remote-ssh" ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <ServerCog className="h-4 w-4" />
              )}
              远程 MinerU
            </Button>
          </div>

          <div className="grid gap-2 md:grid-cols-4">
            {[
              ["1", "选择来源"],
              ["2", sourceMode === "local-cli" ? "检查本地环境" : "填写 SSH"],
              ["3", sourceMode === "local-cli" ? "测试本地命令" : "测试远程连接"],
              ["4", "知识库上传 PDF"]
            ].map(([step, label], index) => (
              <div key={step} className="flex items-center gap-2 rounded-md border border-border px-3 py-2">
                <span className="flex h-6 w-6 items-center justify-center rounded-full bg-primary text-xs font-semibold text-primary-foreground">
                  {step}
                </span>
                <span className="text-sm font-medium">{label}</span>
                {index < 3 ? <ArrowRight className="ml-auto hidden h-4 w-4 text-muted-foreground lg:block" /> : null}
              </div>
            ))}
          </div>
        </CardHeader>

        <CardContent className="grid gap-4 xl:grid-cols-[1.15fr_0.85fr]">
          <div className="space-y-4 rounded-lg border border-border p-4">
            {mineruSettings.error ? (
              <Alert variant="warning">
                MinerU 配置接口暂时不可用：{mineruSettings.error}。页面会继续显示当前表单；
                保存失败时请确认 FastAPI 已重启到最新代码。
              </Alert>
            ) : null}

            {sourceMode === "local-cli" ? (
              <div className="space-y-4">
                <Alert>
                  本地模式适合当前机器已经安装 `mineru` 的场景。统一入库接口会优先按“本地
                  CLI”执行，也可以继续使用现有本地 MinerU 上传按钮。
                </Alert>

                <div className="rounded-md border border-border p-4">
                  <div className="mb-2 text-sm font-medium">本地命令</div>
                  <div className="rounded-md bg-muted px-3 py-2 font-mono text-xs">
                    {localStatus.data?.command ??
                      mineruSettings.data?.mineru_cli_command ??
                      config.data.mineru_cli_command ??
                      "mineru"}
                  </div>
                </div>

                <div className="grid gap-4 md:grid-cols-2">
                  <div className="rounded-md border border-border p-4">
                    <div className="mb-2 text-sm font-medium">本地解析结果目录</div>
                    <div className="font-mono text-xs text-muted-foreground">
                      {mineruSettings.data?.mineru_local_output_dir ?? config.data.mineru_local_output_dir}
                    </div>
                  </div>
                  <div className="rounded-md border border-border p-4">
                    <div className="mb-2 text-sm font-medium">统一入库接口</div>
                    <div className="font-mono text-xs text-muted-foreground">{recommendedEndpoint}</div>
                  </div>
                </div>

                {message ? <Alert variant={messageType}>{message}</Alert> : null}
                <div className="flex flex-wrap gap-2">
                  <Button variant="outline" onClick={() => void handleTestLocal()} disabled={localStatus.loading}>
                    {localStatus.loading ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <PlayCircle className="h-4 w-4" />
                    )}
                    测试本地 MinerU
                  </Button>
                </div>
              </div>
            ) : (
              <div className="space-y-4">
                <div className="grid gap-4 md:grid-cols-[1fr_130px]">
                  <div>
                    <label className="mb-2 block text-sm font-medium">服务器 Host</label>
                    <Input
                      value={form.host}
                      onChange={(event) => update("host", event.target.value)}
                      placeholder="例如 172.31.22.13"
                    />
                  </div>
                  <div>
                    <label className="mb-2 block text-sm font-medium">SSH 端口</label>
                    <Input value={form.port} onChange={(event) => update("port", event.target.value)} />
                  </div>
                </div>
                <div className="grid gap-4 md:grid-cols-2">
                  <div>
                    <label className="mb-2 block text-sm font-medium">SSH 用户</label>
                    <Input
                      value={form.user}
                      onChange={(event) => update("user", event.target.value)}
                      placeholder="root"
                    />
                  </div>
                  <div>
                    <label className="mb-2 block text-sm font-medium">SSH 密码</label>
                    <Input
                      type="password"
                      value={form.password}
                      onChange={(event) => update("password", event.target.value)}
                      placeholder={passwordLabel}
                    />
                  </div>
                </div>
                <div>
                  <label className="mb-2 flex items-center gap-2 text-sm font-medium">
                    <KeyRound className="h-4 w-4 text-muted-foreground" />
                    SSH 私钥路径，可选
                  </label>
                  <Input
                    value={form.keyPath}
                    onChange={(event) => update("keyPath", event.target.value)}
                    placeholder="/Users/you/.ssh/id_rsa"
                  />
                  <p className="mt-1 text-xs text-muted-foreground">
                    填写私钥路径时优先使用密钥登录；留空时使用已保存的密码登录。`.` 或目录路径不会再被当成私钥。
                  </p>
                </div>
                <div className="grid gap-4 md:grid-cols-2">
                  <div>
                    <label className="mb-2 block text-sm font-medium">服务器临时目录</label>
                    <Input value={form.workDir} onChange={(event) => update("workDir", event.target.value)} />
                  </div>
                  <div>
                    <label className="mb-2 block text-sm font-medium">本地解析结果目录</label>
                    <Input value={form.outputDir} onChange={(event) => update("outputDir", event.target.value)} />
                  </div>
                </div>
                {message ? <Alert variant={messageType}>{message}</Alert> : null}
                <div className="flex flex-wrap gap-2">
                  <Button onClick={() => void handleSaveRemote()} disabled={saving}>
                    {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
                    保存远程配置
                  </Button>
                  <Button
                    variant="outline"
                    onClick={() => void handleTestRemote()}
                    disabled={remoteStatus.loading || !remoteConfigured}
                  >
                    {remoteStatus.loading ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <PlayCircle className="h-4 w-4" />
                    )}
                    测试远程 MinerU
                  </Button>
                </div>
              </div>
            )}
          </div>

          <div className="space-y-4">
            <Card className="border-border/80 shadow-none">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-base">
                  {(sourceMode === "local-cli" ? localAvailable : remoteAvailable) ? (
                    <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                  ) : (
                    <CircleDot className="h-4 w-4 text-muted-foreground" />
                  )}
                  连接状态
                </CardTitle>
                <CardDescription>
                  {sourceMode === "local-cli"
                    ? "测试逻辑：在当前机器执行 `mineru --version`。"
                    : "测试逻辑：SSH 登录服务器并执行 `mineru --version`。"}
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3 text-sm">
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">状态</span>
                  <Badge
                    variant={
                      sourceMode === "local-cli"
                        ? localAvailable
                          ? "success"
                          : localStatus.data?.error
                            ? "danger"
                            : "outline"
                        : remoteAvailable
                          ? "success"
                          : remoteStatus.data?.error
                            ? "danger"
                            : "outline"
                    }
                  >
                    {sourceMode === "local-cli"
                      ? localAvailable
                        ? "可用"
                        : localStatus.data?.error
                          ? "不可用"
                          : "未检测"
                      : remoteAvailable
                        ? "可用"
                        : remoteStatus.data?.error
                          ? "不可用"
                          : "未检测"}
                  </Badge>
                </div>
                <div className="rounded-md bg-muted px-3 py-2 font-mono text-xs">
                  {sourceMode === "local-cli"
                    ? localStatus.data?.command ??
                      mineruSettings.data?.mineru_cli_command ??
                      config.data.mineru_cli_command ??
                      "mineru"
                    : remoteStatus.data?.command ?? `ssh ${form.user || "root"}@${form.host || "<host>"} mineru`}
                </div>
                {(sourceMode === "local-cli" ? localStatus.data?.version : remoteStatus.data?.version) ? (
                  <Alert>
                    MinerU 版本：
                    {sourceMode === "local-cli" ? localStatus.data?.version : remoteStatus.data?.version}
                  </Alert>
                ) : null}
                {(sourceMode === "local-cli" ? localStatus.data?.error : remoteStatus.data?.error) ? (
                  <Alert variant="danger">
                    连接失败：
                    {sourceMode === "local-cli" ? localStatus.data?.error : remoteStatus.data?.error}
                  </Alert>
                ) : null}
              </CardContent>
            </Card>

            <Card className="border-border/80 shadow-none">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-base">
                  <ShieldCheck className="h-4 w-4 text-primary" />
                  当前生效策略
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2 text-sm leading-6 text-muted-foreground">
                <p>当前首选来源：{sourceMode === "local-cli" ? "本地 MinerU CLI" : "远程 MinerU SSH"}</p>
                <p>运行时配置来源：{mineruSettings.data?.mineru_source_origin ?? config.data.mineru_source_origin ?? "unknown"}</p>
                <p>
                  远程密码保存到本地 SQLite 运行时设置，接口读取时只返回脱敏值；本地模式不需要单独凭据。
                </p>
              </CardContent>
            </Card>
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-4 lg:grid-cols-[0.9fr_1.1fr]">
        <Card>
          <CardHeader>
            <CardTitle>接入检查清单</CardTitle>
            <CardDescription>从来源选择到知识库入库的完整链路。</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {checks.map((check) => (
              <div key={check.label} className="flex items-center justify-between rounded-md border border-border px-3 py-2">
                <div className="flex items-center gap-2 text-sm">
                  {check.ok ? (
                    <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                  ) : (
                    <XCircle className="h-4 w-4 text-amber-600" />
                  )}
                  {check.label}
                </div>
                <Badge variant={check.ok ? "success" : "warning"}>{check.state}</Badge>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Workflow className="h-4 w-4" />
              使用边界与示例
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm leading-6 text-muted-foreground">
            <Alert>
              当前推荐统一入库接口：<span className="font-mono text-foreground">{recommendedEndpoint}</span>。
              已有问答接口不会受影响，MinerU 只负责文档清洗入库链路。
            </Alert>
            <div className="grid gap-3 md:grid-cols-3">
              {[
                ["Mock Parser", "用于无 MinerU 时演示样例 JSON 入库"],
                ["Local MinerU", "适合本机已安装 mineru 的开发环境"],
                ["Remote MinerU", "适合把耗时解析放到 GPU 或服务器环境"]
              ].map(([title, body]) => (
                <div key={title} className="rounded-md border border-border p-3">
                  <div className="mb-1 flex items-center gap-2 font-medium text-foreground">
                    <UploadCloud className="h-4 w-4 text-primary" />
                    {title}
                  </div>
                  <p>{body}</p>
                </div>
              ))}
            </div>
            <p>
              MinerU 负责复杂版面解析；本知识库负责解析结果标准化、医学证据切分、入库、检索和可溯源问答。
            </p>
            <p>
              当前 API Base URL：<span className="font-mono text-foreground">{API_BASE_URL}</span>
            </p>
            {examples.length ? (
              <div className="space-y-3">
                {examples.map((example) => (
                  <div key={example.source} className="rounded-md border border-border p-3">
                    <div className="mb-1 flex items-center justify-between gap-2">
                      <div className="font-medium text-foreground">{example.label}</div>
                      <Badge variant={example.source === sourceMode ? "success" : "outline"}>{example.source}</Badge>
                    </div>
                    <p className="mb-3 text-xs leading-5">{example.description}</p>
                    <pre className="overflow-x-auto rounded-md bg-muted px-3 py-2 text-xs text-foreground">
                      {JSON.stringify(example.example_config, null, 2)}
                    </pre>
                  </div>
                ))}
              </div>
            ) : null}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
