"""Recipe Box — starter app for Week 7.

A tiny FastAPI service for recipes and tags, with a static frontend. Use it as the
playground for concurrent multi-agent work and a generator-critic loop.

Run:
    pip install -r requirements.txt
    uvicorn main:app --reload
    # open http://localhost:8000/
Test:
    pytest
"""
import json
import math
from contextlib import closing
from fractions import Fraction
from pathlib import Path
import re
import sqlite3
import unicodedata

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel

BASE = Path(__file__).parent
DB_PATH = BASE / "recipes.db"

app = FastAPI(title="Recipe Box")


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with closing(get_db()) as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS recipes (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                title       TEXT NOT NULL,
                ingredients TEXT NOT NULL,  -- JSON list of strings
                tags        TEXT NOT NULL   -- JSON list of strings
            )"""
        )
        conn.commit()


init_db()


class RecipeIn(BaseModel):
    title: str
    ingredients: list[str] = []
    tags: list[str] = []


def _row_to_recipe(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "title": row["title"],
        "ingredients": json.loads(row["ingredients"]),
        "tags": json.loads(row["tags"]),
    }


def _format_quantity(val: float) -> str:
    """Format a numeric quantity without float noise and without trailing '.0' for integers."""
    if math.isinf(val) or math.isnan(val):
        raise OverflowError("scaled quantity overflow")
    if val == 0:
        return "0"
    rounded = round(val, 8)
    if rounded > 0:
        if rounded == int(rounded):
            return str(int(rounded))
        return f"{rounded:.8f}".rstrip("0").rstrip(".")
    return f"{val:.8g}"


def _normalize_fractions(text: str) -> str:
    """Normalize Unicode fraction slash and vulgar fraction characters to ASCII fractions."""
    text = text.replace("\u2044", "/")
    result = []
    for i, ch in enumerate(text):
        if unicodedata.category(ch) == "No":
            try:
                val = unicodedata.numeric(ch)
                frac = Fraction(val).limit_denominator(100)
                prev = text[i - 1] if i > 0 else ""
                prefix = " " if prev.isdigit() else ""
                result.append(f"{prefix}{frac.numerator}/{frac.denominator}")
                continue
            except (ValueError, TypeError):
                pass
        result.append(ch)
    return "".join(result)


_DASH_CHARS = "-–—−"
_DASH_CLASS = f"[{_DASH_CHARS}]"
_MIXED_PATTERN = r"\d+(?:\s+|" + _DASH_CLASS + r")\d+\s*/\s*\d+"
_FRAC_PATTERN = r"\d+\s*/\s*\d+"
_DEC_PATTERN = r"\d+(?:\.\d+)?|\.\d+"
_QTY_PATTERN = f"(?:{_MIXED_PATTERN}|{_FRAC_PATTERN}|{_DEC_PATTERN})"


def _parse_quantity(q_str: str) -> float | None:
    """Parse a quantity string (mixed fraction, simple fraction, or decimal/int) into a float."""
    q_str = q_str.strip()
    mixed = re.match(r"^(\d+)(?:\s+|" + _DASH_CLASS + r")(\d+)\s*/\s*(\d+)$", q_str)
    if mixed:
        whole, num, denom = int(mixed.group(1)), int(mixed.group(2)), int(mixed.group(3))
        return (whole + num / denom) if denom != 0 else None
    frac = re.match(r"^(\d+)\s*/\s*(\d+)$", q_str)
    if frac:
        num, denom = int(frac.group(1)), int(frac.group(2))
        return (num / denom) if denom != 0 else None
    dec = re.match(r"^(\d+(?:\.\d+)?|\.\d+)$", q_str)
    if dec:
        return float(dec.group(1))
    return None


def scale_ingredient(ingredient: str, factor: float) -> str:
    """Scale the leading quantity in an ingredient string by a numeric factor.

    Supports integers (e.g. '200 g flour'), decimals (e.g. '1.5 cups milk'),
    simple fractions (e.g. '1/2 tsp salt'), mixed fractions (e.g. '1 1/2 cups flour',
    '1-1/2 cups flour', '1½ cups flour'), and quantity ranges (e.g. '1-2 tsp salt',
    '1–2 tsp salt'). Percentages (e.g. '70% dark chocolate'), ordinals (e.g.
    '1st batch of dough'), and ingredients without leading numbers (e.g.
    'salt to taste') remain unchanged.
    """
    # Ordinals: e.g. 1st batch, 2nd layer
    if re.match(r"^\s*\d+(?:st|nd|rd|th)\b", ingredient, re.IGNORECASE):
        return ingredient

    # Normalize unicode fraction slash and vulgar fractions
    normalized = _normalize_fractions(ingredient)

    # Check for percentage at start: e.g. '70% dark chocolate', '2% milk'
    if re.match(r"^\s*" + _QTY_PATTERN + r"\s*%", normalized):
        return ingredient

    # Check for range: e.g. '1-2 tsp salt', '1/2-1 tsp salt', '1 to 2 pinches', '1–2 tsp'
    range_match = re.match(
        r"^(\s*)(" + _QTY_PATTERN + r")(\s*" + _DASH_CLASS + r"\s*|\s+to\s+)(" + _QTY_PATTERN + r")(.*)$",
        normalized,
    )
    if range_match:
        leading_ws, q1_str, sep, q2_str, rest = range_match.groups()
        # Avoid treating hyphenated mixed fractions (e.g. 1-1/2) as ranges
        is_hyphenated_mixed = (
            sep.strip() in _DASH_CHARS
            and re.match(r"^\d+$", q1_str.strip())
            and ("/" in q2_str)
        )
        if not is_hyphenated_mixed:
            if rest.lstrip().startswith("%"):
                return ingredient
            val1 = _parse_quantity(q1_str)
            val2 = _parse_quantity(q2_str)
            if val1 is not None and val2 is not None:
                scaled1 = _format_quantity(val1 * factor)
                scaled2 = _format_quantity(val2 * factor)
                return f"{leading_ws}{scaled1}{sep}{scaled2}{rest}"

    # Single quantity: mixed fraction, simple fraction, or decimal/int
    single_match = re.match(r"^(\s*)(" + _QTY_PATTERN + r")(.*)$", normalized)
    if single_match:
        leading_ws, q_str, rest = single_match.groups()
        val = _parse_quantity(q_str)
        if val is not None:
            scaled = _format_quantity(val * factor)
            return f"{leading_ws}{scaled}{rest}"

    return ingredient


@app.get("/")
def index():
    return FileResponse(BASE / "static" / "index.html")


@app.post("/recipes")
def create_recipe(recipe: RecipeIn):
    with closing(get_db()) as conn:
        cur = conn.execute(
            "INSERT INTO recipes (title, ingredients, tags) VALUES (?, ?, ?)",
            (recipe.title, json.dumps(recipe.ingredients), json.dumps(recipe.tags)),
        )
        conn.commit()
        rid = cur.lastrowid
    return {"id": rid, **recipe.model_dump()}


@app.get("/recipes")
def list_recipes(tag: str | None = None):
    with closing(get_db()) as conn:
        rows = conn.execute("SELECT * FROM recipes ORDER BY id").fetchall()
    recipes = [_row_to_recipe(r) for r in rows]
    if tag is not None:
        recipes = [r for r in recipes if tag in r["tags"]]
    return recipes


@app.get("/recipes/{recipe_id}")
def get_recipe(recipe_id: int):
    with closing(get_db()) as conn:
        row = conn.execute("SELECT * FROM recipes WHERE id = ?", (recipe_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="unknown recipe")
    return _row_to_recipe(row)


@app.get("/recipes/{recipe_id}/scaled")
def get_scaled_recipe(recipe_id: int, factor: float):
    """Return a recipe with ingredient quantities scaled by the given factor."""
    if math.isnan(factor) or math.isinf(factor) or factor <= 0:
        raise HTTPException(status_code=400, detail="factor must be a positive number")
    with closing(get_db()) as conn:
        row = conn.execute("SELECT * FROM recipes WHERE id = ?", (recipe_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="unknown recipe")
    recipe = _row_to_recipe(row)
    try:
        recipe["ingredients"] = [scale_ingredient(item, factor) for item in recipe["ingredients"]]
    except (OverflowError, ValueError):
        raise HTTPException(status_code=400, detail="factor causes numeric overflow")
    return recipe


@app.get("/shopping-list")
def get_shopping_list(request: Request = None, ids: str = "") -> list[str]:
    raw_list = request.query_params.getlist("ids") if request is not None else []
    if not raw_list and ids:
        raw_list = [ids]

    recipe_ids: list[int] = []
    for item in raw_list:
        for part in item.split(","):
            part = part.strip()
            if part.isdigit():
                recipe_ids.append(int(part))

    if not recipe_ids:
        return []

    placeholders = ",".join("?" for _ in recipe_ids)
    with closing(get_db()) as conn:
        rows = conn.execute(
            f"SELECT id, ingredients FROM recipes WHERE id IN ({placeholders})",
            recipe_ids,
        ).fetchall()

    recipe_map = {row["id"]: json.loads(row["ingredients"]) for row in rows}

    merged: list[str] = []
    seen: set[str] = set()
    for rid in recipe_ids:
        if rid in recipe_map:
            for ingredient in recipe_map[rid]:
                if ingredient not in seen:
                    seen.add(ingredient)
                    merged.append(ingredient)

    return merged

