# Evaluation Plan

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

