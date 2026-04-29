# Evaluation Plan

This project uses two evaluation layers:

- a generic medical RAG evaluation set for retrieval, citation, and faithfulness metrics
- the competition-provided question set exported to `examples/competition_queries.json`

## Parsing Quality

Use sampled PDFs with double-column layouts, baseline tables, endpoint tables, clinical plots, captions, and references.

Metrics:

- heading hierarchy accuracy
- table preservation accuracy
- caption-to-figure/table alignment
- page and bounding-box retention
- reference extraction accuracy

## Chunk Quality

Metrics:

- percentage of chunks with complete section path
- percentage of primary/secondary outcomes preserved without splitting key result sentences
- table and caption separation accuracy
- average citation metadata completeness

## Retrieval Quality

Build a question set covering:

- trial design
- eligibility criteria
- intervention
- primary outcome
- secondary outcome
- subgroup analysis
- adverse events
- limitations
- image-only diagnostic flowcharts
- rotated or long baseline tables
- old scanned tables with noisy OCR
- watermark-covered Chinese consensus pages
- abstract result sentences with medical units and symbols

Metrics:

- recall@k against expected section paths
- citation precision
- mean reciprocal rank
- evidence sufficiency rate

## Answer Faithfulness

Evaluate whether answers are fully supported by retrieved chunks.

Metrics:

- unsupported claim rate
- citation coverage
- refusal accuracy when evidence is insufficient

## Medical Safety

The system should not provide clinical recommendations beyond the literature evidence. For insufficient evidence, it must return “证据不足，无法可靠回答”.

## Competition Query Set

The official sample questions are stored in `examples/competition_queries.json`.
They are designed to stress the exact failure modes described in the competition topic:

| ID | Source | Target Capability |
| --- | --- | --- |
| competition-q1 | Stanford B 型主动脉夹层诊断和治疗中国专家共识（2022版） | figure caption and diagnostic flowchart traceability |
| competition-q2 | shchelochkov2019.pdf | long/rotated table preservation |
| competition-q3 | todo1992.pdf | old scanned table extraction |
| competition-q4 | 子宫内膜异位症超声评估中国专家共识.pdf | watermark-affected OCR and page-level provenance |
| competition-q5 | seyfarth2008.pdf | abstract result retrieval with medical symbols and units |

Recommended answer grading:

- **Recall@K**: whether the expected document and section/table/figure chunk appears in top K.
- **Citation Coverage**: whether every answer sentence is backed by at least one retrieved chunk.
- **Table Preservation Rate**: whether table rows, columns, and units remain aligned.
- **Evidence Sufficiency Rate**: whether the system refuses when MinerU output does not contain enough evidence.
- **Unit Integrity**: whether values such as `ΔCI = 0.11 ± 0.31 l/min/m2` remain intact after parsing, chunking, retrieval, and answer generation.
