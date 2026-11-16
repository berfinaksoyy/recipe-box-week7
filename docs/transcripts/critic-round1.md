# Review: Task 3 Ingredient Scaling

Review of the ingredient-scaling implementation and test suite against the criteria in [docs/RUBRIC.md](file:///Users/berfin/recipe-task-c/docs/RUBRIC.md).

---

## 1. Correctness — PASS

### Concrete Findings
- **Integer scaling**: Handled via `dec_match` regex in [main.py#L100-L105](file:///Users/berfin/recipe-task-c/main.py#L100-L105).
- **Decimal scaling**: Handled via `dec_match` regex (`\d+(?:\.\d+)?|\.\d+`) in [main.py#L100-L105](file:///Users/berfin/recipe-task-c/main.py#L100-L105).
- **Fraction scaling**: Simple fractions (`\d+\s*/\s*\d+`) and mixed fractions (`\d+\s+\d+\s*/\s*\d+`) are handled in [main.py#L82-L98](file:///Users/berfin/recipe-task-c/main.py#L82-L98).
- **Ingredients without leading quantities**: Fallthrough return at [main.py#L106](file:///Users/berfin/recipe-task-c/main.py#L106) preserves text like `"salt to taste"` unchanged.
- **Readable results / formatting**: `_format_quantity` in [main.py#L67-L73](file:///Users/berfin/recipe-task-c/main.py#L67-L73) rounds to 8 digits, converts integer values to `int` strings (avoiding `.0`), and trims trailing zeros and dots for decimals.
- **Factor validation**: [main.py#L148-L149](file:///Users/berfin/recipe-task-c/main.py#L148-L149) checks `math.isnan(factor) or math.isinf(factor) or factor <= 0`, raising `HTTPException(status_code=400, detail="factor must be a positive number")`. Non-numeric or missing factor parameters trigger FastAPI's query validator, returning HTTP 422.
- **Unknown recipe & mutation safety**: Returns 404 on missing recipe at [main.py#L152-L153](file:///Users/berfin/recipe-task-c/main.py#L152-L153). Scaling only executes a `SELECT` query ([main.py#L150-L151](file:///Users/berfin/recipe-task-c/main.py#L150-L151)) and scales ingredients in memory without mutating stored records.

### Edge Cases Identified in Code
- **Fixed-precision formatting limitation**: In [main.py#L72](file:///Users/berfin/recipe-task-c/main.py#L72), `f"{val:f}"` defaults to Python's 6 decimal places (`%.6f`). If an ingredient scales to a quantity with precision beyond 6 decimal places or below `0.0000005`, it gets truncated or stripped down to `""`.
- **Percentage ingredients**: [main.py#L100](file:///Users/berfin/recipe-task-c/main.py#L100) matches any leading digits; an ingredient such as `"70% dark chocolate"` would be scaled to `"140% dark chocolate"`.
- **Quantity ranges**: An ingredient such as `"1-2 tsp salt"` matches `dec_match` on `"1"`, resulting in `"2-2 tsp salt"` when doubled instead of scaling both bounds or preserving the range.

---

## 2. Tests — FAIL

### Concrete Findings
- **Rule Violation — Status codes without exact value assertion**:
  In [test_main.py#L232-L244](file:///Users/berfin/recipe-task-c/test_main.py#L232-L244) (`test_scale_recipe_invalid_factor_non_numeric`), lines 240 and 243 only assert the status code:
  ```python
  res_non_num = client.get(f"/recipes/{rid}/scaled?factor=two")
  assert res_non_num.status_code == 422

  res_missing = client.get(f"/recipes/{rid}/scaled")
  assert res_missing.status_code == 422
  ```
  This violates the rubric requirement: *"Tests assert exact values, not just status codes"* and does not verify the response payload or error message structure.

### Missing Test Cases & Uncovered Edge Cases
1. **No test for endpoint scaling down (`factor < 1`)**: All scaled endpoint tests ([test_main.py#L135-L214](file:///Users/berfin/recipe-task-c/test_main.py#L135-L214)) only test scaling up with `factor=2` or `factor=3`. There is no test calling `GET /recipes/{id}/scaled?factor=0.5`.
2. **No test for special float values (`nan`, `inf`, `-inf`)**: Although [main.py#L148](file:///Users/berfin/recipe-task-c/main.py#L148) explicitly checks `math.isnan(factor)` and `math.isinf(factor)`, there are no tests verifying `?factor=nan` or `?factor=inf`.
3. **Mixed fractions not tested via HTTP endpoint**: Mixed fractions like `"1 1/2 cups flour"` are tested only via unit function invocation in [test_main.py#L270-L278](file:///Users/berfin/recipe-task-c/test_main.py#L270-L278), not through the `GET /recipes/{id}/scaled` endpoint.
4. **Leading decimals without integer prefix (`.5`)**: Handled by regex `\.\d+` in [main.py#L100](file:///Users/berfin/recipe-task-c/main.py#L100), but only `"0.5 tsp vanilla"` is tested in [test_main.py#L155](file:///Users/berfin/recipe-task-c/test_main.py#L155).
5. **Zero-denominator fraction safety**: Guarded in [main.py#L86](file:///Users/berfin/recipe-task-c/main.py#L86) and [main.py#L95](file:///Users/berfin/recipe-task-c/main.py#L95) (`d == 0`), but never tested in [test_main.py](file:///Users/berfin/recipe-task-c/test_main.py).

---

## 3. Clarity — PASS

### Concrete Findings
- **Named helpers with docstrings**:
  - `_format_quantity` defined in [main.py#L67-L73](file:///Users/berfin/recipe-task-c/main.py#L67-L73) with a descriptive docstring.
  - `scale_ingredient` defined in [main.py#L75-L106](file:///Users/berfin/recipe-task-c/main.py#L75-L106) with a descriptive docstring.
- **Dead code & imports**: No unused imports or dead code in [main.py#L13-L22](file:///Users/berfin/recipe-task-c/main.py#L13-L22). Variable names (`mixed_match`, `frac_match`, `dec_match`, `leading_ws`, `whole`, `num`, `denom`, `rest`) clearly describe their contents.
- **Style note**: In [test_main.py#L271](file:///Users/berfin/recipe-task-c/test_main.py#L271), `from main import scale_ingredient` is imported inside the test function rather than at module top.

---

VERDICT: REVISE
1. Update `test_scale_recipe_invalid_factor_non_numeric` in [test_main.py#L232-L244](file:///Users/berfin/recipe-task-c/test_main.py#L232-L244) to assert exact response content (e.g. checking `res.json()["detail"]`), satisfying the rule that tests must assert exact values rather than only status codes.
2. Add a test for scaling down (`factor < 1`, e.g. `factor=0.5`) on the `GET /recipes/{id}/scaled` endpoint in [test_main.py](file:///Users/berfin/recipe-task-c/test_main.py).
3. Add tests for edge-case factor values (`factor=nan`, `factor=inf`) to verify the 400 validation error in [test_main.py](file:///Users/berfin/recipe-task-c/test_main.py).
4. Add endpoint-level test coverage for mixed fractions (e.g. `"1 1/2 cups flour"`) via `GET /recipes/{id}/scaled` in [test_main.py](file:///Users/berfin/recipe-task-c/test_main.py).
5. Move the local import `from main import scale_ingredient` in [test_main.py#L271](file:///Users/berfin/recipe-task-c/test_main.py#L271) to the top of [test_main.py](file:///Users/berfin/recipe-task-c/test_main.py).
