# Plan 032: Fix missing AI insights and blank export charts

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md` — unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**: `git diff --stat HEAD -- backend/app/agents/graph.py frontend/src/components/ResultVisualizer.jsx`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P1
- **Effort**: S
- **Risk**: LOW
- **Depends on**: none
- **Category**: bug
- **Planned at**: <YYYY-MM-DD>

## Why this matters

The AI insights and next steps often fail to appear because the JSON parser doesn't properly extract arrays if the LLM includes conversational text before the JSON. The HTML export report generates a broken, blank chart because its fallback SVG generator fails on text columns, and it completely ignores the rich Plotly chart specification already available in the document.

## Current state

- `backend/app/agents/graph.py` — The JSON parser relies on checking if the text starts exactly with `[` to determine if it should parse an array, failing when conversational text precedes it.
- `frontend/src/components/ResultVisualizer.jsx` — The `exportReport` function relies purely on the fallback `buildChartSVG` without properly checking for valid numeric values, causing `NaN` rect heights. It also ignores the Plotly specification when generating the HTML report.

Excerpts:
**backend/app/agents/graph.py:112-114**
```python
    # Try array first if text starts with `[`, otherwise try object first
    braces = ('[', ']') if text.startswith('[') else ('{', '}')
    for open_char, close_char in [braces, ('{', '}') if braces != ('{', '}') else ('[', ']')]:
```

**frontend/src/components/ResultVisualizer.jsx:322-328**
```javascript
  const viz = doc.visualization || {};
  const chartType = viz.chart_type || 'bar';
  const chartSvg = buildChartSVG(doc.results || [], chartType);
  const chartSection = chartSvg
    ? `<h2>Chart (${chartType})</h2><div style="text-align:center;margin:16px 0;">${chartSvg}</div>`
    : '';
```

## Commands you will need

| Purpose   | Command                  | Expected on success |
|-----------|--------------------------|---------------------|
| Backend Test | `cd backend && pytest` | all pass            |
| Frontend Lint | `cd frontend && npm run lint` | exit 0              |

## Scope

**In scope** (the only files you should modify):
- `backend/app/agents/graph.py`
- `frontend/src/components/ResultVisualizer.jsx`

## Git workflow

- Branch: `advisor/032-fix-insights-and-export-chart`
- Commit message: `fix: improve json parsing for insights and add plotly to export report`

## Steps

### Step 1: Fix `_safe_json_parse` in backend

Open `backend/app/agents/graph.py` and modify `_safe_json_parse` to detect the correct outermost brackets even if there is conversational text.

Find:
```python
    # Try array first if text starts with `[`, otherwise try object first
    braces = ('[', ']') if text.startswith('[') else ('{', '}')
    for open_char, close_char in [braces, ('{', '}') if braces != ('{', '}') else ('[', ']')]:
```

Replace with:
```python
    # Find the first array and object brackets
    first_square = text.find('[')
    first_curly = text.find('{')
    
    # Try array first if it appears before an object, otherwise try object first
    if first_square != -1 and (first_curly == -1 or first_square < first_curly):
        braces = ('[', ']')
    else:
        braces = ('{', '}')
    
    for open_char, close_char in [braces, ('{', '}') if braces != ('{', '}') else ('[', ']')]:
```

**Verify**: `cd backend && pytest` → all pass.

### Step 2: Use Plotly spec in `exportReport` and fix fallback SVG

Open `frontend/src/components/ResultVisualizer.jsx`. Modify `exportReport` to render the Plotly chart when `hasPlotlySpec` is true. Also modify `buildChartSVG` to properly check for valid numbers.

Find `exportReport` and replace the chart generation logic:
```javascript
  const viz = doc.visualization || {};
  const hasPlotlySpec = viz && viz.spec && viz.spec.data;
  
  let chartSection = '';
  if (hasPlotlySpec) {
    const specJson = JSON.stringify(viz.spec).replace(/</g, '\\u003c');
    chartSection = `
      <h2>Chart (${viz.chart_type || 'Visualization'})</h2>
      <div id="plotly-chart" style="width:100%; height:400px; margin:16px 0;"></div>
      <script>
        const spec = ${specJson};
        if (window.Plotly) {
          Plotly.newPlot('plotly-chart', spec.data || [], spec.layout || {}, { responsive: true });
        }
      </script>
    `;
  } else {
    const chartType = viz.chart_type || 'bar';
    const chartSvg = buildChartSVG(doc.results || [], chartType);
    chartSection = chartSvg
      ? `<h2>Chart (${chartType})</h2><div style="text-align:center;margin:16px 0;">${chartSvg}</div>`
      : '';
  }

  const title = doc.question || 'DataPilot Report';
```

And update the HTML template within `exportReport` to include the Plotly script in the `<head>`:
Find:
```javascript
const html = `<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>${title}</title>
<style>
```
Replace with:
```javascript
const html = `<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>${title}</title>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
```

Finally, find `buildChartSVG` and update the `numKeys` filter so it avoids `null`, `""`, and `NaN`:
Find:
```javascript
  const strKey = keys.find((key) => typeof results[0][key] === 'string') || null;
  const numKeys = keys.filter((key) => Number.isFinite(Number(results[0][key])));
  const labelKey = strKey || numKeys[0] || keys[0];
```
Replace with:
```javascript
  const strKey = keys.find((key) => typeof results[0][key] === 'string') || null;
  const numKeys = keys.filter((key) => {
    const val = results[0][key];
    return val !== null && val !== '' && !Number.isNaN(Number(val)) && Number.isFinite(Number(val));
  });
  if (numKeys.length === 0) return '';
  const labelKey = strKey || numKeys[0] || keys[0];
```

**Verify**: `cd frontend && npm run lint` → exit 0.

## Done criteria

- [ ] `pytest` passes in the `backend/` directory
- [ ] `npm run lint` passes in the `frontend/` directory
- [ ] `_safe_json_parse` checks `first_square < first_curly` rather than just `text.startswith`
- [ ] `exportReport` inserts Plotly script into HTML head and uses Plotly when `hasPlotlySpec` is true.
- [ ] `buildChartSVG` correctly filters numeric columns and returns `''` if none are found.

## STOP conditions

- If `_safe_json_parse` looks significantly different from the excerpt.
- If Plotly integration causes unexpected linting errors about `window.Plotly`.

## Maintenance notes

This fixes the JSON parsing issue in `insight_node` and `suggestion_node`. The fallback SVG builder in the frontend was producing an `<rect height="NaN">` when processing strings, breaking the entire SVG. It will now gracefully return no SVG if no valid numeric data is found, preventing the "blank space" issue. Plotly support in the HTML report guarantees the visual matches the UI precisely.
