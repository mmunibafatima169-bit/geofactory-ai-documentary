# AGENTS.md — Mandatory Rules for Every Future AI Agent

This document defines the mandatory operating rules for any AI agent working on the GeoFactory project. These rules are non-negotiable and must be followed in every session.

---

## 1. Mandatory Start-of-Session Protocol

Before making ANY modifications, every agent MUST:

1. **Read all six mandatory project documents:**
   - `GEOFACTORY_MASTER_CONTEXT.md`
   - `AGENTS.md` (this file)
   - `PROJECT_STATUS.md`
   - `NEXT_TASK.md`
   - `CHANGELOG.md`
   - `AGENT_RESUME_PROMPT.md`

2. **Inspect Git status completely:**
   ```bash
   git status
   git log --oneline -5
   git diff --stat
   git stash list
   git branch -a
   ```

3. **Record the starting commit:** Note the exact HEAD SHA-256.

4. **Identify the single approved task** from `NEXT_TASK.md`.

5. **Check for unfinished work** from the previous agent (see `PROJECT_STATUS.md` and `NEXT_TASK.md`).

---

## 2. Mandatory Development Rules

### 2.1 Scope Discipline
- **Work ONLY within the approved task scope** defined in `NEXT_TASK.md`.
- Do not begin future tasks without explicit user authorization.
- Do not "improve" unrelated code while working on the approved task.

### 2.2 Preservation of Existing Work
- **Never delete existing files** without explicit user approval.
- **Never overwrite existing work blindly** — read first, understand, then modify.
- **Never reset the repository** (`git reset`, `git clean`, `git restore`, `git checkout` to discard changes).
- **Never discard staged or unstaged changes** without documenting and user approval.
- **Never replace existing documentation** without reading it first.

### 2.3 Git Hygiene
- **Use a separate feature branch** for all development: `git checkout -b feature/<task-name>`
- **Never commit directly to `main`**.
- Create meaningful checkpoint commits **only after verification and user authorization**.
- Push checkpoint commits to the feature branch **only after explicit user authorization**.
- Never describe uncommitted local work as "safely backed up on GitHub".

### 2.4 Testing & Verification
- Run relevant tests **before and after** changes:
  ```bash
  python3 -m unittest discover -v
  cd studio/remotion && npx tsc --noEmit
  # If dashboard changes: npx next typegen && npm exec tsc -- --noEmit && npm run build
  ```
- **Record test results** in `CHANGELOG.md` and session notes.
- Do not claim a feature works without test evidence.

### 2.5 Evidence-Based Claims
- Every capability claim must have **verifiable evidence**: test output, file path, command result.
- Distinguish **VERIFIED** (tested, evidenced) from **REPORTED** (claimed in docs but not independently verified) from **UNVERIFIED** (no evidence).
- Do not confuse source-code existence with production readiness.

### 2.6 Documentation Updates
- Update relevant project documentation **regularly during development**, not just at the end.
- At minimum, update before ending a session:
  - `PROJECT_STATUS.md` — current state, verified/unverified/blocked items
  - `NEXT_TASK.md` — single highest-priority next task (or "awaiting user direction")
  - `CHANGELOG.md` — when meaningful changes occurred (with dates, commit IDs, evidence)

---

## 3. Mandatory End-of-Session Protocol

Before ending any work session, the agent MUST:

1. **Update `PROJECT_STATUS.md`** with:
   - Current Git state (HEAD commit, branch, clean/dirty)
   - Verified implementation status changes
   - New blockers discovered
   - Test results

2. **Update `NEXT_TASK.md`** with:
   - Single highest-priority next task (objective, reason, steps, acceptance criteria, dependencies, blockers, verification)
   - Or "Awaiting user direction" if no clear next step

3. **Update `CHANGELOG.md`** if meaningful changes occurred:
   - Date, commit ID (if committed), description, evidence

4. **Record exact Git state:**
   ```bash
   git status
   git log --oneline -1
   ```

5. **Provide a handoff summary** for the next agent:
   - What was done (with evidence)
   - What remains unfinished
   - Exact continuation instructions
   - Any uncertain or missing information

6. **List unfinished work** explicitly — do not hide incomplete items.

---

## 4. Prohibited Actions

The following are **NEVER permitted** without explicit user approval:

- `git reset`, `git clean`, `git restore` (discarding changes)
- `git checkout` (changing branches during initial inspection)
- `git pull`, `git merge`, `git rebase`, `git cherry-pick`
- `git stash` (hiding work)
- Installing paid tools or services
- Automatic merge, publish, deploy, or public upload
- Committing directly to `main`
- Pushing without explicit user authorization
- Claiming production quality without evidence
- Beginning a new task without updating `NEXT_TASK.md` and getting authorization

---

## 5. Communication Standards

- **Explain important actions in simple language** — the user is not a professional programmer.
- **Give exact copy-paste commands** when user interaction is needed.
- **Do not ask the user to make unnecessary technical decisions**.
- **Do not repeat questions** already answered in project documentation.
- **Do not perform lengthy unnecessary experiments**.
- **Do not generate another 60-second sample** unless explicitly authorized.
- **Prioritize actual production blockers** over optional installations.

---

## 6. Legal & Licensing Honesty

- **Record all licence decisions** in code comments, metadata, and documentation.
- **Never claim commercial rights** without verified source evidence.
- Distinguish between: "licence metadata says X" vs "we have independently verified X".
- **Never copy RealLifeLore content, branding, wording, thumbnails, footage, voice, or assets**.
- Style inspiration only — measured rubric from public thumbnails, not replication.

---

## 7. Emergency Stop Conditions

If any of these conditions occur, **STOP immediately and report to user**:

- Workspace identity or repository remote cannot be verified
- Unexpected modifications or conflicts found during initial inspection
- Baseline commit or expected history doesn't match
- Production blocker discovered that cannot be resolved within approved scope
- Test suite regressions introduced
- Legal/licensing uncertainty that affects deliverables

---

## 8. Quick Reference: Required Commands at Session Start

```bash
# 1. Verify workspace
pwd
git remote -v
git branch
git log --oneline -1

# 2. Check status
git status
git diff --stat
git stash list

# 3. Read all six docs
cat GEOFACTORY_MASTER_CONTEXT.md
cat AGENTS.md
cat PROJECT_STATUS.md
cat NEXT_TASK.md
cat CHANGELOG.md
cat AGENT_RESUME_PROMPT.md

# 4. Run test gate
python3 -m unittest discover -v 2>&1 | tail -20
```

---

**Remember:** GeoFactory belongs to the project repository, not to an AI agent. Every new agent must understand the existing work, continue from the last verified checkpoint, save progress, and leave the project ready for the next agent. Never restart unnecessarily. Never lose verified progress. Never leave the next agent confused.
