import json
import re
from functools import lru_cache
from pathlib import Path

DATA_DIR = Path(__file__).parent

PRODUCTS_FILE = DATA_DIR / "Products.json"
NUTRIENTS_FILE = DATA_DIR / "Nutrient and Functional Ingredient Data.json"
RECOGNIZED_FILE = DATA_DIR / "Individually_Recognized_Ingredient_list.json"
MARKET_PRODUCTS_FILE = DATA_DIR / "Market_Products.json"

BASE_PRODUCT_NAME = "뉴트리시파이 데일리 베이스"

NEGATION_TOKENS = (
    "괜찮", "없", "아니", "없어요", "안 ", "안그", "않", "제외",
    "멀쩡", "양호", "정상", "문제없", "이상없",
)

# Phrases that look negated but actually signal a present symptom
# ("안 좋다" = not good = problem exists). When any of these is in the clause
# the negation check is overridden and the need is kept.
SYMPTOM_OVERRIDES = (
    "안 좋", "좋지 않", "별로", "심해", "심함", "아파", "아픔",
    "걱정", "고민", "불편",
)

NEED_KEYWORDS: dict[str, list[str]] = {
    "피로 개선": ["피로", "피곤", "지침", "무기력", "기력"],
    "눈 건강": ["눈", "시력", "시야", "건조", "침침", "뻑뻑"],
    "관절 건강": ["관절", "무릎", "연골", "계단", "삐걱"],
    "뼈 건강": ["뼈", "골다공", "골밀도"],
    "장 건강": ["변비", "배변", "설사", "유산균", "속이", "더부룩"],
    "혈행 개선": ["혈행", "혈액", "혈압", "혈관", "콜레스테롤"],
    "기억력 개선": ["기억", "집중", "뇌", "인지", "건망"],
    "피부 건강": ["피부", "주름", "탄력", "보습", "미백"],
    "면역력 증진": ["면역", "감기", "잔병", "환절기"],
    "항산화": ["항산화", "노화", "유해산소", "스트레스"],
}

CLAIM_KEYWORDS: dict[str, list[str]] = {
    "피로 개선": ["피로", "에너지"],
    "눈 건강": ["시각", "눈", "시력"],
    "관절 건강": ["관절", "연골"],
    "뼈 건강": ["뼈", "골"],
    "장 건강": ["장", "배변", "유해균", "유익균"],
    "혈행 개선": ["혈행", "혈액", "혈중", "콜레스테롤", "혈압"],
    "기억력 개선": ["기억", "인지"],
    "피부 건강": ["피부"],
    "면역력 증진": ["면역"],
    "항산화": ["항산화", "유해산소"],
}


@lru_cache(maxsize=1)
def load_products() -> list[dict]:
    with open(PRODUCTS_FILE, encoding="utf-8") as f:
        return json.load(f).get("자사_제품", [])


@lru_cache(maxsize=1)
def load_services() -> list[dict]:
    """Dispenser / membership / other non-supplement offerings.

    Kept separate from 자사_제품 so they never leak into recommend_for_need().
    """
    with open(PRODUCTS_FILE, encoding="utf-8") as f:
        return json.load(f).get("서비스_상품", [])


def get_service(slug: str) -> dict | None:
    for s in load_services():
        if s.get("상세_slug") == slug:
            return s
    return None


@lru_cache(maxsize=1)
def load_nutrients() -> list[dict]:
    with open(NUTRIENTS_FILE, encoding="utf-8") as f:
        return json.load(f).get("nutrients", [])


@lru_cache(maxsize=1)
def load_recognized() -> list[dict]:
    with open(RECOGNIZED_FILE, encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def load_market_products() -> list[dict]:
    if not MARKET_PRODUCTS_FILE.exists():
        return []
    with open(MARKET_PRODUCTS_FILE, encoding="utf-8") as f:
        return json.load(f).get("시장_제품", [])


_CLAUSE_SPLIT_RE = re.compile(
    r"(?:,|\.|!|\?|는데\s|은데\s|ㄴ데\s|지만\s|고\s|이고\s|이며\s|며\s|그리고\s|그런데\s)"
)


def _split_clauses(text: str) -> list[str]:
    parts = [c.strip() for c in _CLAUSE_SPLIT_RE.split(text) if c and c.strip()]
    return parts or [text]


def _is_negated_clause(clause: str) -> bool:
    if any(tok in clause for tok in SYMPTOM_OVERRIDES):
        return False
    return any(tok in clause for tok in NEGATION_TOKENS)


def detect_needs(text: str) -> list[str]:
    """Detect needs per clause, dropping ones in a negated clause.

    "피로는 괜찮은데 눈이 침침해요" splits into ["피로는 괜찮은데", "눈이 침침해요"];
    the first clause has 괜찮 (negation) so 피로 is dropped; the second is positive.
    """
    clauses = _split_clauses(text)
    needs: list[str] = []
    for need, kws in NEED_KEYWORDS.items():
        positive_hit = False
        for clause in clauses:
            if not any(k in clause for k in kws):
                continue
            if _is_negated_clause(clause):
                continue
            positive_hit = True
            break
        if positive_hit:
            needs.append(need)
    return needs


def find_market_competitors(needs: list[str]) -> list[dict]:
    """Return market products whose 기능성_요약 overlaps with the user's needs."""
    if not needs:
        return []
    need_set = set(needs)
    hits: list[dict] = []
    for mp in load_market_products():
        if need_set & set(mp.get("기능성_요약", [])):
            hits.append(mp)
    return hits


def find_functional_ingredients_for_need(need: str) -> list[dict]:
    """Return 건기식 고시 기능성 원료 whose claim text mentions the need's keywords.

    Pulls from both the general nutrient database and the individually-recognized list,
    unified into a single shape: {name, source, claim, daily_intake, precautions}.
    """
    claim_kws = CLAIM_KEYWORDS.get(need, [])
    if not claim_kws:
        return []

    results: list[dict] = []

    for item in load_nutrients():
        text = " ".join(item.get("functions", []))
        if any(k in text for k in claim_kws):
            results.append(
                {
                    "name": item.get("name", ""),
                    "source": "nutrient",
                    "claim": "; ".join(item.get("functions", [])),
                    "daily_intake": item.get("daily_intake"),
                    "precautions": item.get("precautions", []),
                }
            )

    for item in load_recognized():
        text = item.get("PRIMARY_FNCLTY", "")
        if any(k in text for k in claim_kws):
            results.append(
                {
                    "name": item.get("RAWMTRL_NM", ""),
                    "source": "recognized",
                    "claim": text,
                    "daily_intake": f"{item.get('DAY_INTK_LOWLIMIT', '')} ~ {item.get('DAY_INTK_HIGHLIMIT', '')}",
                    "precautions": (
                        [item.get("IFTKN_ATNT_MATR_CN", "")]
                        if item.get("IFTKN_ATNT_MATR_CN")
                        else []
                    ),
                }
            )

    return results


def _normalize_ingredient_name(name: str) -> str:
    """Strip parenthetical qualifiers and whitespace for loose matching."""
    base = name
    for ch in ["(", "（"]:
        if ch in base:
            base = base.split(ch, 1)[0]
    return base.strip()


def match_company_ingredients(
    functional_ingredients: list[dict], products: list[dict]
) -> list[dict]:
    """Intersect 건기식 고시 원료 with 자사 제품의 주요_원료.

    Returns the subset of functional ingredients that also appear in at least one
    company product, annotated with which products contain them.
    """
    product_map: dict[str, list[str]] = {}
    for p in products:
        for ing in p.get("주요_원료", []):
            ing_name = _normalize_ingredient_name(ing.get("이름", ""))
            if ing_name:
                product_map.setdefault(ing_name, []).append(p["제품명"])

    matched: list[dict] = []
    seen_names: set[str] = set()
    for fi in functional_ingredients:
        fi_name = _normalize_ingredient_name(fi.get("name", ""))
        if not fi_name or fi_name in seen_names:
            continue
        for ing_name, product_names in product_map.items():
            if fi_name in ing_name or ing_name in fi_name:
                seen_names.add(fi_name)
                matched.append({**fi, "company_products": sorted(set(product_names))})
                break

    return matched


def products_containing(ingredient_names: list[str], products: list[dict]) -> list[dict]:
    """Return products whose 주요_원료 includes any of the given ingredient names."""
    norm_targets = [_normalize_ingredient_name(n) for n in ingredient_names if n]
    hits: list[dict] = []
    for p in products:
        for ing in p.get("주요_원료", []):
            ing_name = _normalize_ingredient_name(ing.get("이름", ""))
            if any(t and (t in ing_name or ing_name in t) for t in norm_targets):
                hits.append(p)
                break
    return hits


def get_base_product(products: list[dict]) -> dict | None:
    for p in products:
        if p.get("제품명") == BASE_PRODUCT_NAME:
            return p
    return None


def recommend_for_need(
    user_text: str,
    products: list[dict],
    exclude_base: bool = True,
) -> dict:
    """Full pipeline: user text → detected needs → functional ingredients → 자사 원료 교집합 → 제품.

    Returns a dict with each pipeline step's output for prompt injection and UI display.
    """
    needs = detect_needs(user_text)

    functional: list[dict] = []
    for need in needs:
        functional.extend(find_functional_ingredients_for_need(need))

    company_ingredients = match_company_ingredients(functional, products)

    matched_names = [ci["name"] for ci in company_ingredients]
    recommended = products_containing(matched_names, products)

    if exclude_base:
        recommended = [p for p in recommended if p.get("제품명") != BASE_PRODUCT_NAME]

    seen = set()
    deduped = []
    for p in recommended:
        if p["제품명"] not in seen:
            seen.add(p["제품명"])
            deduped.append(p)

    def _need_fit_score(p: dict) -> int:
        return sum(1 for n in p.get("연관_니즈", []) if n in needs)

    deduped.sort(key=_need_fit_score, reverse=True)
    deduped = [p for p in deduped if _need_fit_score(p) > 0] or deduped

    diversified = _diversify_by_primary_need(deduped, needs)

    return {
        "needs": needs,
        "functional_ingredients": functional[:10],
        "company_ingredients": company_ingredients,
        "products": diversified,
        "market_competitors": find_market_competitors(needs),
    }


def _diversify_by_primary_need(
    products: list[dict], needs: list[str], per_need_cap: int = 1
) -> list[dict]:
    """Cap how many products per primary need slot can appear in the recommendation list.

    Each product's "primary need" is the first entry in 연관_니즈 that overlaps with
    the user's detected needs. This prevents a single need from dominating the
    recommendation list when several products share the same indication.
    """
    if not products or not needs:
        return products

    counts: dict[str, int] = {}
    kept: list[dict] = []
    overflow: list[dict] = []
    for p in products:
        primary = next(
            (n for n in p.get("연관_니즈", []) if n in needs), None
        )
        if primary is None:
            kept.append(p)
            continue
        if counts.get(primary, 0) < per_need_cap:
            counts[primary] = counts.get(primary, 0) + 1
            kept.append(p)
        else:
            overflow.append(p)
    return kept + overflow


def find_mentioned_ingredients(user_text: str, products: list[dict]) -> list[dict]:
    """Return ingredient safety info for any product ingredient named in the user's text."""
    seen: set[str] = set()
    results: list[dict] = []

    for p in products:
        for ing in p.get("주요_원료", []):
            name = ing.get("이름", "")
            if not name or name in seen:
                continue
            if name in user_text:
                seen.add(name)
                for n in load_nutrients():
                    if name in n.get("name", "") or n.get("name", "") in name:
                        results.append(
                            {
                                "name": n["name"],
                                "daily_intake": n.get("daily_intake"),
                                "precautions": n.get("precautions", []),
                            }
                        )
                        break
    return results
