# CHANGELOG.md — Verified Historical Changes

**Format:** Date | Commit ID | Component | Change Description | Evidence

---

## 2026-11-12 | (Current Session) | Documentation | Reconstructed six permanent project continuity documents | Files created: GEOFACTORY_MASTER_CONTEXT.md, AGENTS.md, PROJECT_STATUS.md, NEXT_TASK.md, CHANGELOG.md, AGENT_RESUME_PROMPT.md in /root/geofactory-ai-documentary/geofactory/

## 2026-11-11 | 49d22d7 | Studio/Quality | Deliver Studio v2 with rendered 60-second documentary sample | 60s v2 sample at studio/remotion/out/venice_sample_60s_v2.mp4 (60.000s, 1080p30, -15.7 LUFS); editorial QA v2 (0 critical); factual verifier passing; asset selector with 2 licensed assets

## 2026-11-11 | dc85cdd | Studio/Architecture | Add Studio layer: multi-engine architecture with Visual Director | New modules: studio/scene_manifest.py, visual_director.py, design_tokens.py, editorial_qa.py, asset_selector.py, factual_verifier.py; Remotion project; Blender/Manim adapters; CLI: plan, editorial-report

## 2026-11-11 | c3acccd | Video Editor | Upgrade visual storytelling: paced stills, motion variety, map montage | video_editor.py: ≤22s still beats (floor 12s), round-robin rotation, 4 alternating Ken Burns motions + grade/vignette, closing montage anchors (70-92%)

## 2026-11-11 | 4e2d140 | Tests | Fix dry-run test path resolution to match config semantics | test_pipeline.py: Path.cwd() → config_path.parent / root (mirrors app semantics)

## 2026-11-11 | 52127e8 | Thumbnail | Tune thumbnail engine to measured reference study | thumbnail_engine.py: saturation band 0.336–0.703, headline area ≤23.8%, bottom-right clearance from RealLifeLore 15-thumbnail analysis

## 2026-11-11 | bd7be89 | CLI/Analysis | Add Gemini video structure analysis CLI | New command for reference video analysis (not production)

## 2026-11-11 | ee0efd5 | Thumbnail/Analysis | Improve thumbnail scoring and document reference analysis | Enhanced scoring rubric; reference study documented

## 2026-11-11 | 5d523ae | Maps/Thumbnail | Add map animation and thumbnail engines | map_animation_engine.py (Natural Earth), thumbnail_engine.py (3 concepts, scored)

## 2026-11-11 | 05e50ce | Providers | Add optional Groq and stock media providers | groq_client.py, Pexels/Pixabay in asset_manager.py, stock-search CLI

## 2026-11-11 | a73d20b | QA | Record post-render memory snapshot | Doctor check after render; RAM/disk logging

## 2026-11-11 | 63fe742 | Pipeline | Complete Phase 4 Iceland documentary package | 1,771 words, 711.5s eSpeak audio, 1280x720 MP4, 11 claims (unreviewed), QA blocks approval

## 2026-11-11 | 280aea5 | Docs | Correct documented memory snapshot | PROJECT_MASTER_LOG.md accuracy fix

## 2026-11-11 | bf5cb4e | TTS/Render | Add local narration and FFmpeg rendering | tts_engine.py (Edge/eSpeak), video_editor.py (Ken Burns, soft SRT)

## 2026-11-11 | 5779b11 | Research/Assets | Add Wikimedia research and licensed asset workflow | research_agent.py (Wikipedia API), asset_manager.py (Commons download + licence gate)

## 2026-11-11 | bde69f8 | Core | Build local-first GeoFactory workflow | SQLite jobs, idempotency, transitions, approval hashing, CLI framework

## 2026-11-11 | 46b2dd5 | Core | Create main.py | Entry point (later replaced by cli.py module)

## 2026-11-11 | 1b1fee3 | Core | Create story_generator.py | Starter file (preserved, not used in workflow)

## 2026-11-11 | 8b15255 | Config | Create .env | Example env (later removed from Git index, preserved locally)

---

## Earlier History (from PROJECT_MASTER_LOG.md)

| Date | Commit | Component | Change |
|------|--------|-----------|--------|
| 2026-11-11 | (initial) | Repo | GitHub clone: mmunibafatima169-bit/geofactory-ai-documentary |
| 2026-11-11 | — | Environment | Sandbox engineering: static FFmpeg, eSpeak NG via Debian debs, Chrome headless + nspr/nss |
| 2026-11-11 | — | Tests | Fixed test bug (4e2d140); suite 39→50 passing |
| 2026-11-11 | — | Venice v1 | 8-min documentary package (494.7s, 1920x1080→720p, 10 claims, approved) |
| 2026-11-11 | — | Venice v2 | Editorial rebuild: fixed claims, 4 Ken Burns motions, map montage, charts, 487.2s, approved |
| 2026-11-11 | — | GitHub Push | 4e2d140 + c3acccd pushed via user PAT (revoked) |
| 2026-11-11 | — | Studio v1 | 60s multi-engine sample (Remotion cold-open, 6 scenes, 60.000s) |
| 2026-11-11 | — | Studio v2 | Quality upgrade: licensed footage, archival film, factual ledger, decoded QA, 0 freezes |

---

## Notes

- **Never invent historical dates, commits, or test results.** Only record verified changes.
- Dates above for commits before 2026-11-11 are approximate (from PROJECT_MASTER_LOG.md session log).
- Commit IDs 49d22d7, dc85cdd, c3acccd, 4e2d140, 52127e8, bd7be89, ee0efd5, 5d523ae, 05e50ce, a73d20b, 63fe742, 280aea5, bf5cb4e, 5779b11, bde69f8, 46b2dd5, 1b1fee3, 8b15255 are verified from `git log --oneline`.
- The baseline commit 188e0a459f1aeb5f742c14fd425b1b5718c3888c mentioned in handoff does NOT exist in this repository's history.
