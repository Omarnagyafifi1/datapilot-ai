# Plan 029: Add Test and Lint Steps to CI Pipeline

> **Executor instructions**: One workflow file to edit. Verify by checking the YAML parses.
>
> **Drift check**: `git diff --stat 0d59108..HEAD -- .github/workflows/deploy.yml`

## Status

- **Priority**: P2
- **Effort**: M
- **Risk**: LOW
- **Depends on**: none
- **Category**: dx
- **Planned at**: commit `0d59108`, 2026-07-12

## Why this matters

The CI pipeline (`.github/workflows/deploy.yml`) has zero verification steps. Every push to `main` builds and deploys regardless of test failures, lint errors, or broken builds. Currently there is no safety gate between "code merged" and "code serving production."

## Current state

`.github/workflows/deploy.yml:14-44` has a single `build-deploy` job with 4 steps: checkout, Azure login, ACR login, Docker build-and-push. No `pytest`, `npm lint`, or `npm build` runs before deployment.

The frontend has an ESLint config (`frontend/eslint.config.js`) but no `test` script in `package.json`. The backend has pytest (19 tests) but no CI invocation.

## Scope

**In scope:**
- `.github/workflows/deploy.yml` — add test/lint steps

**Out of scope:**
- Creating separate CI workflow for PRs
- Fixing lint errors (just run the check; if it fails, the workflow fails)
- Adding frontend tests (no test framework exists)

## Steps

### Step 1: Add lint-and-test job

Add a `lint-and-test` job before `build-deploy` in `deploy.yml`:

```yaml
jobs:
  lint-and-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.13'

      - name: Install Python deps
        run: |
          python -m pip install --upgrade pip
          pip install pytest ruff
          if [ -f backend/requirements.txt ]; then pip install -r backend/requirements.txt; fi

      - name: Lint Python
        run: ruff check backend/app/ --no-fix || true

      - name: Run backend tests
        run: pytest backend/final_test/ -v --tb=short

      - name: Set up Node
        uses: actions/setup-node@v4
        with:
          node-version: '22'

      - name: Install frontend deps
        run: npm ci --prefix frontend

      - name: Lint frontend
        run: npm run lint --prefix frontend

      - name: Build frontend
        run: npm run build --prefix frontend
```

### Step 2: Add job dependency

Change `build-deploy` to depend on `lint-and-test`:

```yaml
  build-deploy:
    needs: lint-and-test
    runs-on: ubuntu-latest
```

**Verify**: `python -c "import yaml; yaml.safe_load(open('.github/workflows/deploy.yml')); print('YAML OK')"` — exit 0.

## Test plan

The pipeline is its own test. If the YAML is valid and steps run without errors, the CI gate works. The `ruff check ... || true` makes lint non-blocking (informational only) initially — remove `|| true` once lint errors are resolved.

## Done criteria

- [ ] `lint-and-test` job exists in `deploy.yml` before `build-deploy`
- [ ] `build-deploy` has `needs: lint-and-test`
- [ ] Backend: Python setup, pip install, ruff lint (non-blocking), pytest
- [ ] Frontend: Node setup, npm ci, npm lint, npm build
- [ ] YAML parses correctly
- [ ] No files outside in-scope list modified
- [ ] `plans/README.md` status row updated

## STOP conditions

- GitHub Actions syntax is different from what's shown (verify against the existing workflow's runner/task pattern)
- The repo uses a different Python version (check `Dockerfile` or `runtime.txt`)

## Maintenance notes

When frontend tests are added (vitest or similar), add `npm run test --prefix frontend` to this job. When the test suite grows significantly, consider splitting into parallel jobs or adding a separate CI workflow for PRs. The ruff lint is non-blocking (`|| true`) to avoid failing the pipeline on pre-existing lint issues — remove this escape hatch after lint errors are cleaned up.
