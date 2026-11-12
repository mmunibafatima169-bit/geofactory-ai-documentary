# AGENT_RESUME_PROMPT.md — Reusable Handoff Prompt

**Use this prompt to start any new AI coding agent (Copilot, Arena, Claude, Gemini, Codex, etc.) on the GeoFactory project.**

---

## Prompt

```
You are taking over the GeoFactory AI Documentary project.

**Repository:** https://github.com/mmunibafatima169-bit/geofactory-ai-documentary
**Workspace:** /root/geofactory-ai-documentary/geofactory (or equivalent local path)
**Current HEAD:** 49d22d7f2989a7f2b081922741333a0dc6883cc1 (main branch)

**First, you MUST:**
1. Read all six mandatory continuity documents in the package directory:
   - GEOFACTORY_MASTER_CONTEXT.md
   - AGENTS.md
   - PROJECT_STATUS.md
   - NEXT_TASK.md
   - CHANGELOG.md
   - AGENT_RESUME_PROMPT.md (this file)

2. Verify Git state:
   git status
   git log --oneline -5
   git remote -v

3. Run the test gate (install Pillow/FFmpeg if needed):
   python3 -m unittest discover -v

4. Check NEXT_TASK.md for the authorized single task.

**Do NOT:**
- Modify any files before completing the above verification
- Begin a new task without explicit authorization
- Commit directly to main
- Push without explicit user approval
- Install paid tools or services

**Project Summary:**
GeoFactory is a local-first pipeline for producing 8–15 minute geography documentaries. It has a working CLI (20+ commands), SQLite persistence, Wikipedia/Commons research, map animation (Natural Earth), thumbnail engine, TTS narration, FFmpeg rendering, QA gates, hash-bound approval, and a loopback dashboard. The Studio layer (Remotion motion graphics, Visual Director, editorial QA, factual verifier, asset selector) is merged locally but not pushed to GitHub. A professional 60-second Venice v2 sample has been rendered with licensed footage, archival film, animated maps, charts, original music/SFX, and decoded-video QA verification.

**Current Blockers:** No API keys for Groq/Pexels/Pixabay; Piper voice licence uncleared; Manim/Blender runtimes unavailable; YouTube upload not implemented; all claims require manual human verification.

**Awaiting User Decision:** Next task is either (A) push Studio layer to GitHub, (B) configure API keys for live validation, (C) resolve Piper voice, or (D) begin YouTube OAuth implementation. See NEXT_TASK.md for details.
```

---

## Quick-Start Commands (Copy-Paste)

```bash
# 1. Navigate to project
cd /root/geofactory-ai-documentary/geofactory

# 2. Verify workspace
pwd && git remote -v && git branch && git log --oneline -1

# 3. Check Git status
git status

# 4. Read all six docs
cat GEOFACTORY_MASTER_CONTEXT.md
cat AGENTS.md
cat PROJECT_STATUS.md
cat NEXT_TASK.md
cat CHANGELOG.md
cat AGENT_RESUME_PROMPT.md

# 5. Run tests (install deps if needed)
python3 -m unittest discover -v 2>&1 | tail -30

# 6. Check current task
cat NEXT_TASK.md
```

---

## Key Project Paths

| Path | Purpose |
|------|---------|
| `/root/geofactory-ai-documentary/geofactory/` | Python package root (this directory) |
| `/root/geofactory-ai-documentary/` | Git repository root (docs, examples, studio/) |
| `geofactory/cli.py` | Main CLI entry point |
| `geofactory/core/` | Config, database, jobs |
| `geofactory/agents/` | Topic, research, script agents |
| `geofactory/media/` | Assets, maps, TTS, video, thumbnails |
| `geofactory/studio/` | Scene manifest, Visual Director, QA, engines |
| `geofactory/quality/` | QA engine |
| `geofactory/publishing/` | YouTube client (fail-closed) |
| `studio/remotion/` | Remotion motion graphics project |
| `examples/studio-sample-v2/` | 60s v2 sample artifacts |

---

## Critical Rules (Non-Negotiable)

1. **Preserve all existing work** — never delete, overwrite blindly, or reset
2. **Work in feature branches only** — never commit to main directly
3. **Test before and after changes** — `python3 -m unittest discover`
4. **Update docs at session boundaries** — PROJECT_STATUS.md, NEXT_TASK.md, CHANGELOG.md
5. **Evidence over claims** — every capability needs test/file/command proof
6. **Human approval gates** — no auto-merge, auto-publish, auto-deploy
7. **Legal honesty** — record licence decisions; never claim commercial rights without verification
8. **No RealLifeLore copying** — style inspiration only (measured rubric)

---

## If Sandbox/Environment Reset

Recreate tools (from PROJECT_MASTER_LOG.md §3):

```bash
# Python deps
pip3 install --break-system-packages --user -r /root/geofactory-ai-documentary/requirements.txt

# FFmpeg static
cd /tmp && curl -sL -o ffmpeg.tar.xz https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz
tar -xf ffmpeg.tar.xz && mkdir -p /root/geofactory-ai-documentary/.tools
cp ffmpeg-*-static/ffmpeg ffmpeg-*-static/ffprobe /root/geofactory-ai-documentary/.tools/

# eSpeak NG (manual Debian debs → .tools/espeak-root/)
# See PROJECT_MASTER_LOG.md §3.3 for package list

# Chrome for Remotion
cd /root/geofactory-ai-documentary/studio/remotion
npm install --no-audit --no-fund
npx remotion browser ensure

# Environment
export PYTHONPATH=/root/geofactory-ai-documentary
export PATH="/root/geofactory-ai-documentary/.tools:$PATH"
```

---

## Verification Checklist for New Agent

- [ ] All six continuity docs read and understood
- [ ] Git status clean, HEAD matches expected (49d22d7)
- [ ] Remote URL matches `mmunibafatima169-bit/geofactory-ai-documentary`
- [ ] Test suite runs (34 pass, 3 import errors without Pillow, 2 skipped without FFmpeg)
- [ ] NEXT_TASK.md shows "AWAITING USER DIRECTION"
- [ ] No uncommitted changes in working tree
- [ ] Understands: Studio layer unpushed (dc85cdd), v2 quality files uncommitted
- [ ] Understands: Baseline commit 188e0a4... NOT FOUND in history
- [ ] Ready to execute authorized single task only

---

**Remember:** GeoFactory belongs to the repository, not to an AI agent. Continue from the last verified checkpoint. Save progress. Leave the project ready for the next agent.
