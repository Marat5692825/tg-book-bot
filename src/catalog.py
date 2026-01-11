import json
from pathlib import Path
from typing import Any

CATALOG_PATH = Path(__file__).resolve().parent.parent / "data" / "catalog.json"

def load_catalog() -> dict[str, Any]:
    if not CATALOG_PATH.exists():
        CATALOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        CATALOG_PATH.write_text('{"categories":[]}', encoding="utf-8")
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))

def save_catalog(catalog: dict[str, Any]) -> None:
    CATALOG_PATH.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")

def get_categories(catalog: dict[str, Any]) -> list[dict]:
    return catalog.get("categories", [])

def get_category(catalog: dict[str, Any], cat_id: str) -> dict | None:
    return next((c for c in get_categories(catalog) if c.get("id") == cat_id), None)

def get_book(catalog: dict[str, Any], book_id: str) -> dict | None:
    for c in get_categories(catalog):
        for b in c.get("books", []):
            if b.get("id") == book_id:
                return b
    return None

def search_books(catalog: dict[str, Any], query: str) -> list[dict]:
    q = query.lower().strip()
    if not q:
        return []
    results = []
    for c in get_categories(catalog):
        for b in c.get("books", []):
            title = (b.get("title") or "").lower()
            author = (b.get("author") or "").lower()
            if q in title or q in author:
                results.append({**b, "_category_title": c.get("title", "")})
    return results

def upsert_category(catalog: dict[str, Any], cat_id: str, title: str) -> None:
    cat = get_category(catalog, cat_id)
    if cat:
        cat["title"] = title
    else:
        catalog.setdefault("categories", []).append({"id": cat_id, "title": title, "books": []})

def add_book_to_category(catalog: dict[str, Any], cat_id: str, book: dict) -> None:
    cat = get_category(catalog, cat_id)
    if not cat:
        raise ValueError("Category not found")
    cat.setdefault("books", []).append(book)

def ensure_unique_book_id(catalog: dict[str, Any], base_id: str) -> str:
    if not get_book(catalog, base_id):
        return base_id
    n = 2
    while True:
        candidate = f"{base_id}-{n}"
        if not get_book(catalog, candidate):
            return candidate
        n += 1

def slugify(s: str) -> str:
    s = s.strip().lower()
    out = []
    prev_dash = False
    for ch in s:
        if ch.isalnum():
            out.append(ch)
            prev_dash = False
        elif ch in (" ", "_", ".", ",", "—", "–", ":", ";", "/", "\\"):
            if not prev_dash:
                out.append("-")
                prev_dash = True
        else:
            pass
    res = "".join(out).strip("-")
    return res if res else "book"
