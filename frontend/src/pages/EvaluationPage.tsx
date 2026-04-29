import { LineChart as LineChartIcon } from "lucide-react";
import {
  CartesianGrid,
  Line,
  LineChart,
  Radar,
  RadarChart,
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";

import { Badge } from "../components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";

const metrics = [
  { name: "Recall@K", value: 0.86 },
  { name: "Citation Coverage", value: 0.92 },
  { name: "Chunk Completeness", value: 0.88 },
  { name: "Table Preservation Rate", value: 0.81 },
  { name: "Evidence Sufficiency Rate", value: 0.79 }
];

const trend = [
  { batch: "B1", recall: 0.68, citation: 0.72, completeness: 0.7 },
  { batch: "B2", recall: 0.74, citation: 0.79, completeness: 0.76 },
  { batch: "B3", recall: 0.8, citation: 0.86, completeness: 0.82 },
  { batch: "B4", recall: 0.86, citation: 0.92, completeness: 0.88 }
];

export function EvaluationPage() {
  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <LineChartIcon className="h-5 w-5 text-primary" />
            评测与分析
          </CardTitle>
          <CardDescription>
            Mock 指标用于比赛答辩展示，后续可替换为 MedBench 或自定义医疗问答评测集结果。
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-3 md:grid-cols-5">
          {metrics.map((metric) => (
            <div key={metric.name} className="rounded-lg border border-border p-4">
              <div className="text-xs text-muted-foreground">{metric.name}</div>
              <div className="mt-2 text-2xl font-semibold">{Math.round(metric.value * 100)}%</div>
              <Badge className="mt-2" variant="success">
                mock benchmark
              </Badge>
            </div>
          ))}
        </CardContent>
      </Card>

      <div className="grid gap-4 xl:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>指标趋势</CardTitle>
            <CardDescription>语义切分与溯源策略迭代后的模拟趋势。</CardDescription>
          </CardHeader>
          <CardContent className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={trend}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="batch" />
                <YAxis domain={[0, 1]} />
                <Tooltip />
                <Line type="monotone" dataKey="recall" stroke="hsl(var(--primary))" strokeWidth={2} />
                <Line type="monotone" dataKey="citation" stroke="#14b8a6" strokeWidth={2} />
                <Line type="monotone" dataKey="completeness" stroke="#64748b" strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>能力雷达</CardTitle>
            <CardDescription>覆盖召回、引用、chunk 完整性、表格保真和证据充分性。</CardDescription>
          </CardHeader>
          <CardContent className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart data={metrics}>
                <PolarGrid />
                <PolarAngleAxis dataKey="name" />
                <PolarRadiusAxis domain={[0, 1]} tick={false} />
                <Radar dataKey="value" fill="hsl(var(--primary))" fillOpacity={0.18} stroke="hsl(var(--primary))" />
                <Tooltip />
              </RadarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      <div id="chunking" className="grid gap-4 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle>语义切分优于固定字数</CardTitle>
          </CardHeader>
          <CardContent className="text-sm leading-6 text-muted-foreground">
            医学论文的核心证据常依赖章节层级、终点定义和结果表格。固定字数切分容易把
            Primary outcome 的定义、统计结果和结论拆散，导致召回片段缺少完整上下文。
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>医疗 RAG 必须可溯源</CardTitle>
          </CardHeader>
          <CardContent className="text-sm leading-6 text-muted-foreground">
            临床科研与决策支持不能接受无来源回答。系统返回 document_id、section_path、page 和
            source text，便于人工复核与责任边界控制。
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>对接 MedBench</CardTitle>
          </CardHeader>
          <CardContent className="text-sm leading-6 text-muted-foreground">
            后续可将 query set、gold evidence、答案评分器接入 evaluation 模块，统计 Recall@K、
            Citation Coverage、Faithfulness 与拒答准确率。
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

