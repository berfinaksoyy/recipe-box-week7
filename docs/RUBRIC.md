# Critic rubric — Task 3: Ingredient scaling

Task: `GET /recipes/{id}/scaled?factor=2` returns the recipe with ingredient quantities
scaled (ingredients look like "200 g flour").

Score each area **PASS** or **FAIL** and list concrete findings with file and line.

## 1. Correctness
- Leading quantities are scaled: integers ("200 g flour"), decimals ("1.5 cups milk"),
  simple fractions ("1/2 tsp salt").
- Ingredients without a leading number ("salt to taste") are returned unchanged.
- Results are readable: no float noise like `0.30000000000000004`; whole numbers have no `.0`.
- `factor` must be a positive number; 0, negative or non-numeric → 422 or 400 with a clear message.
- Unknown recipe → 404. The stored recipe is NOT modified.

## 2. Tests
- At least one test per correctness rule above, including failure cases.
- Tests assert exact values, not just status codes.

## 3. Clarity
- Parsing/scaling logic is in a small, named helper with a docstring.
- No dead code, no unused imports, names say what they hold.

## Output format (required)
End with exactly one of these lines:
`VERDICT: APPROVE` — only if every area is PASS.
`VERDICT: REVISE` — followed by a numbered list of what must change.
