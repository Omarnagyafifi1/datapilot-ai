# Plan 013: Fix PDF export chart rendering (inline CSS var values)

> **Executor instructions**: Follow this plan step by step. Run every
> verification command before moving to the next step. If anything in the
> "STOP conditions" section occurs, stop and report.
>
> **Drift check**: `git diff --stat cea37b2..HEAD -- frontend/src/components/ResultVisualizer.jsx`
> If changed, compare excerpts against live code; mismatch = STOP.

## Status

- **Priority**: P1
- **Effort**: S
- **Risk**: LOW
- **Depends on**: none
- **Category**: bug
- **Planned at**: commit cea37b2, 2026-07-11

## Why this matters

The SVG charts in the exported PDF report use CSS variables (`var(--cyber-blue)`, `var(--background)`, `var(--foreground)`, `var(--muted)`) that don't resolve in a standalone HTML document outside the Tailwind/CSS-variable context. When the user clicks "Export Report," the generated HTML has invisible charts — the bars, pie slices, lines, and dots all render with transparent or undefined colors. Inlining the actual hex values fixes this.

## Current state

`frontend/src/components/ResultVisualizer.jsx` has 6 SVG-building functions that all use CSS variables:

- `buildBarSVG` (line 404): `fill="var(--cyber-blue)"` (bar fill), `fill="var(--foreground)"` (label text), `fill="var(--background)"` (background rect)
- `buildPieSVG` (line 418): `fill="var(--cyber-blue)"`, `fill="var(--cyber-pink)"`, `fill="var(--cyber-lime)"` (slice colors), `fill="var(--foreground)"` (legend text), `fill="var(--background)"` (background rect)
- `buildLineSVG` (line 433): `stroke="var(--cyber-blue)"` (line), `fill="var(--cyber-blue)"` (dots), `fill="var(--foreground)"` (labels), `fill="var(--background)"` (background rect)
- `buildScatterSVG` (line 460): `fill="var(--cyber-blue)"` (dots), `fill="var(--muted)"` (axis labels), `fill="var(--background)"` (background rect)
- `buildHistogramSVG` (line 480): `fill="var(--cyber-blue)"` (bars), `fill="var(--muted)"` (labels), `fill="var(--background)"` (background rect)
- `downloadPNGFromSVG` (line 511): `ctx.fillStyle = 'var(--background)'` (canvas fill)

The `exportReport` function (line 304) builds a standalone HTML document with its own `<style>` block but does NOT include CSS variable definitions — the variables come from Tailwind classes loaded in the main app.

## Repo conventions

- Color scheme uses Tailwind classes in JSX and CSS variables in SVG. The actual variable values are defined in `frontend/src/index.css` (Tailwind `@theme` block or `:root`).
- Use the same hex values that the existing CSS variables resolve to.

## Scope

**In scope**: `frontend/src/components/ResultVisualizer.jsx`

**Out of scope**: Any other file, any styling outside the SVG inline fills

## Git workflow

- Branch: `advisor/013-fix-pdf-export-chart-colors`
- Commit message: `fix: inline CSS variable values in SVG chart building functions`

## Steps

### Step 1: Identify the actual CSS variable values

Read `frontend/src/index.css` and find the `:root` or `@theme` block where the CSS variables are defined. Look for `--cyber-blue`, `--cyber-pink`, `--cyber-lime`, `--background`, `--foreground`, `--muted`.

If they're in a Tailwind config (`frontend/tailwind.config.js` or `frontend/src/index.css`), note the hex values. Common values might be:
- `--cyber-blue`: `#00d4ff` (cyan)
- `--cyber-pink`: `#ff2d95`
- `--cyber-lime`: `#a3e635`
- `--background`: `#0a0a0f` or similar dark
- `--foreground`: `#e2e8f0` or similar light
- `--muted`: `#64748b`

**Actually read the file to get the actual values** — do not assume.

### Step 2: Replace CSS variable references with inline hex values in all SVG builders

In `frontend/src/components/ResultVisualizer.jsx`, replace every occurrence of CSS variable references in SVG string templates with their actual hex values. The functions to modify:

1. `buildBarSVG` — replace `var(--cyber-blue)`, `var(--foreground)`, `var(--background)`
2. `buildPieSVG` — replace `var(--cyber-blue)`, `var(--cyber-pink)`, `var(--cyber-lime)`, `var(--foreground)`, `var(--background)`
3. `buildLineSVG` — replace `var(--cyber-blue)`, `var(--foreground)`, `var(--background)`
4. `buildScatterSVG` — replace `var(--cyber-blue)`, `var(--muted)`, `var(--background)`
5. `buildHistogramSVG` — replace `var(--cyber-blue)`, `var(--muted)`, `var(--background)`
6. `downloadPNGFromSVG` — replace `'var(--background)'` with the actual hex

Example: `fill="var(--cyber-blue)"` → `fill="#00d4ff"`

**Important**: Do NOT change the color computation logic, only replace the CSS variable strings.

**Verify**: Read the modified lines and confirm no `var(--` strings remain in any SVG template literal.

### Step 3: Add CSS variable fallback in the export report HTML

In the `exportReport` function (around line 325), the standalone HTML template has an inline `<style>` block. Add the CSS variable definitions inside the `:root` so the standalone document also has them:

```css
<style>
  :root {
    --cyber-blue: #00d4ff;
    --cyber-pink: #ff2d95;
    --cyber-lime: #a3e635;
    --background: #ffffff;
    --foreground: #1a1a2e;
    --muted: #64748b;
  }
  /* ... existing styles ... */
</style>
```

Use a light background (`#ffffff`) for the print-oriented report rather than the dark app background — this matches the print stylesheet already in the export (`color: #1a1a2e`, `background: #f1f5f9` for code blocks, etc.).

**Verify**: Read the `exportReport` function and confirm the `:root` block with CSS variable definitions exists before the rest of the `<style>` content.

## Test plan

- `npx tsc --noEmit` — must exit 0 (no TypeScript errors from the changes)
- `npx eslint frontend/src/components/ResultVisualizer.jsx` — exit 0

Manual test: open the app, run a query with results, click "Export Report" → the generated HTML should show charts with visible colors, not invisible/transparent elements.

## Done criteria

- [ ] All SVG building functions use hex color values instead of `var(--...)`
- [ ] The `exportReport` HTML template includes `:root` CSS variable definitions
- [ ] No `var(--` string remains inside any SVG template literal in `ResultVisualizer.jsx` (grep check)
- [ ] `npx tsc --noEmit` exits 0
- [ ] `npx eslint frontend/src/components/ResultVisualizer.jsx` exits 0

## STOP conditions

- Code excerpts don't match the live file
- The CSS variable values are defined inside a Tailwind `@theme` directive that makes them non-trivial to extract
- Verification fails twice

## Maintenance notes

- If new SVG chart types are added in the future, they must use hex color values or include CSS variable fallbacks in the export HTML.
- The `exportReport` function's `:root` block should be kept in sync with `index.css` if the color scheme is updated.
