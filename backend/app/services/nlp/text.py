"""Text normalisation, tokenising, sentence splitting, entity/field extraction, rule-based classification."""
from __future__ import annotations
import re

STOP = set("""a an the and or but if of to in on at by for with from as is are was were be been being do does did can could
should would will may might must shall has have had it its this that these those there here what which who whom whose when
where why how i you we they he she them their our your my me us not no yes any some all each than then so such into about
over under per also tell please give say says said stated listed explicitly mentioned anywhere according included until many much between difference different versus vs""".split())

TOKEN = re.compile(r"\d[\d,]*(?:\.\d+)?%?|[a-z]+")
SUFFIXES = ("ations", "ation", "ments", "ment", "ions", "ion", "ings", "ing", "ies", "ied", "ness", "ly", "ed", "es", "s")


def tokens(text: str) -> list[str]:
    return [t.replace(",", "") for t in TOKEN.findall(text.lower())]


def stem(w: str) -> str:
    """Light stemmer: strip one common suffix, then keep the first 5 letters. Crude on purpose; it only has to
    make 'exclusions', 'excluded' and 'exclude' meet."""
    if not w[0].isalpha():
        return w
    for s in SUFFIXES:
        if w.endswith(s) and len(w) - len(s) >= (5 if s.startswith("ment") else 3):
            w = w[: -len(s)]
            break
    else:
        if w.endswith("e") and len(w) >= 3:
            w = w[:-1]
    return w[:5]


def content_terms(text: str) -> list[str]:
    return [stem(t) for t in tokens(text) if t not in STOP]


_PAGENUM = re.compile(r"^(page\s+)?\d{1,4}(\s*(of|/)\s*\d{1,4})?$", re.I)


def strip_repeated_lines(raw_pages: list[str]) -> list[str]:
    """Drop page numbers and headers/footers that repeat on most pages of a document."""
    n = len(raw_pages)
    counts: dict[str, int] = {}
    for p in raw_pages:
        for line in {l.strip() for l in p.splitlines() if l.strip()}:
            counts[line] = counts.get(line, 0) + 1
    repeated = {l for l, c in counts.items() if n >= 3 and c >= max(3, int(0.6 * n + 0.99)) and len(l) < 120}
    out = []
    for p in raw_pages:
        keep = [l for l in p.splitlines() if l.strip() not in repeated and not _PAGENUM.match(l.strip())]
        out.append("\n".join(keep))
    return out


def normalize(text: str) -> str:
    text = text.replace("\r", "\n").replace("\u00a0", " ").replace("\x00", "")
    text = re.sub(r"-\n(?=[a-z])", "", text)
    lines = [re.sub(r"[ \t]+", " ", l).strip() for l in text.split("\n")]
    out = []
    for i, l in enumerate(lines):
        if not l:
            out.append("")
            continue
        nxt = next((x for x in lines[i + 1:] if x), "")
        # short line with no closing punctuation followed by a capitalised line is a heading
        if len(l) <= 60 and l[-1] not in ".:;,!?" and nxt and (nxt[0].isupper() or nxt[0].isdigit()):
            l += "."
        out.append(l)
    joined = re.sub(r"(?<!\n)\n(?!\n)", " ", "\n".join(out))
    return re.sub(r"[ \t]+", " ", re.sub(r"\n{2,}", "\n\n", joined)).strip()


_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z$0-9\"“(])|\s+•\s+")


def split_sentences(text: str) -> list[str]:
    return [s.strip() for s in _SPLIT.split(text) if s and s.strip()]


# ---- entities and fields ------------------------------------------------------------------------------------------
ENTITY_PATTERNS = {
    "MONEY": r"\$\s?\d[\d,]*(?:\.\d+)?",
    "DURATION": r"\b\d+\s*(?:business\s+)?(?:days?|weeks?|months?|years?)\b",
    "PERCENT": r"\b\d+(?:\.\d+)?\s?%",
    "AGE": r"\baged?\s+\d+(?:\s*(?:to|-)\s*\d+)?|\b(?:up to|until)\s+age\s+\d+",
    "DATE": r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}(?:,\s*\d{4})?|\b\d{4}-\d{2}-\d{2}\b",
    "VISITS": r"\b\d+\s+(?:visits?|sessions?)\b",
}
_nlp = None


def extract_entities(text: str) -> list[dict]:
    global _nlp
    found = [{"label": l, "text": m.group(0), "method": "regex"}
             for l, pat in ENTITY_PATTERNS.items() for m in re.finditer(pat, text, re.I)]
    try:  # optional spaCy pass for people/orgs/places; silently skipped when the model is missing
        if _nlp is None:
            import spacy
            _nlp = spacy.load("en_core_web_sm")
        for e in _nlp(text[:50000]).ents:
            if e.label_ in {"ORG", "PERSON", "GPE"}:
                found.append({"label": e.label_, "text": e.text, "method": "spacy"})
    except Exception:
        pass
    return found


FIELD_RULES = [
    ("coverage_limit", r"(annual|lifetime|coverage).{0,40}limit|limit.{0,30}(per|each) (member|year)", ENTITY_PATTERNS["MONEY"]),
    ("deductible", r"deductible", ENTITY_PATTERNS["MONEY"]),
    ("out_of_pocket_max", r"out[- ]of[- ]pocket", ENTITY_PATTERNS["MONEY"]),
    ("copay", r"co-?pay", ENTITY_PATTERNS["MONEY"]),
    ("coinsurance", r"coinsurance", ENTITY_PATTERNS["PERCENT"]),
    ("waiting_period", r"waiting period", ENTITY_PATTERNS["DURATION"]),
    ("deadline", r"\bwithin\b|\bno later than\b|\bdeadline\b", ENTITY_PATTERNS["DURATION"]),
    ("visit_limit", r"\bvisits?\b|\bsessions?\b", ENTITY_PATTERNS["VISITS"]),
    ("eligibility", r"\beligible\b|\beligibility\b|\bmust (?:be|reside|have)\b|\baged?\b", ENTITY_PATTERNS["AGE"]),
    ("exclusion", r"\bexclu(?:de|ded|sion|sions)\b|\bnot covered\b|\bdoes not cover\b", None),
    ("prior_authorization", r"prior authori[sz]ation|pre-?authori[sz]ation", None),
    ("required_document", r"\bmust (?:include|submit|attach)\b|\brequired documents?\b|\bsubmit(?:ted)? with\b", None),
]


def extract_fields(sentences: list[tuple[str, int]]) -> list[dict]:
    """sentences: (text, page_no). Every field carries the sentence it came from; nothing is inferred."""
    out, seen = [], set()
    for text, page in sentences:
        for name, trigger, value_pat in FIELD_RULES:
            if not re.search(trigger, text, re.I):
                continue
            if value_pat:
                vals = re.findall(value_pat, text, re.I)
                if not vals:
                    continue
                value = ", ".join(dict.fromkeys(v.strip() for v in vals))
            else:
                value = text if len(text) <= 220 else text[:217] + "..."
            key = (name, value, page)
            if key not in seen:
                seen.add(key)
                out.append({"field": name, "value": value, "page_no": page, "evidence": text, "method": "rule"})
    return out


CLASS_KEYWORDS = {
    "insurance_policy": ["eligibility", "exclusion", "excluded", "policy", "enrollment", "renewal", "premium", "member", "deductible"],
    "benefits_guide": ["benefit", "benefits", "visits", "allowance", "wellness", "coinsurance", "copay", "limit", "waiting period"],
    "claims_guide": ["claim", "claims", "appeal", "submission", "submit", "deadline", "denial", "pre-authorization", "itemized"],
}


def classify(text: str) -> tuple[str, float]:
    """Keyword-density baseline. The score is the winning class's share of all keyword hits, not a probability."""
    low = text.lower()
    hits = {c: sum(low.count(k) for k in kws) for c, kws in CLASS_KEYWORDS.items()}
    total = sum(hits.values())
    if total < 5:
        return "unclassified", 0.0
    best = max(hits, key=hits.get)
    return best, round(hits[best] / total, 3)


_DEF = re.compile(r"\b([A-Z][A-Za-z\- ]{2,40}?)\s+(?:means|is defined as|refers to|is the)\s+([^.]{10,200})\.")


def extract_definitions(text: str) -> list[dict]:
    return [{"term": m.group(1).strip(), "definition": m.group(2).strip(), "evidence": m.group(0)} for m in _DEF.finditer(text)]
