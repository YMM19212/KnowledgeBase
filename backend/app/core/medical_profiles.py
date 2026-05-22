import re
from collections.abc import Iterable

DOCUMENT_TYPE_PATTERNS = {
    "guideline_consensus": [
        r"guideline",
        r"consensus",
        r"statement",
        r"recommendation",
        r"共识",
        r"指南",
        r"推荐意见",
    ],
    "review_meta": [
        r"meta[- ]analysis",
        r"systematic review",
        r"review article",
        r"综述",
        r"meta分析",
        r"meta 分析",
        r"系统综述",
    ],
    "trial": [
        r"trial",
        r"randomized",
        r"double-blind",
        r"placebo",
        r"clinical trial",
        r"study",
        r"randomisation",
        r"randomization",
        r"随机",
        r"试验",
    ],
}

MEDICAL_SCOPE_HINTS = (
    "主要结局",
    "次要结局",
    "纳入标准",
    "排除标准",
    "基线",
    "推荐意见",
    "证据等级",
    "不良事件",
    "安全性",
    "摘要",
    "结果",
    "方法",
    "结论",
    "participants",
    "intervention",
    "primary outcome",
    "secondary outcome",
    "adverse events",
    "recommendation",
    "eligibility",
    "baseline",
)


def infer_document_type(title: str, abstract: str | None, section_paths: Iterable[str]) -> str:
    corpus = " ".join([title or "", abstract or "", *section_paths]).lower()
    for document_type, patterns in DOCUMENT_TYPE_PATTERNS.items():
        if any(re.search(pattern, corpus, re.I) for pattern in patterns):
            return document_type
    return "other"


def extract_question_id(text: str) -> str | None:
    digit_match = re.search(r"问题\s*([0-9]{1,2})", text)
    if digit_match:
        return f"问题{digit_match.group(1)}"
    zh_match = re.search(r"问题\s*([一二三四五六七八九十]{1,3})", text)
    if zh_match:
        return f"问题{zh_match.group(1)}"
    return None


def normalize_section_path(section_path: str) -> str:
    normalized = re.sub(r"\s+", " ", section_path).strip()
    question_id = extract_question_id(normalized)
    if question_id and question_id not in normalized:
        normalized = f"{question_id} > {normalized}"
    return normalized


def classify_table_role(
    section_path: str,
    title: str | None,
    caption: str | None,
    markdown: str,
    document_type: str,
) -> str:
    corpus = " ".join(filter(None, [section_path, title, caption, markdown])).lower()
    if re.search(r"baseline|characteristics|demographic|基线|特征", corpus):
        return "baseline_table"
    if re.search(r"adverse|safety|harms?|不良|安全", corpus):
        return "safety_table"
    if re.search(r"outcome|endpoint|结局|终点|results?", corpus):
        return "outcome_table"
    if re.search(r"abbreviations?|acronyms?", corpus):
        return "abbreviation_table"
    if re.search(r"reference|supplement|appendix|evidence grade|loe", corpus):
        return "reference_supporting_table"
    if document_type == "guideline_consensus" and re.search(r"专家组|成员|evidence", corpus):
        return "reference_supporting_table"
    return "supporting_table"


def classify_text_role(
    section_path: str,
    text: str,
    content_type: str,
    document_type: str,
    page_start: int | None,
) -> str:
    if content_type == "table":
        return "supporting_table"
    if content_type == "figure_caption":
        return "figure_block"
    combined = f"{section_path}\n{text}".lower()
    canonical = section_path.lower()
    if extract_question_id(section_path):
        if re.search(r"recommendation|推荐意见", combined):
            return "recommendation_block"
        return "question_answer_block"
    if (
        re.search(r"results|结果", canonical)
        and re.search(r"abstract|摘要", canonical)
        and page_start == 1
    ):
        return "abstract_result"
    if re.search(r"recommendation|推荐意见", combined):
        return "recommendation_block"
    if re.search(r"eligibility|inclusion|exclusion|纳入|排除", combined):
        return "eligibility_criteria"
    if re.search(r"intervention|received|assigned|placebo|随机|治疗", combined):
        if re.search(r"placebo|control|对照", combined):
            return "comparator_arm"
        return "intervention_arm"
    if re.search(r"primary outcome|primary endpoint|主要结局|主要终点", canonical):
        if re.search(r"\d|p\s*[<=>]|95% ci|difference|improved|增加|下降", combined, re.I):
            return "primary_endpoint_result"
        return "primary_endpoint_definition"
    if re.search(r"secondary outcome|secondary endpoint|次要结局|次要终点", canonical):
        if re.search(r"\d|p\s*[<=>]|95% ci|difference|improved|增加|下降", combined, re.I):
            return "secondary_endpoint_result"
        return "secondary_endpoint_definition"
    if re.search(r"adverse|safety|harms?|不良|安全", canonical):
        return "adverse_event_result"
    if re.search(r"subgroup analysis", canonical):
        return "subgroup_result"
    if re.search(r"sensitivity analysis", canonical):
        return "sensitivity_result"
    if document_type == "guideline_consensus" and re.search(
        r"evidence grade|推荐级别|证据等级",
        combined,
    ):
        return "recommendation_block"
    return "general_text"


def has_medical_scope_hint(text: str) -> bool:
    lowered = text.lower()
    return any(hint.lower() in lowered for hint in MEDICAL_SCOPE_HINTS)


def extract_table_headers(markdown: str) -> list[str]:
    lines = [line.strip() for line in markdown.splitlines() if line.strip()]
    header_line = next((line for line in lines if "|" in line), None)
    if not header_line:
        return []
    parts = [cell.strip() for cell in header_line.strip("|").split("|")]
    return [part for part in parts if part and not set(part) <= {"-", ":"}]
