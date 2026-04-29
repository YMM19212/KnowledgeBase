import {
  Activity,
  Bot,
  Database,
  FileText,
  Gauge,
  Microscope,
  Settings,
  SlidersHorizontal
} from "lucide-react";

export const navItems = [
  { label: "Dashboard", path: "/", icon: Gauge },
  { label: "知识库", path: "/knowledge-bases", icon: Database },
  { label: "文档管理", path: "/documents", icon: FileText },
  { label: "RAG 问答", path: "/rag", icon: Bot },
  { label: "MinerU 配置", path: "/mineru", icon: SlidersHorizontal },
  { label: "评测分析", path: "/evaluation", icon: Activity },
  { label: "系统设置", path: "/settings", icon: Settings },
  { label: "医疗语义切分", path: "/evaluation#chunking", icon: Microscope }
];

