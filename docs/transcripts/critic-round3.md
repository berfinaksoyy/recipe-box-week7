# Critic review — Task 3: Ingredient scaling

## 1. Correctness: FAIL

- **Server crash (HTTP 500) on large factor overflow**:
  - In [main.py](file:///Users/berfin/recipe-task-c/main.py#L173-L176), `get_scaled_recipe` validates `factor`:
    ```python
    if math.isnan(factor) or math.isinf(factor) or factor <= 0:
        raise HTTPException(status_code=400, detail="factor must be a positive number")
    ```
    A large finite float such as `factor=1e308` is valid float input and passes line 175. However, scaling an ingredient like `"200 g flour"` in [main.py](file:///Users/berfin/recipe-task-c/main.py#L130) computes `val * factor = 200.0 * 1e308`, which overflows float representation to `float('inf')`.
  - In `_format_quantity` at [main.py](file:///Users/berfin/recipe-task-c/main.py#L69-L70):
    ```python
    val = round(val, 8)
    if val == int(val):
    ```
    Calling `int(float('inf'))` raises `OverflowError: cannot convert float infinity to integer`. This unhandled exception crashes the endpoint and returns an undocumented HTTP 500 Internal Server Error instead of HTTP 400.

- **Quantities collapse to zero on very small factors**:
  - In [main.py](file:///Users/berfin/recipe-task-c/main.py#L69-L72), `_format_quantity` rounds `val` to 8 decimal places: `val = round(val, 8)`.
  - For small positive factors such as `factor=1e-9`, scaling `"1 cup flour"` results in `val * factor = 1e-9`. Rounding to 8 decimal places yields `0.0`.
  - Lines 70–71 then evaluate `0.0 == int(0.0)` as `True` and return `"0"`, converting `"1 cup flour"` to `"0 cup flour"`. A positive scaling factor should not wipe out ingredient amounts to zero.

- **Corrupted range scaling with Unicode en dashes (`–`), em dashes (`—`), or minus signs (`−`)**:
  - In [main.py](file:///Users/berfin/recipe-task-c/main.py#L109-L112), `range_match` only checks for ASCII hyphens:
    ```python
    range_match = re.match(
        r"^(\s*)(" + _QTY_PATTERN + r")(\s*-\s*|\s+to\s+)(" + _QTY_PATTERN + r")(.*)$",
        ingredient,
    )
    ```
  - Standard recipe ranges written with an en dash `–` (`\u2013`), em dash `—` (`\u2014`), or minus sign `−` (`\u2212`) such as `"1–2 tsp salt"` or `"10–20 g sugar"` fail `range_match`.
  - The string falls through to `single_match` at [main.py](file:///Users/berfin/recipe-task-c/main.py#L125-L131), matching only `"1"` and treating `"–2 tsp salt"` as the trailing unit text.
  - Scaling `"1–2 tsp salt"` by factor 2 produces `"2–2 tsp salt"`, and `"10–20 g sugar"` becomes `"20–20 g sugar"`. The upper bound remains unscaled.

- **Failure to scale Unicode fraction symbols (`½`, `⅓`, `¼`, `¾`, etc.) and fraction slashes (`⁄`)**:
  - In [main.py](file:///Users/berfin/recipe-task-c/main.py#L75), `_QTY_PATTERN` relies on `\d`, which in Python `re` only matches Unicode category "Nd" (decimal digits). Unicode vulgar fractions like `½` (`\u00bd`) belong to category "No" (numeric other) and are not matched.
  - Standalone fractions such as `"½ tsp salt"` fail regex matching at [main.py](file:///Users/berfin/recipe-task-c/main.py#L125) and are returned completely unscaled (`"½ tsp salt"` with factor 2).
  - Mixed fractions such as `"1½ cups flour"` match only the leading digit `"1"` in `single_match` at [main.py](file:///Users/berfin/recipe-task-c/main.py#L125-L131), leaving `"½ cups flour"` in `rest`. Scaling by 2 yields `"2½ cups flour"` instead of `"3 cups flour"`.
  - Fractions using the Unicode fraction slash `⁄` (`\u2044`), such as `"1⁄2 tsp salt"`, are parsed as integer `1` followed by `"⁄2 tsp salt"`, scaling with factor 2 to `"2⁄2 tsp salt"`.

- **Hyphenated mixed fractions misidentified as ranges**:
  - Recipes frequently format mixed numbers with a hyphen, e.g. `"1-1/2 cups flour"`.
  - At [main.py](file:///Users/berfin/recipe-task-c/main.py#L109-L122), `range_match` parses `"1-1/2"` as a range from `1` to `1/2`.
  - Scaling `"1-1/2 cups flour"` by 2 produces `"2-1 cups flour"` instead of `"3 cups flour"`.

- **Ordinals without space before unit misinterpreted as quantities**:
  - At [main.py](file:///Users/berfin/recipe-task-c/main.py#L75) and [main.py](file:///Users/berfin/recipe-task-c/main.py#L125), `_QTY_PATTERN` followed by text without a space matches ordinals like `"1st batch of dough"` or `"2nd layer of cheese"`.
  - Scaling `"1st batch of dough"` by 2 produces `"2st batch of dough"`.

---

## 2. Tests: FAIL

- In [test_main.py](file:///Users/berfin/recipe-task-c/test_main.py#L135-L404), there are no tests for:
  - Very large factors or float overflow cases (e.g. `factor=1e308`), missing the HTTP 500 crash in `_format_quantity`.
  - Very small factors (e.g. `factor=1e-9`), missing the zero-collapse issue.
  - Ranges with Unicode en dashes (`–`), em dashes (`—`), or minus signs (`−`).
  - Unicode vulgar fractions (`½`, `¼`, `¾`, `1½`) and Unicode fraction slashes (`⁄`).
  - Hyphenated mixed fractions (`1-1/2 cups flour`).

---

## 3. Clarity: PASS

- [main.py](file:///Users/berfin/recipe-task-c/main.py#L67-L134) isolates quantity parsing, formatting, and ingredient scaling into small, dedicated helpers (`_format_quantity`, `_parse_quantity`, `scale_ingredient`) with docstrings.
- No unused imports or dead code are present.

---

VERDICT: REVISE
1. Guard `get_scaled_recipe` and `_format_quantity` in [main.py](file:///Users/berfin/recipe-task-c/main.py#L70) against float overflow and infinities (`val * factor >= float('inf')`), raising HTTP 400 when the scaled result overflows rather than crashing with an unhandled 500 `OverflowError`.
2. Handle very small scaling factors in [main.py](file:///Users/berfin/recipe-task-c/main.py#L69-L72) so that positive quantities do not round down to `"0"`.
3. Expand range parsing in [main.py](file:///Users/berfin/recipe-task-c/main.py#L110) to support Unicode en dashes (`–`, `\u2013`), em dashes (`—`, `\u2014`), and minus signs (`−`, `\u2212`).
4. Normalize or support Unicode vulgar fractions (`½`, `⅓`, `¼`, etc.) and fraction slash (`⁄`) in [main.py](file:///Users/berfin/recipe-task-c/main.py#L75-L92) before scaling, ensuring both standalone (`½ tsp`) and mixed (`1½ cups`) fractions scale accurately.
5. Distinguish hyphenated mixed numbers (e.g. `"1-1/2 cups"`) from ranges in [main.py](file:///Users/berfin/recipe-task-c/main.py#L109-L113) so they scale as mixed numbers rather than ranges.
6. Guard quantity parsing against ordinal suffixes (`st`, `nd`, `rd`, `th`) when quantities lack spaces before following letters.
7. Add automated tests in [test_main.py](file:///Users/berfin/recipe-task-c/test_main.py) covering large overflow factors, small factors, Unicode dashes, Unicode fraction characters, and hyphenated mixed fractions.
