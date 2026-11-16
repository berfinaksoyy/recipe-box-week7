# Round 2 Review: Task 3 Ingredient Scaling

Review of the ingredient scaling implementation in [main.py](file:///Users/berfin/recipe-task-c/main.py) and test suite in [test_main.py](file:///Users/berfin/recipe-task-c/test_main.py) against the criteria in [RUBRIC.md](file:///Users/berfin/recipe-task-c/docs/RUBRIC.md) and the findings from [critic-round1.md](file:///Users/berfin/recipe-task-c/docs/transcripts/critic-round1.md).

---

## Verification of Round 1 Findings

1. **Assert exact values in `test_scale_recipe_invalid_factor_non_numeric`**:
   - **Status**: **FIXED**
   - **Verification**: In [test_main.py#L240-L263](file:///Users/berfin/recipe-task-c/test_main.py#L240-L263), both non-numeric factor (`factor=two`) and missing factor requests now assert the exact response payload structure and error messages (`res_non_num.json() == ...` and `res_missing.json() == ...`) rather than asserting only HTTP status codes.

2. **Add endpoint test for scaling down (`factor < 1`)**:
   - **Status**: **FIXED**
   - **Verification**: Added `test_scale_recipe_down_factor` in [test_main.py#L266-L281](file:///Users/berfin/recipe-task-c/test_main.py#L266-L281), testing `GET /recipes/{id}/scaled?factor=0.5` and asserting exact values on scaled integer and fraction fields.

3. **Add tests for edge-case factor values (`nan`, `inf`, `-inf`)**:
   - **Status**: **FIXED**
   - **Verification**: Added `test_scale_recipe_invalid_factor_nan_and_inf` in [test_main.py#L283-L294](file:///Users/berfin/recipe-task-c/test_main.py#L283-L294), verifying that `"nan"`, `"inf"`, and `"-inf"` return HTTP 400 with `{"detail": "factor must be a positive number"}`.

4. **Add endpoint-level coverage for mixed fractions**:
   - **Status**: **FIXED**
   - **Verification**: Added `test_scale_recipe_mixed_fractions_endpoint` in [test_main.py#L296-L306](file:///Users/berfin/recipe-task-c/test_main.py#L296-L306), executing `GET /recipes/{id}/scaled?factor=2` on `"1 1/2 cups flour"` and `"2 1/4 cups milk"` and verifying exact scaled results `["3 cups flour", "4.5 cups milk"]`.

5. **Move local import of `scale_ingredient` to module level**:
   - **Status**: **FIXED**
   - **Verification**: `scale_ingredient` is now imported at top-level alongside `app` in [test_main.py#L3](file:///Users/berfin/recipe-task-c/test_main.py#L3).

6. **Additional edge-case improvements addressed**:
   - **Formatting precision**: [main.py#L67-L73](file:///Users/berfin/recipe-task-c/main.py#L67-L73) updated `_format_quantity` to use `round(val, 8)` and `f"{val:.8f}".rstrip("0").rstrip(".")`, preventing truncation or empty strings on small values.
   - **Percentage safety**: Leading percentages (e.g. `"70% dark chocolate"`, `"2% milk"`) are preserved unchanged via [main.py#L104-L106](file:///Users/berfin/recipe-task-c/main.py#L104-L106) and tested in [test_main.py#L308-L331](file:///Users/berfin/recipe-task-c/test_main.py#L308-L331).
   - **Quantity range scaling**: Quantity ranges (e.g. `"1-2 tsp salt"`, `"1 to 2 bay leaves"`) now scale both bounds via [main.py#L108-L122](file:///Users/berfin/recipe-task-c/main.py#L108-L122) and are tested in [test_main.py#L333-L358](file:///Users/berfin/recipe-task-c/test_main.py#L333-L358).
   - **Zero-denominator safety**: Handled in [main.py#L84](file:///Users/berfin/recipe-task-c/main.py#L84), [main.py#L88](file:///Users/berfin/recipe-task-c/main.py#L88) and tested in [test_main.py#L360-L370](file:///Users/berfin/recipe-task-c/test_main.py#L360-L370).
   - **Mutation safety test**: Stored recipe immutability verified through the API in [test_main.py#L378-L394](file:///Users/berfin/recipe-task-c/test_main.py#L378-L394).

---

## Rubric Assessment

### 1. Correctness — PASS

- **Leading quantities scaled**:
  - Integers (`"200 g flour"` -> `"400 g flour"`): [main.py#L125-L131](file:///Users/berfin/recipe-task-c/main.py#L125-L131) via regex `_QTY_PATTERN` [main.py#L75](file:///Users/berfin/recipe-task-c/main.py#L75).
  - Decimals (`"1.5 cups milk"` -> `"3 cups milk"` or `"4.5 cups milk"`): Handled via decimal branch in [main.py#L89-L91](file:///Users/berfin/recipe-task-c/main.py#L89-L91) and [main.py#L125-L131](file:///Users/berfin/recipe-task-c/main.py#L125-L131).
  - Simple fractions (`"1/2 tsp salt"` -> `"1 tsp salt"`): Handled via fraction branch in [main.py#L85-L88](file:///Users/berfin/recipe-task-c/main.py#L85-L88).
  - Mixed fractions (`"1 1/2 cups flour"` -> `"3 cups flour"`): Handled via mixed fraction branch in [main.py#L81-L84](file:///Users/berfin/recipe-task-c/main.py#L81-L84).
- **Ingredients without leading numbers**:
  - Ingredients such as `"salt to taste"` do not match the leading quantity pattern and return unchanged via fallback at [main.py#L133](file:///Users/berfin/recipe-task-c/main.py#L133).
- **Readable results (no float noise, no trailing `.0`)**:
  - `_format_quantity` in [main.py#L67-L73](file:///Users/berfin/recipe-task-c/main.py#L67-L73) rounds to 8 decimal places, converts whole values (`val == int(val)`) to integer strings (`"3"`, not `"3.0"`), and strips trailing zeros and periods from non-integers.
- **Factor validation**:
  - Positive check in [main.py#L175-L176](file:///Users/berfin/recipe-task-c/main.py#L175-L176) rejects `factor <= 0`, `math.isnan(factor)`, and `math.isinf(factor)` with HTTP 400 and detail `"factor must be a positive number"`.
  - Non-numeric or missing factors are handled by FastAPI validation returning HTTP 422 with clear error details.
- **Unknown recipe & immutability**:
  - Returns HTTP 404 with `{"detail": "unknown recipe"}` at [main.py#L179-L180](file:///Users/berfin/recipe-task-c/main.py#L179-L180).
  - The endpoint executes a read-only `SELECT` query ([main.py#L177-L178](file:///Users/berfin/recipe-task-c/main.py#L177-L178)) and constructs the response in memory without modifying the SQLite database.

---

### 2. Tests — PASS

- **Coverage of all correctness rules**:
  - Integers: [test_main.py#L135-L150](file:///Users/berfin/recipe-task-c/test_main.py#L135-L150)
  - Decimals: [test_main.py#L152-L168](file:///Users/berfin/recipe-task-c/test_main.py#L152-L168)
  - Simple fractions: [test_main.py#L170-L184](file:///Users/berfin/recipe-task-c/test_main.py#L170-L184)
  - Mixed fractions (endpoint): [test_main.py#L296-L306](file:///Users/berfin/recipe-task-c/test_main.py#L296-L306)
  - Ingredients without leading numbers: [test_main.py#L186-L196](file:///Users/berfin/recipe-task-c/test_main.py#L186-L196)
  - Float noise suppression & no `.0` on whole numbers: [test_main.py#L198-L214](file:///Users/berfin/recipe-task-c/test_main.py#L198-L214)
  - Factor zero and negative: [test_main.py#L216-L230](file:///Users/berfin/recipe-task-c/test_main.py#L216-L230)
  - Factor non-numeric and missing: [test_main.py#L232-L264](file:///Users/berfin/recipe-task-c/test_main.py#L232-L264)
  - Factor `nan`, `inf`, `-inf`: [test_main.py#L283-L294](file:///Users/berfin/recipe-task-c/test_main.py#L283-L294)
  - Scaling down (`factor < 1`): [test_main.py#L266-L281](file:///Users/berfin/recipe-task-c/test_main.py#L266-L281)
  - Unknown recipe (404): [test_main.py#L372-L376](file:///Users/berfin/recipe-task-c/test_main.py#L372-L376)
  - Original recipe immutability verification: [test_main.py#L378-L394](file:///Users/berfin/recipe-task-c/test_main.py#L378-L394)
- **Exact value assertions**:
  - Every scaling test asserts exact response contents (`res.json()`, `res.json()["ingredients"]`, or `res.json()["detail"]`) in addition to status codes.

---

### 3. Clarity — PASS

- **Small named helpers with docstrings**:
  - `_format_quantity`: [main.py#L67-L73](file:///Users/berfin/recipe-task-c/main.py#L67-L73)
  - `_parse_quantity`: [main.py#L78-L93](file:///Users/berfin/recipe-task-c/main.py#L78-L93)
  - `scale_ingredient`: [main.py#L95-L133](file:///Users/berfin/recipe-task-c/main.py#L95-L133)
  - `get_scaled_recipe`: [main.py#L172-L184](file:///Users/berfin/recipe-task-c/main.py#L172-L184)
- **Dead code and imports**:
  - No unused imports or dead code in [main.py#L13-L23](file:///Users/berfin/recipe-task-c/main.py#L13-L23) or [test_main.py#L1-L3](file:///Users/berfin/recipe-task-c/test_main.py#L1-L3).
  - Variable and function names clearly describe their purpose and contents.

---

VERDICT: APPROVE
