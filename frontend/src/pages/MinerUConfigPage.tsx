import { useEffect, useState } from "react";
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
import { api } from "../lib/api";

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

export function MinerUConfigPage() {
  const config = useApi(api.config, []);
  const remoteSettings = useApi(api.mineruRemoteSettings, []);
  const remoteStatus = useApi(api.remoteMinerUStatus, []);
  const [form, setForm] = useState<RemoteForm>(defaultForm);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [messageType, setMessageType] = useState<"default" | "warning" | "danger">("default");

  useEffect(() => {
    if (!remoteSettings.data) return;
    setForm({
      host: remoteSettings.data.mineru_remote_host ?? "",
      port: String(remoteSettings.data.mineru_remote_port ?? 22),
      user: remoteSettings.data.mineru_remote_user ?? "root",
      password: "",
      keyPath: remoteSettings.data.mineru_remote_key_path ?? "",
      workDir: remoteSettings.data.mineru_remote_work_dir ?? "/tmp/medrag_mineru",
      outputDir: remoteSettings.data.mineru_remote_output_dir ?? "./data/mineru_remote_outputs"
    });
  }, [remoteSettings.data]);

  if (config.loading || remoteSettings.loading) return <Skeleton className="h-[640px]" />;
  if (config.error || !config.data) {
    return <RetryState message={config.error ?? "无法加载配置"} onRetry={config.refresh} />;
  }
  if (remoteSettings.error || !remoteSettings.data) {
    return (
      <RetryState
        message={remoteSettings.error ?? "无法加载远程 MinerU 配置"}
        onRetry={remoteSettings.refresh}
      />
    );
  }

  const remoteConfigured = remoteSettings.data.mineru_remote_configured;
  const remoteAvailable = remoteStatus.data?.available;
  const passwordLabel = remoteSettings.data.mineru_remote_password_configured
    ? `已保存：${remoteSettings.data.mineru_remote_password_masked ?? "已脱敏"}`
    : "未保存密码，可填写 SSH 密码";

  const update = (key: keyof RemoteForm, value: string) => {
    setForm((current) => ({ ...current, [key]: value }));
  };

  const handleSave = async () => {
    setSaving(true);
    setMessage(null);
    try {
      const port = Number.parseInt(form.port, 10);
      if (!form.host.trim()) throw new Error("请填写服务器 Host");
      if (!form.user.trim()) throw new Error("请填写 SSH 用户名");
      if (!Number.isInteger(port) || port < 1 || port > 65535) {
        throw new Error("端口必须在 1 到 65535 之间");
      }
      await api.updateMinerURemoteSettings({
        mineru_remote_host: form.host.trim(),
        mineru_remote_port: port,
        mineru_remote_user: form.user.trim(),
        mineru_remote_password: form.password.trim(),
        mineru_remote_key_path: form.keyPath.trim(),
        mineru_remote_work_dir: form.workDir.trim(),
        mineru_remote_output_dir: form.outputDir.trim()
      });
      setMessage("配置已保存。现在可以点击测试连接，确认服务器上的 mineru 命令是否可用。");
      setMessageType("default");
      setForm((current) => ({ ...current, password: "" }));
      await Promise.all([remoteSettings.refresh(), config.refresh()]);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "保存失败");
      setMessageType("danger");
    } finally {
      setSaving(false);
    }
  };

  const handleTest = async () => {
    setMessage("正在通过 SSH 测试远程 MinerU，请稍等。");
    setMessageType("warning");
    await remoteStatus.refresh();
    setMessage(null);
  };

  const checks = [
    {
      label: "连接信息",
      state: remoteConfigured ? "已配置" : "待配置",
      ok: remoteConfigured
    },
    {
      label: "SSH + mineru --version",
      state: remoteAvailable ? "可用" : remoteStatus.loading ? "检测中" : "待检测",
      ok: Boolean(remoteAvailable)
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

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="space-y-3">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <CardTitle className="flex items-center gap-2">
                <ServerCog className="h-5 w-5 text-primary" />
                远程 MinerU 连接向导
              </CardTitle>
              <CardDescription>
                用 SSH 连接服务器上的 MinerU，后端会上传 PDF、执行 pipeline、下载解析结果并自动写入知识库。
              </CardDescription>
            </div>
            <Badge variant={remoteConfigured ? "success" : "warning"}>
              {remoteConfigured ? "Remote MinerU Ready" : "需要配置"}
            </Badge>
          </div>
          <div className="grid gap-2 md:grid-cols-4">
            {[
              ["1", "填写 SSH"],
              ["2", "保存配置"],
              ["3", "测试连接"],
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
                填写私钥路径时优先使用密钥登录；不填则使用已保存的密码登录。
              </p>
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <label className="mb-2 block text-sm font-medium">服务器临时目录</label>
                <Input
                  value={form.workDir}
                  onChange={(event) => update("workDir", event.target.value)}
                />
              </div>
              <div>
                <label className="mb-2 block text-sm font-medium">本地解析结果目录</label>
                <Input
                  value={form.outputDir}
                  onChange={(event) => update("outputDir", event.target.value)}
                />
              </div>
            </div>
            {message ? <Alert variant={messageType}>{message}</Alert> : null}
            <div className="flex flex-wrap gap-2">
              <Button onClick={handleSave} disabled={saving}>
                {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
                保存配置
              </Button>
              <Button variant="outline" onClick={handleTest} disabled={remoteStatus.loading || !remoteConfigured}>
                {remoteStatus.loading ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <PlayCircle className="h-4 w-4" />
                )}
                测试连接
              </Button>
            </div>
          </div>

          <div className="space-y-4">
            <Card className="border-border/80 shadow-none">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-base">
                  {remoteAvailable ? (
                    <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                  ) : (
                    <CircleDot className="h-4 w-4 text-muted-foreground" />
                  )}
                  连接状态
                </CardTitle>
                <CardDescription>测试逻辑：SSH 登录服务器并执行 `mineru --version`。</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3 text-sm">
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">状态</span>
                  <Badge variant={remoteAvailable ? "success" : remoteStatus.data?.error ? "danger" : "outline"}>
                    {remoteAvailable ? "可用" : remoteStatus.data?.error ? "不可用" : "未检测"}
                  </Badge>
                </div>
                <div className="rounded-md bg-muted px-3 py-2 font-mono text-xs">
                  {remoteStatus.data?.command ?? `ssh ${form.user || "root"}@${form.host || "<host>"} mineru`}
                </div>
                {remoteStatus.data?.version ? (
                  <Alert>MinerU 版本：{remoteStatus.data.version}</Alert>
                ) : null}
                {remoteStatus.data?.error ? (
                  <Alert variant="danger">连接失败：{remoteStatus.data.error}</Alert>
                ) : null}
              </CardContent>
            </Card>

            <Card className="border-border/80 shadow-none">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-base">
                  <ShieldCheck className="h-4 w-4 text-primary" />
                  凭据保存策略
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2 text-sm leading-6 text-muted-foreground">
                <p>密码保存到本地 SQLite 运行时设置，接口读取时只返回脱敏值。</p>
                <p>生产部署建议改用 SSH key 或服务器侧 Secret Manager。</p>
                <p>当前配置来源：{remoteSettings.data.mineru_remote_source}</p>
              </CardContent>
            </Card>
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-4 lg:grid-cols-[0.9fr_1.1fr]">
        <Card>
          <CardHeader>
            <CardTitle>接入检查清单</CardTitle>
            <CardDescription>从连接配置到知识库入库的完整链路。</CardDescription>
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
              使用边界
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm leading-6 text-muted-foreground">
            <Alert>
              配置完成后，到知识库详情页选择 PDF，点击“用远程 MinerU 入库”。系统会自动执行
              PDF → MinerU pipeline → 医学语义切分 → Evidence Unit → 向量索引。
            </Alert>
            <div className="grid gap-3 md:grid-cols-3">
              {[
                ["Mock Parser", "用于无 MinerU 时演示样例 JSON 入库"],
                ["Local MinerU", "适合本机已安装 mineru 的开发环境"],
                ["Remote MinerU", "适合把耗时解析放到 GPU/服务器环境"]
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
              MinerU 仍负责复杂版面解析；本知识库负责解析结果标准化、医学证据切分、入库、检索和可溯源问答。
            </p>
            <p>
              当前 API Base URL：<span className="font-mono text-foreground">{config.data.api_prefix}</span>
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
