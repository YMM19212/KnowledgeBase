# Medical Semantic Chunking Strategy

Traditional fixed-length chunking can split clinical outcomes, eligibility criteria, tables, and figure captions away from their meaning. This project uses document logic first.

## Section-Aware Rules

The chunker recognizes common medical literature sections:

- Abstract
- Introduction
- Methods
- Participants
- Intervention
- Outcomes
- Primary outcome
- Secondary outcome
- Subgroup analysis
- Sensitivity analysis
- Results
- Discussion
- Conclusion
- Adverse events
- Limitations

The section path is preserved, for example `Methods > Outcomes > Primary outcome`.

## Tables and Figures

Tables and figures are not merged blindly into surrounding paragraphs. They become separate chunks with:

- `content_type=table` or `content_type=figure_caption`
- table or figure id in `source_span`
- page number
- citation text

This helps the retriever return baseline tables, endpoint tables, and clinical figure captions as evidence.

## Medical Evidence Units

Medical Semantic Chunking v2 adds an evidence-unit layer on top of chunks.
Compatibility is preserved through broad retrieval-facing `evidence_type`
values:

- `abstract_result`
- `primary_outcome`
- `secondary_outcome`
- `table_evidence`
- `figure_evidence`
- `clinical_question_answer`
- `safety_or_adverse_event`

Each chunk also stores a more specific `evidence_role` for evidence-aware
ranking:

- `baseline_table`
- `eligibility_criteria`
- `intervention_arm`
- `comparator_arm`
- `primary_endpoint_result`
- `secondary_endpoint_result`
- `adverse_event_result`
- `recommendation_block`
- `question_answer_block`
- `abstract_result`

The evidence unit is persisted in `evidence_units` and mirrored into chunk
metadata. It stores a short claim, page span, citation text, confidence,
evidence sufficiency, and a structured `normalized_facts` payload with
document-type-specific fields:

- `trial`: population, arm, comparator, endpoint type, timepoint, effect
  measure, effect value, CI, P value, adverse event
- `guideline`: recommendation statement, recommendation grade, evidence grade,
  clinical question id, target population
- `review_meta`: study count, sample size, pooled effect, heterogeneity
- `table`: role, table id, title, caption, headers, key values

## Kimi Enrichment

Rules always run first. If Kimi/Moonshot is configured, the ingest pipeline
sends each chunk to the OpenAI-compatible chat API once during ingestion or
evidence rebuild. Kimi can enrich structured fields for trial results,
guideline recommendations, review/meta summaries, and tables.

Kimi failures do not block ingestion. The system falls back to rule-generated
evidence, records `llm_enriched=false`, and keeps `extraction_mode=rule`.

## Fallback Token Control

`max_tokens` and `overlap_tokens` are only fallback controls. They split oversized section text after semantic grouping has already happened.

## Traceability Metadata

Each chunk stores:

- `document_id`
- `chunk_id`
- `section_path`
- `page_start`
- `page_end`
- `content_type`
- `evidence_level`
- `source_span`
- `citation_text`
- `evidence_type`
- `evidence_role`
- `document_type`
- `evidence_sufficiency`
- `extraction_mode`
- `llm_enriched`
