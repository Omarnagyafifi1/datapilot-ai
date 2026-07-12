# Plan 023: Fix Test Data Supplier ID Reference Range for Non-Default Scale

> **Executor instructions**: Follow step by step. Verify each command before moving on. Stop and report if STOP conditions trigger.
>
> **Drift check**: `git diff --stat 0d59108..HEAD -- scripts/generate_test_dataset.py`

## Status

- **Priority**: P1
- **Effort**: S
- **Risk**: LOW
- **Depends on**: none
- **Category**: bug (test data)
- **Planned at**: commit `0d59108`, 2026-07-12

## Why this matters

When the test dataset generator runs at any scale factor other than 1.0, the products table references supplier IDs that don't exist. `gen_suppliers` correctly produces `row_targets["suppliers"]` suppliers, but `gen_products` hardcodes `random.randint(1, 5000)`. At scale=0.1 (~500 suppliers), ~90% of products have invalid `supplier_id` values. Every LEFT JOIN returns NULL for supplier names — which is the exact "empty supplier_name" symptom the user reported.

## Current state

In `scripts/generate_test_dataset.py:350` — the `gen_products` generator uses a hardcoded upper bound:

```python
def gen_products(n=50000):
    for i in range(1, n + 1):
        yield (i, ..., random.randint(1, 300), random.randint(1, 5000), ...)
```

The 6th yielded value (index 5) is `category_id` with `randint(1, 300)`, and the 7th (index 6) is `supplier_id` with `randint(1, 5000)`.

But on line 507, the suppliers are generated with this call:
```python
gen_suppliers(row_targets["suppliers"])
```

Where `row_targets["suppliers"]` scales with the scale factor. At scale=0.1, this produces ~500 suppliers. The products still reference IDs up to 5000.

The column order at line 512-513 confirms index 6 is `supplier_id`:
```python
["id","name_en","name_ar",...,"category_id","supplier_id","unit_price","stock_quantity",...]
```

## Scope

**In scope:** `scripts/generate_test_dataset.py` only

**Out of scope:** Any production code, any other test scripts, the data sources or SQL generation logic

## Git workflow

- Branch: `advisor/023-fix-test-data-supplier-range`
- Commit message: `fix: make gen_products supplier_id range respect scale factor`

## Steps

### Step 1: Add `supplier_count` parameter to `gen_products`

Change the `gen_products` function signature from:
```python
def gen_products(n=50000):
```
to:
```python
def gen_products(n=50000, supplier_count=5000):
```

Replace the hardcoded `random.randint(1, 5000)` on line 350 with:
```python
random.randint(1, supplier_count),
```

The full line should become:
```python
random.randint(1, 300), random.randint(1, supplier_count),
```

### Step 2: Update the call site

In the `main()` block at line 513, change:
```python
gen_products(row_targets["products"]))
```
to:
```python
gen_products(row_targets["products"], row_targets["suppliers"]))
```

**Verify**: `python scripts/generate_test_dataset.py --scale 1.0` (with `--db-path` pointing to a temp location) should complete without errors. Then verify with scale 0.1.

## Test plan

Manual: run `python scripts/generate_test_dataset.py --scale 0.1 --db-path /tmp/test_scale.db` and check:
```sql
SELECT COUNT(*) FROM products p LEFT JOIN suppliers s ON p.supplier_id = s.id WHERE s.id IS NULL;
```
This should return 0 after the fix (previously ~90% of products).

## Done criteria

- [ ] `gen_products` accepts `supplier_count` parameter
- [ ] `randint(1, 5000)` replaced with `randint(1, supplier_count)`
- [ ] Call site passes `row_targets["suppliers"]` as second argument
- [ ] At scale=0.1, 0% of products have invalid supplier references
- [ ] No files outside in-scope list modified
- [ ] `plans/README.md` status row updated

## STOP conditions

- The column order in the INSERT on line 512 has changed — verify `supplier_id` is still the 7th column (index 6) before editing
- The `row_targets` dict doesn't have a `"suppliers"` key

## Maintenance notes

If more reference columns are added to `gen_products` in the future (e.g., a `manufacturer_id`), each must be parameterized similarly instead of hardcoding the max ID. This pattern applies to all `*_id` columns in the test data generators.
