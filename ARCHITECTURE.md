# Architecture and data flow

## Runtime shape

The project is a Python package (`geofactory`) with a CLI, a loopback-only HTTP review dashboard, SQLite persistence, optional Python provider dependencies, and media executables. `python -m geofactory` is the entry point. The pre-existing story-generation files remain untouched and separate.

```text
CLI / loopback dashboard
          |
          +-- core/config.py (validated safe defaults)
          +-- core/database.py (SQLite schema/version)
          +-- core/jobs.py (idempotency, transitions, recovery, approval hash)
          |
          +-- agents/topic_agent.py (deterministic proposals/history scoring)
          +-- agents/research_agent.py (Wikipedia API search, owner-reviewed ledger import/export)
          +-- agents/script_agent.py (source-aware notes; optional Groq/Ollama draft)
          +-- agents/groq_client.py (Groq JSON requests; sanitized provider errors)
          +-- media/asset_manager.py (Commons/Pexels/Pixabay video; licensed local audio)
          +-- media/map_animation_engine.py (Natural Earth country zooms, highlights, scene manifests)
          +-- wikimedia.py (shared HTTPS API client, User-Agent, rate limit, bounded downloads)
          +-- media/tts_engine.py (chunked Edge/eSpeak/Piper WAV synthesis, FFprobe checks, measured SRT)
          +-- media/visual_builder.py (original labelled SVG charts)
          +-- media/video_editor.py (video-first FFmpeg timeline, optional music mix, soft SRT)
          +-- media/thumbnail_engine.py (three map-first concepts, heuristic scores, edit recipes)
          +-- media/thumbnail_maker.py (Pillow JPEG and SVG companion)
          +-- quality/qa_engine.py (technical/evidence/rights release gates)
          +-- scheduler/worker.py (sequential offline package and recovery)
          +-- analytics/feedback.py (owner CSV import, descriptive summary)
          +-- publishing/youtube_client.py (deliberately fail-closed)
```

## Persistent model

The database has a schema version (`PRAGMA user_version`) and tables for jobs, topic proposals, job events, research sources, claims, media assets (with `image`, `video`, or `audio` type), approvals, upload attempts, and imported analytics. Foreign keys are enabled. Job transitions are checked centrally. Job creation uses a unique idempotency key. SQLite transactions protect state changes and ledger imports.

Output files are human-editable and stored under `output/<job-id>/`. Approval hashes sorted relative paths and file bytes, excluding only `approval.json`. The database stores the approval digest and the receipt stores the same digest. CLI status, dashboard review, and any upload gate check the digest; a mismatch invalidates the approval. Public publishing is unavailable in this build.

## Workflow boundaries

1. Topic proposals are local scoring seeds, saved for review; they make no factual availability claims.
2. Research leads can be discovered through the public English Wikipedia API. Source title, page URL, publisher, retrieval date, evidence excerpt, and CC BY-SA 4.0 text licence are recorded. API discovery is not fact verification; inspect the article's citations and use independent sources. Hand-imported sources must also state their licence. No general-purpose web scraping is performed.
3. Script notes are evidence-aware. If configured, Groq `llama-3.3-70b-versatile` is preferred; otherwise the local Ollama/manual fallback is used. Groq receives the research evidence and requested prompt, so this is not local-only processing. Narration word counts and claim IDs are validated. Model prose is not proof; a human must verify every claim.
4. Narration supports Edge TTS, eSpeak NG, or Piper. Edge TTS is an online service accessed through a community client; the owner must review the service's current terms and intended use. Piper requires an existing voice file and a non-empty owner-recorded licence; the program cannot validate external voice-model terms. Sentence chunks are checked with FFprobe/FFmpeg for valid decoding and near-silence, joined atomically, and timed into SRT cues from measured durations. A manifest hashes the exact text, WAV, and SRT. Text-only mode is explicit and cannot pass the narration QA gate.
5. Commons images can be searched and downloaded through the public Wikimedia Commons API. Pexels/Pixabay clips can be searched only through their official APIs using owner-supplied keys. Provider results are downloaded only from allowlisted HTTPS API/CDN hosts, capped at 250 MiB, signature checked, and validated with FFprobe. Provider license/creator/source/retrieval/hash/attribution metadata is recorded; owner review of current provider and item terms remains required. Pixabay's public API does not expose a documented music endpoint. Music must be downloaded manually from a source whose licence the owner verifies, then registered with `music-add`; no scraping is performed.
6. FFmpeg places verified, generated Natural Earth map scenes and registered video clips first at their actual durations, then uses licensed stills to cover any remaining narration. It refuses to loop insufficient footage. Ken Burns effects apply only to still-image segments. It encodes H.264/AAC and muxes an SRT subtitle track. One registered background track, if supplied, is mixed at `volume=0.1` (-20 dB) under narration and limited.
7. `map_animation_engine.py` caches the pinned Natural Earth 1:110m Admin 0 Countries 5.1.1 GeoJSON release. Its sidecar records dataset, version, public-domain licence, source, download date, and hash. It renders world-to-country zoom/highlight PNG frames and joins them into H.264 scene segments. Every map carries a de-facto/disputed-status qualification. Routes and markers can only be passed as explicit coordinates and require a recorded source; no statistical overlays or other basemap layers are inferred.
8. `thumbnail_engine.py` composes three visually distinct 1280×720 map-first concepts from the Natural Earth country layer. It writes editable JSON recipes, a contact sheet, a 160×90 mobile preview, and dimension-specific heuristic scores, then selects the highest-scoring concept. Scores are not a guarantee of geographic completeness, audience response, or success. No channel logo or third-party branding is rendered.
9. The original Pillow thumbnail helper remains available for packages without a selected map country.
10. QA probes and decodes final audio/video, checks the audio peak for silence/clipping, duration/resolution/audio/subtitle streams and SRT timing, validates narration manifest hashes, and blocks unsupported/unreviewed claims, unknown asset rights, missing attribution, invalid map metadata, low thumbnail rubric scores, or incomplete package files. Automated QA cannot check every frame, fact, legal right, or platform policy.
11. The dashboard exposes an exact-package approval action with a process-local anti-CSRF token. Approval requires fresh QA and is never inferred from a default or prior artifact.
12. Upload integration is intentionally unavailable. The CLI refuses upload even with a configuration change; OAuth, private-first API upload, schedule/publication workflows, quota handling, and remote status verification need a separate reviewed implementation.
13. CSV analytics are imported from the owner. Reports summarize observations and do not claim causation.

## Recovery and failure behavior

Transient worker states are visible in SQLite. Recovery requeues interrupted local research/script/render steps with incremented attempts. Once the retry limit is reached, the job is failed with an explanation. An interrupted upload has an ambiguous external outcome, so it is never blindly retried. Low disk, missing FFmpeg/eSpeak/Piper/Ollama, invalid rights, invalid URLs, and failed QA surface explicit errors or blocking QA findings.

## Security and privacy

- The dashboard and local model endpoint are restricted to loopback.
- `.env` is not loaded by the application. Provider keys are read from ignored `config.json` or explicitly supported environment variables; dataclass representations and provider errors omit credentials.
- `config.json`, media, database, backups, credentials, and logs are ignored.
- subprocesses use argument arrays, not a shell.
- Rights/source URLs must be HTTPS. Only official provider APIs and allowlisted media hosts are retrieved; no rate-limit or access restrictions are bypassed.
- Approval is content-hash-bound; changed deliverables require renewed approval.
- Never enable external access through a reverse proxy without a separate threat review.
