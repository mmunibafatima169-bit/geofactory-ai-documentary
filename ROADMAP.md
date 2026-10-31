# Implementation roadmap

Status reflects the code in this repository, not a promise of future work.

| Phase | Dependencies | Completion criteria | Status |
|---|---|---|---|
| 1. Repository/machine assessment and architecture | Existing repository, host diagnostics | Preserve useful starter code; record OS, Python, memory, disk, GPU, FFmpeg, Git, Ollama; document safe plan | Complete. Ubuntu 24.04/Python 3.14.2; 7.8 GiB total RAM (~5.3 GiB available at latest check), ~14.2 GiB disk free, CPU-only, FFmpeg/Ollama installed |
| 2. Config, logging, SQLite, queue, CLI | Python 3.11+ | Validated config, schema version, state transitions, idempotency, local diagnostics, tests | Complete for local sequential workflow |
| 3. Topics and source-linked research | SQLite; public Wikipedia API; owner review | Scored/deduplicated proposals; source/claim import; factual claims require source IDs | Partial. Wikipedia API discovery and licence/date recording work; independent-source verification, broader trusted-source discovery, and claim fact-checking remain manual |
| 4. Scripts, claims, scenes | Research ledger; optional Ollama | Original 1,200–1,800-word draft; chapter/scene plan; every material factual claim traceable | Partial. Schema-constrained `qwen2.5:0.5b` inference was tested but returned only 74 narration words after 89.9 seconds on a full-script attempt; it does not meet the length requirement. A manually drafted 1,771-word Iceland narration is source-linked, but all 11 factual claims remain unreviewed and the 2025 energy figures need verification. Keep Ollama disabled for script generation until it can reliably meet the acceptance checks |
| 5. TTS and subtitles | FFmpeg/FFprobe; locally installed eSpeak NG, or a separately verified Piper voice | Chunked local narration; measured audio; silence/decode checks; SRT timed from measured audio | Implemented and tested with eSpeak NG. Piper Lessac model was rejected because its dataset terms exclude commercial use; no Piper voice model was downloaded. TTS recovery is per-command atomic output, not resumable per-chunk state |
| 6. Rights-aware assets and visuals | Commons API; owner review | Records, hash/attribution, reusable images/maps/charts | Partial. Commons search/download and licence metadata gates, manual local registration, and original SVG chart; no authoritative maps or independent legal verification |
| 7. Video and thumbnail | FFmpeg/FFprobe; registered rights-cleared stills/audio | Playable 16:9 H.264, audio-synced still motion, soft subtitles, original thumbnail | Implemented Ken Burns still rendering, measured narration duration, AAC audio, MP4 soft subtitles, and a 1280x720 photo-backed JPEG thumbnail. The real Iceland package rendered to a 711.567-second 1280x720 H.264/AAC MP4 with soft subtitles; FFprobe and decode checks passed. 1280x720 is the CPU fallback |
| 8. QA and approval dashboard | Rendered package | Automated blockers, preview/ledgers, approve/reject/change; exact-version approval | Partial. Local queue and hash-bound approval implemented; full editorial/frame/policy checks remain manual |
| 9. YouTube OAuth publishing | Official API review, credentials, quota/legal review | OAuth, private-first upload, exact approval, explicit visibility, status checks | Not implemented. Publishing is disabled and the client fails closed |
| 10. Scheduling, restart recovery, analytics | Persistent queue and owner analytics | Safe restart, bounded retry, pause/resume, supported analytics | Partial. SQLite state/recovery, manual sequential worker, backup, CSV import; no auto scheduler or OAuth analytics |
| 11. End-to-end sample and failure testing | Optional media tools/models; Wikimedia APIs | Playable 8–15-minute sample; restart/approval/render tests | Partial. Live Wikipedia research and licensed Commons downloads completed. The Iceland package has 1,771 narration words, 711.5 seconds of eSpeak NG audio, a 1280x720 MP4, valid subtitles, metadata, attribution, and a photo-backed thumbnail. QA confirms technical media checks pass but correctly blocks approval on 11 unreviewed factual claims. A small Ollama prompt took 29.1 seconds; the full-script attempt took 89.9 seconds and failed the word-count check without exhausting memory. All 28 unit/integration tests pass, covering TTS, silence rejection, rendering, thumbnail output/failure recovery, claim-review gating, and Wikimedia rights checks |

## Known blockers and next acceptance work

- A commercially appropriate Piper voice has not been established. Use the installed eSpeak NG fallback unless voice rights are independently cleared.
- Add independent authoritative sources beyond Wikipedia and validate source facts against their citations.
- Ollama and `qwen2.5:0.5b` are installed. Inference was tested, but the model did not generate a valid-length script; the documented manual fallback stays active.
- Implement stronger editorial/factual checks and human review of maps, labels, subtitles, and full-length video.
- Implement YouTube only in a separate change with OAuth consent, official API policy/quota review, private-first semantics, idempotent upload verification, and explicit release approval.
- Add migrations for future schema versions before changing the deployed schema.
- Test interruption during actual full-duration FFmpeg rendering on Windows and Linux.

The demo is intentionally not an example of real-world geography; it cannot pass approval without replacing the synthetic placeholders.
