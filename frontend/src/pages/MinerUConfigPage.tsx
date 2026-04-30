import { CheckCircle2, ServerCog, Workflow } from "lucide-react";

import { Alert } from "../components/ui/alert";
import { Badge } from "../components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { RetryState } from "../components/ui/empty-state";
import { Input } from "../components/ui/input";
import { Skeleton } from "../components/ui/skeleton";
import { useApi } from "../hooks/useApi";
import { api } from "../lib/api";

export function MinerUConfigPage() {
  const { data, loading, error, refresh } = useApi(api.config, []);
  const localStatus = useApi(api.localMinerUStatus, []);
  const remoteStatus = useApi(api.remoteMinerUStatus, []);

  if (loading) return <Skeleton className="h-[520px]" />;
  if (error || !data) return <RetryState message={error ?? "无法加载配置"} onRetry={refresh} />;

  const checks = [
    { label: "local mineru CLI", state: localStatus.data?.available ? "available" : "check needed" },
    { label: "remote mineru SSH", state: remoteStatus.data?.available ? "available" : "check needed" },
    { label: "submit_parse_task()", state: data.parser_mode === "mineru" ? "ready" : "reserved" },
    { label: "get_parse_result()", state: data.parser_mode === "mineru" ? "ready" : "reserved" },
    { label: "normalize_mineru_json()", state: "implemented boundary" },
    { label: "MockParser", state: data.parser_mode === "mock" ? "active" : "standby" }
  ];

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <ServerCog className="h-5 w-5 text-primary" />
            MinerU 接入配置
          </CardTitle>
          <CardDescription>
            当前项目保留 MinerU 服务器适配层，正式接入时不影响下游切分、索引和 RAG。
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 lg:grid-cols-2">
          <div>
            <label className="mb-2 block text-sm font-medium">MinerU API URL</label>
            <Input readOnly value={data.mineru_api_url || "未配置，当前使用 Mock Parser"} />
          </div>
          <div>
            <label className="mb-2 block text-sm font-medium">Parser Mode</label>
            <Input readOnly value={data.parser_mode} />
          </div>
          <div>
            <label className="mb-2 block text-sm font-medium">Local MinerU Command</label>
            <Input readOnly value={data.mineru_cli_command || "mineru"} />
          </div>
          <div>
            <label className="mb-2 block text-sm font-medium">Local Output Directory</label>
            <Input readOnly value={data.mineru_local_output_dir || "./data/mineru_outputs"} />
          </div>
          <div>
            <label className="mb-2 block text-sm font-medium">Remote MinerU Host</label>
            <Input readOnly value={data.mineru_remote_host || "未配置"} />
          </div>
          <div>
            <label className="mb-2 block text-sm font-medium">Remote Work Directory</label>
            <Input readOnly value={data.mineru_remote_work_dir || "/tmp/medrag_mineru"} />
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-4 lg:grid-cols-[0.9fr_1.1fr]">
        <Card>
          <CardHeader>
            <CardTitle>接口状态</CardTitle>
            <CardDescription>后端 `MinerUParserAdapter` 的接入边界。</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {checks.map((check) => (
              <div key={check.label} className="flex items-center justify-between rounded-md border border-border px-3 py-2">
                <div className="flex items-center gap-2 text-sm">
                  <CheckCircle2 className="h-4 w-4 text-primary" />
                  {check.label}
                </div>
                <Badge variant={check.state === "active" || check.state === "ready" ? "success" : "outline"}>
                  {check.state}
                </Badge>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Workflow className="h-4 w-4" />
              Mock 阶段与正式阶段边界
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm leading-6 text-muted-foreground">
            <Alert>
              当前 Mock 阶段读取 `examples/sample_mineru_output.json`，用于验证知识库构建、医疗语义切分、
              向量索引、RAG 检索和可溯源引用。
            </Alert>
            <p>
              正式阶段只需要在后端实现 PDF 上传、任务轮询和 MinerU JSON 标准化。只要输出仍映射为
              `ParsedDocument`，前端和下游索引检索链路不需要改动。
            </p>
            <p>
              推荐新增配置：解析语言、OCR 模式、表格抽取强度、图注关联策略、任务超时与重试策略。
            </p>
            <p>
              当前支持 SSH 远程模式：后端通过 SFTP 上传 PDF 到服务器，执行服务器上的 `mineru`
              pipeline，再下载 MinerU 输出目录并复用现有知识库入库流程。
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
