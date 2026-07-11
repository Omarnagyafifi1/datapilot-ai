# Plan 002: Fix scenario memory embedding to use stable hash

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md`.
>
> **Drift check (run first)**: `git diff --stat c5d07ba..HEAD -- backend/app/agents/scenario_memory.py`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P1
- **Effort**: S
- **Risk**: LOW
- **Depends on**: none
- **Category**: bug
- **Planned at**: commit `c5d07ba`, 2026-07-11

## Why this matters

The `ScenarioMemory._embed` method uses Python's built-in `hash()` which is salted with a random seed per process start (PYTHONHASHSEED). This means the same text produces different embedding vectors every time the server restarts. The FAISS index built in one process is meaningless in another — similarity search returns effectively random results. Users see different scenario matches after every deployment.

## Current state

In `backend/app/agents/scenario_memory.py`, the `_embed` method at line 79:

```python
def _embed(self, text: str, dim: int = 512) -> np.ndarray:
    vec = np.zeros(dim, dtype=np.float32)
    for token in self._tokenize(text):
        vec[hash(token) % dim] += 1.0
    norm = float(np.linalg.norm(vec))
    if norm > 0:
        vec /= norm
    return vec
```

`hash(token)` uses Python's built-in `hash()`, which for strings is randomized per-process (since Python 3.3). The fix: use a deterministic hash function like `hashlib.md5` or Python's `zlib.adler32`.

## Commands you will need

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Typecheck | `python -c "import ast; ast.parse(open('backend/app/agents/scenario_memory.py').read()); print('OK')"` | exit 0, prints OK |
| Tests | `python -m pytest backend/final_test/ -v` | all pass |

## Scope

**In scope**:
- `backend/app/agents/scenario_memory.py`

**Out of scope**:
- Any other file

## Git workflow

- Branch: `advisor/002-scenario-memory-stable-hash`
- Commit message: `fix: use deterministic hash in scenario memory embedding`
- Do NOT push or open a PR unless instructed

## Steps

### Step 1: Import hashlib at top of file

Add `import hashlib` to the imports section of `backend/app/agents/scenario_memory.py`. Place it with the other stdlib imports (after `import json` or `import re`).

### Step 2: Replace `hash(token)` with deterministic hash

Change the `_embed` method. Replace:

```python
vec[hash(token) % dim] += 1.0
```

with:

```python
# Use hashlib for deterministic hash (Python's built-in hash() is salted per-process)
digest = hashlib.md5(token.encode("utf-8")).digest()
idx = int.from_bytes(digest[:4], "little") % dim
vec[idx] += 1.0
```

The full method after the change should be:

```python
def _embed(self, text: str, dim: int = 512) -> np.ndarray:
    vec = np.zeros(dim, dtype=np.float32)
    for token in self._tokenize(text):
        digest = hashlib.md5(token.encode("utf-8")).digest()
        idx = int.from_bytes(digest[:4], "little") % dim
        vec[idx] += 1.0
    norm = float(np.linalg.norm(vec))
    if norm > 0:
        vec /= norm
    return vec
```

**Verify**: Read the modified `_embed` method and confirm `hash(token)` has been replaced.

### Step 3: Run tests

```bash
python -m pytest backend/final_test/ -v
```

## Test plan

No new tests needed. The existing test suite validates the overall system works. If you want to add a test:

- Add a test in `backend/final_test/test_units.py` that:
  1. Creates a `ScenarioMemory` instance with a temp path
  2. Calls `_embed("some text")` twice
  3. Asserts both calls return equal vectors (proving determinism)

```python
def test_scenario_memory_embed_deterministic(tmp_path):
    from app.agents.scenario_memory import ScenarioMemory
    mem = ScenarioMemory(tmp_path / "scenarios.md")
    vec1 = mem._embed("test question")
    vec2 = mem._embed("test question")
    assert (vec1 == vec2).all()
```

## Done criteria

ALL must hold:

- [ ] `python -c "import ast; ast.parse(open('backend/app/agents/scenario_memory.py').read()); print('OK')"` exits 0
- [ ] `python -m pytest backend/final_test/ -v` exits 0, all tests pass
- [ ] `grep -n "hash(token)" backend/app/agents/scenario_memory.py` returns no matches
- [ ] `grep "hashlib" backend/app/agents/scenario_memory.py` shows `import hashlib` at the top
- [ ] No files outside the in-scope list are modified (`git status`)
- [ ] `plans/README.md` status row updated to DONE

## STOP conditions

Stop and report back if:

- The code at the locations in "Current state" doesn't match the excerpts.
- A step's verification fails twice after a reasonable fix attempt.
- The fix appears to require touching an out-of-scope file.

## Maintenance notes

- `hashlib.md5` is deterministic and fast. The first 4 bytes of the digest give 2^32 possible bucket indices, which is more than enough for dim=512.
- If the `dim` parameter ever changes, the hash-to-index mapping is recomputed on the next `_embed` call — no migration needed since the FAISS index is rebuilt from scratch on each process start anyway.
