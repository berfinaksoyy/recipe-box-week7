# Critic review — Task 3: Ingredient scaling (Round 4)

Review of the ingredient scaling implementation in [main.py](file:///Users/berfin/recipe-task-c/main.py) and test suite in [test_main.py](file:///Users/berfin/recipe-task-c/test_main.py) against [docs/RUBRIC.md](file:///Users/berfin/recipe-task-c/docs/RUBRIC.md) and findings from [docs/transcripts/critic-round3.md](file:///Users/berfin/recipe-task-c/docs/transcripts/critic-round3.md).

---

## Verification of Round 3 Findings

1. **Large factor overflow handling (`factor=1e308`)**:
   - **Status**: **FIXED**
   - **Verification**: [main.py#L71-L72](file:///Users/berfin/recipe-task-c/main.py#L71-L72) raises `OverflowError` on `inf`/`nan`. In [main.py#L229-L233](file:///Users/berfin/recipe-task-c/main.py#L229-L233), `get_scaled_recipe` catches `(OverflowError, ValueError)` and returns HTTP 400 with detail `"factor causes numeric overflow"`. Tested in [test_main.py#L412-L422](file:///Users/berfin/recipe-task-c/test_main.py#L412-L422).

2. **Quantities collapsing to zero on small factors (`factor=1e-9`)**:
   - **Status**: **FIXED**
   - **Verification**: [main.py#L75-L80](file:///Users/berfin/recipe-task-c/main.py#L75-L80) in `_format_quantity` formats non-zero positive quantities that round to zero via `f"{val:.8g}"`, preserving small numbers (`"1e-09 cup flour"`). Tested in [test_main.py#L424-L434](file:///Users/berfin/recipe-task-c/test_main.py#L424-L434).

3. **Unicode dashes (`–`, `—`, `−`) in quantity ranges**:
   - **Status**: **FIXED**
   - **Verification**: [main.py#L102-L103](file:///Users/berfin/recipe-task-c/main.py#L102-L103) defines `_DASH_CHARS = "-–—−"` and `_DASH_CLASS = f"[{_DASH_CHARS}]"`, utilized in `range_match` at [main.py#L150](file:///Users/berfin/recipe-task-c/main.py#L150). Tested in [test_main.py#L436-L449](file:///Users/berfin/recipe-task-c/test_main.py#L436-L449).

4. **Unicode vulgar fractions (`½`, `⅓`, `¼`, etc.) and fraction slash (`⁄`)**:
   - **Status**: **FIXED**
   - **Verification**: [main.py#L83-L99](file:///Users/berfin/recipe-task-c/main.py#L83-L99) replaces `\u2044` with `/` and normalizes vulgar fraction characters via `unicodedata.numeric`. Tested in [test_main.py#L451-L474](file:///Users/berfin/recipe-task-c/test_main.py#L451-L474). *(Note: introduces a new edge case on non-fraction numerals detailed below).*

5. **Hyphenated mixed fractions vs ranges**:
   - **Status**: **PARTIALLY FIXED / REGRESSION INTRODUCED**
   - **Verification**: While `"1-1/2 cups flour"` now scales to `"3 cups flour"` via [main.py#L156-L160](file:///Users/berfin/recipe-task-c/main.py#L156-L160) and is tested in [test_main.py#L476-L486](file:///Users/berfin/recipe-task-c/test_main.py#L476-L486), the heuristic used to detect hyphenated mixed fractions causes valid recipe ranges ending in fractions to fail scaling (detailed in Section 1 below).

6. **Ordinals (`1st batch`, `2nd layer`)**:
   - **Status**: **FIXED**
   - **Verification**: [main.py#L138-L139](file:///Users/berfin/recipe-task-c/main.py#L138-L139) guards with `re.match(r"^\s*\d+(?:st|nd|rd|th)\b", ingredient, re.IGNORECASE)`. Tested in [test_main.py#L488-L511](file:///Users/berfin/recipe-task-c/test_main.py#L488-L511).

7. **Automated tests in `test_main.py`**:
   - **Status**: **FIXED**
   - **Verification**: Tests for Round 3 issues were added in [test_main.py#L412-L511](file:///Users/berfin/recipe-task-c/test_main.py#L412-L511).

---

## 1. Correctness: FAIL

- **Upper bound in quantity ranges left unscaled when it contains a fraction (e.g. `"1 - 1 1/2 cups flour"`, `"1–1 1/2 cups flour"`, `"2 - 2 1/2 tsp"`, `"1 - 3/4 cup"`)**:
  - In [main.py#L149-L160](file:///Users/berfin/recipe-task-c/main.py#L149-L160):
    ```python
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
            ...
    ```
  - For standard ingredient ranges like `"1 - 1 1/2 cups flour"` or `"1–1 1/2 cups flour"`:
    - `q1_str = "1"` (matches `^\d+$`)
    - `sep = " - "` or `sep = "–"` (`sep.strip() in _DASH_CHARS` is `True`)
    - `q2_str = "1 1/2"` (`"/" in q2_str` is `True`)
  - Because `is_hyphenated_mixed` evaluates to `True`, the entire range scaling block at lines 161–169 is bypassed.
  - Execution falls through to `single_match` at [main.py#L172-L178](file:///Users/berfin/recipe-task-c/main.py#L172-L178), matching only the leading integer `"1"` and capturing `" - 1 1/2 cups flour"` in `rest`.
  - Scaling `"1 - 1 1/2 cups flour"` by 2 yields `"2 - 1 1/2 cups flour"` (and by 3 yields `"3 - 1 1/2 cups flour"`), leaving the upper bound completely unscaled.
  - A hyphenated mixed number (`"1-1/2"`) has **no whitespace** around the dash (`sep in _DASH_CHARS`), and its second part `q2_str` is strictly a simple fraction (`re.match(r"^\d+\s*/\s*\d+$", q2_str.strip())`), not a mixed fraction.

- **Superscript digits and integer numerals corrupted into fractions by `_normalize_fractions`**:
  - In [main.py#L88-L96](file:///Users/berfin/recipe-task-c/main.py#L88-L96):
    ```python
    for i, ch in enumerate(text):
        if unicodedata.category(ch) == "No":
            try:
                val = unicodedata.numeric(ch)
                frac = Fraction(val).limit_denominator(100)
                prev = text[i - 1] if i > 0 else ""
                prefix = " " if prev.isdigit() else ""
                result.append(f"{prefix}{frac.numerator}/{frac.denominator}")
                continue
    ```
  - Unicode category `"No"` includes non-fraction numerals such as superscripts (`²`, `³`, `¹`, `⁴`), subscripts (`₀`, `₁`), and circled numbers (`①`).
  - For a superscript such as `²` (`\u00b2`), `unicodedata.numeric('²')` returns `2.0`.
  - Line 91 computes `Fraction(2.0).limit_denominator(100) = Fraction(2, 1)`. Line 95 then appends `"2/1"`.
  - As a result, ingredients with unit exponents or note references such as `"100 g flour²"` or `"1 pinch salt¹"` are corrupted into `"100 g flour2/1"` and `"1 pinch salt1/1"`.
  - Normalization should only apply when `val % 1 != 0` (or `frac.denominator > 1`, or `"FRACTION"` is present in `unicodedata.name(ch)`).

---

## 2. Tests: FAIL

- In [test_main.py#L333-L358](file:///Users/berfin/recipe-task-c/test_main.py#L333-L358), `test_scale_recipe_ranges_scale_both_bounds` tests integer ranges (`"1-2 tsp"`, `"2 - 4 cloves"`), decimals, and simple fractions (`"1/2-1 tsp"`), but lacks tests for:
  - Ranges where one bound is a mixed fraction (e.g. `"1 - 1 1/2 cups flour"` or `"1 to 2 1/2 cups milk"`), which misses the upper-bound scaling failure.
  - Ranges with Unicode vulgar fractions (e.g. `"½ - 1 tsp salt"`).

---

## 3. Clarity: PASS

- [main.py#L69-L180](file:///Users/berfin/recipe-task-c/main.py#L69-L180) continues to maintain clean, small named helpers (`_format_quantity`, `_normalize_fractions`, `_parse_quantity`, `scale_ingredient`) with clear docstrings.
- No dead code or unused imports are present in [main.py](file:///Users/berfin/recipe-task-c/main.py#L13-L25) or [test_main.py](file:///Users/berfin/recipe-task-c/test_main.py#L1-L4).

---

VERDICT: REVISE
1. Fix range detection in [main.py#L156-L160](file:///Users/berfin/recipe-task-c/main.py#L156-L160): distinguish hyphenated mixed numbers from ranges by ensuring `sep` has no surrounding whitespace (`sep in _DASH_CHARS`) and `q2_str` matches a simple fraction (`^\d+\s*/\s*\d+$`), so ranges containing mixed numbers (e.g. `"1 - 1 1/2 cups flour"`, `"1–1 1/2 cups flour"`) scale both bounds accurately.
2. Restrict fraction normalization in [main.py#L88-L96](file:///Users/berfin/recipe-task-c/main.py#L88-L96) to actual fractional values (`val % 1 != 0` or `frac.denominator > 1`), preventing non-fraction numerals (such as superscripts `¹`, `²`, `³`) from being converted to fractions like `"2/1"`.
3. Add automated tests in [test_main.py](file:///Users/berfin/recipe-task-c/test_main.py) asserting exact scaled values for ranges with mixed fraction bounds (e.g. `"1 - 1 1/2 cups flour"` -> `"2 - 3 cups flour"`).
