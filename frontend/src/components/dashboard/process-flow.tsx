import { Bot, Database, FileText, GitBranch, Layers3, Link2 } from "lucide-react";

const steps = [
  { label: "PDF", detail: "医疗文献", icon: FileText },
  { label: "MinerU 解析", detail: "版式/表格/图注", icon: GitBranch },
  { label: "语义切分", detail: "章节与医学终点", icon: Layers3 },
  { label: "向量索引", detail: "metadata + embedding", icon: Database },
  { label: "RAG 问答", detail: "证据约束生成", icon: Bot },
  { label: "溯源引用", detail: "chunk/page/source", icon: Link2 }
];

export function ProcessFlow() {
  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-6">
      {steps.map((step, index) => (
        <div key={step.label} className="relative rounded-lg border border-border bg-card p-4">
          <step.icon className="h-5 w-5 text-primary" />
          <div className="mt-3 text-sm font-semibold">{step.label}</div>
          <div className="mt-1 text-xs text-muted-foreground">{step.detail}</div>
          {index < steps.length - 1 ? (
            <div className="absolute -right-2 top-1/2 hidden h-px w-4 bg-border xl:block" />
          ) : null}
        </div>
      ))}
    </div>
  );
}

