# Plan 035: Fix export chart to render when results are string-only

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md` — unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**: `git diff --stat 80a9d6f..HEAD -- frontend/src/components/ResultVisualizer.jsx`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P1
- **Effort**: S
- **Risk**: LOW
- **Depends on**: none
- **Category**: bug
- **Planned at**: commit `80a9d6f`, 2026-07-12

## Why this matters

When query results contain only string columns (e.g., `SELECT DISTINCT title FROM ...`), the export report shows "Chart (bar)" followed by blank space — no SVG, no Plotly chart. The issue is twofold: (1) `buildChartSVG` returns `''` when no numeric columns are found (which is correct for its numeric charts), but the export has no fallback visualization for string-only data; (2) the Plotly path (`hasPlotlySpec`) may not render because the spec's `data` array is empty for string-only queries. The user sees a broken export with a missing chart.

## Current state

`buildChartSVG` at `frontend/src/components/ResultVisualizer.jsx:408-438`:

```javascript
function buildChartSVG(results = [], chartType = 'bar') {
  if (!results.length) return '';
  const keys = Object.keys(results[0]);
  const strKey = keys.find((key) => typeof results[0][key] === 'string') || null;
  const numKeys = keys.filter((key) => {
    const val = results[0][key];
    return val !== null && val !== '' && !Number.isNaN(Number(val)) && Number.isFinite(Number(val));
  });
  if (numKeys.length === 0) return '';  // <-- returns empty for string-only results
  // ...
  return buildBarSVG(labels, values);
}
```

The `exportReport` function at `frontend/src/components/ResultVisualizer.jsx:310-392` uses Plotly when `viz.spec.data` exists, otherwise falls back to `buildChartSVG`:

```javascript
const viz = doc.visualization || {};
const hasPlotlySpec = viz && viz.spec && viz.spec.data;

let chartSection = '';
if (hasPlotlySpec) {
  // Plotly render path
} else {
  const chartSvg = buildChartSVG(doc.results || [], chartType);
  chartSection = chartSvg ? `<h2>Chart...</h2>...${chartSvg}...` : '';
}
```

For a `SELECT DISTINCT title FROM ...` query, the `generate_visualization` function in the backend returns a spec with `chart_type: "bar"` but the Plotly `spec.data` may contain an empty trace or a bar chart with string x-values and no y-values. When `viz.spec.data` is truthy (an array, possibly empty), the Plotly path is taken but may render nothing. If `spec.data` is empty, `hasPlotlySpec` is falsy, and `buildChartSVG` returns `''` because `numKeys.length === 0`.

**Repo conventions**: React functional components with hooks, inline SVG generation via helper functions (`buildBarSVG`, `buildPieSVG`, etc.). Match the existing SVG builder style.

## Commands you will need

| Purpose   | Command                  | Expected on success |
|-----------|--------------------------|---------------------|
| Lint      | `cd frontend && npm run lint` | exit 0 |
| Build     | `cd frontend && npm run build` | exit 0 |

## Scope

**In scope**:
- `frontend/src/components/ResultVisualizer.jsx` — only `buildChartSVG` and `exportReport`

**Out of scope**:
- Backend `graph.py`, `visualization_service.py`
- The Plotly rendering in the main UI (React component) — that path works; only the export is broken

## Steps

### Step 1: Update `buildChartSVG` to render a frequency bar chart for string-only data

When `numKeys.length === 0` but there are string keys, compute value counts and render a bar chart with frequencies. This gives meaningful output for `SELECT DISTINCT title` queries.

Find this block at `frontend/src/components/ResultVisualizer.jsx:416`:

```javascript
  if (numKeys.length === 0) return '';
```

Replace the entire method body so that when `numKeys.length === 0` and there are string keys, it generates a frequency chart. The result should be:

```javascript
function buildChartSVG(results = [], chartType = 'bar') {
  if (!results.length) return '';
  const keys = Object.keys(results[0]);
  const strKey = keys.find((key) => typeof results[0][key] === 'string') || null;
  const numKeys = keys.filter((key) => {
    const val = results[0][key];
    return val !== null && val !== '' && !Number.isNaN(Number(val)) && Number.isFinite(Number(val));
  });

  // For string-only results, build a frequency bar chart using value counts
  if (numKeys.length === 0 && strKey) {
    const freq = {};
    for (const row of results) {
      const val = String(row[strKey] ?? '');
      freq[val] = (freq[val] || 0) + 1;
    }
    const labels = Object.keys(freq).slice(0, 12);
    const values = labels.map((l) => freq[l]);
    return buildBarSVG(labels, values);
  }

  // Fall back to empty if truly nothing to chart
  if (numKeys.length === 0) return '';

  const labelKey = strKey || numKeys[0] || keys[0];
  const valueKey = numKeys[0] || keys[0];
  // ... rest of existing function unchanged (lines 420-437)
```

**Verify**: `cd frontend && npm run lint` → exit 0

### Step 2: Ensure `exportReport` includes a chart for string-only results

The `exportReport` function already has the two paths (Plotly + SVG fallback). With step 1's fix, the SVG fallback now handles string-only data. Verify the flow by checking that when `hasPlotlySpec` is false (or the Plotly CDN fails), `buildChartSVG` produces SVG for string-only results.

No code change needed in `exportReport` — the fix in step 1 is sufficient. If there are test files (none currently for the export function), this step is verification-only.

**Verify**: `cd frontend && npm run build` → exit 0

## Test plan

- No automated tests for `buildChartSVG` exist. Manual verification required:
  - Load a query that returns only string columns (e.g., `SELECT DISTINCT title FROM ...`).
  - Click the export button.
  - Confirm the generated HTML includes an SVG bar chart showing value frequencies.
- The existing `npm run lint` and `npm run build` commands verify code correctness.

## Done criteria

All must hold:

- [ ] `cd frontend && npm run lint` — exit 0
- [ ] `cd frontend && npm run build` — exit 0
- [ ] `buildChartSVG` no longer returns `''` for string-only results; instead produces a frequency bar chart
- [ ] No files outside `frontend/src/components/ResultVisualizer.jsx` are modified

## STOP conditions

Stop and report back if:

- The `buildChartSVG` function at `frontend/src/components/ResultVisualizer.jsx:408` doesn't match the excerpt.
- `npm run lint` produces errors unrelated to the changed code (pre-existing lint issues).

## Maintenance notes

The frequency-chart fallback is a simple value-count approach. For very large datasets (>1000 unique values), it slices to 12 labels. If the dataset has more than 12 unique string values, some are omitted. This matches the existing cap in `buildBarSVG` (line 434: `results.slice(0, 12)`). The Plotly path in `exportReport` should eventually become the primary rendering path; this SVG fallback is a safety net.
