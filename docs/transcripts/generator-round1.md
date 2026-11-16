# Generator Round 1 — Fixes and Edge Cases

## Summary of Changes

In response to the Critic's Round 1 review ([docs/transcripts/critic-round1.md](file:///Users/berfin/recipe-task-c/docs/transcripts/critic-round1.md)), the following changes were implemented:

### 1. Correctness & Logic Fixes ([main.py](file:///Users/berfin/recipe-task-c/main.py#L67-L135))
- **Percentages**: Added check to ignore ingredients with leading percentages (e.g., `"70% dark chocolate"`, `"2% milk"`), leaving them unchanged. Ingredients with leading quantities ahead of a percentage (e.g., `"2 cups 2% milk"`, `"100 g 70% dark chocolate"`) scale their leading quantity normally.
- **Ranges**: Added regex and logic to detect quantity ranges (e.g., `"1-2 tsp salt"`, `"1/2-1 tsp chili flakes"`, `"2 - 4 cloves garlic"`, `"1 to 2 bay leaves"`) and scale both bounds. Percentage ranges (e.g. `"70-80% dark chocolate"`) remain unscaled.
- **Fixed Precision Formatting**: Replaced `f"{val:f}"` (defaulting to 6 decimal places) in `_format_quantity` with `f"{val:.8f}".rstrip("0").rstrip(".")` to support full precision up to 8 decimal places without truncation.
- **Single Quantity Parser**: Factored out `_parse_quantity(q_str)` to cleanly support mixed fractions, simple fractions (with zero-denominator guard), and decimals/integers uniformly for both single quantities and ranges.

### 2. Critic Feedback Items Addressed ([test_main.py](file:///Users/berfin/recipe-task-c/test_main.py#L1-L404))
1. **Exact Value Assertions in 422 Errors**:
   Updated `test_scale_recipe_invalid_factor_non_numeric` to assert exact error structure (`type`, `loc`, `msg`, `input`) for non-numeric (`"two"`) and missing factor query parameters.
2. **Scaling Down (`factor < 1`)**:
   Added `test_scale_recipe_down_factor` asserting `GET /recipes/{id}/scaled?factor=0.5` correctly scales down quantities.
3. **Special Float Validation (`nan`, `inf`, `-inf`)**:
   Added `test_scale_recipe_invalid_factor_nan_and_inf` testing `factor=nan`, `factor=inf`, and `factor=-inf`, asserting exact 400 error payload (`{"detail": "factor must be a positive number"}`).
4. **Mixed Fractions Endpoint Test**:
   Added `test_scale_recipe_mixed_fractions_endpoint` verifying mixed fractions (e.g., `"1 1/2 cups flour"`, `"2 1/4 cups milk"`) scaled via the HTTP endpoint.
5. **Top-Level Import**:
   Moved `from main import scale_ingredient` to the top of `test_main.py`.
6. **Percentage Tests**:
   Added `test_scale_recipe_percentages_unchanged` testing `"70% dark chocolate"` and `"2% milk"` remain intact while `"4 cups 2% milk"` scales.
7. **Range Tests**:
   Added `test_scale_recipe_ranges_scale_both_bounds` verifying scaling of both bounds for ranges with hyphens, spaces, and `"to"`.
8. **Leading Decimals & Zero Denominator**:
   Added `test_scale_recipe_leading_decimal_and_zero_denominator` testing `".5 tsp salt"` and `"1/0 tsp cinnamon"`.

## Verification
Ran test suite:
```bash
~/recipe-box-week7/.venv/bin/python -m pytest -q
```
Result: `25 passed, 1 warning in 0.17s`.

No commits were created, and the server was not started.
