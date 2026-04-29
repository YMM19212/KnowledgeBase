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

