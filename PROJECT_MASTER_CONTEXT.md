# GeoFactory AI Documentary --- Complete Project Handoff

**Purpose:** A single, AI-readable project brief covering the original
project goals, repository work, production architecture, sample-video
reviews, decisions, constraints, and next steps.

**Last updated:** 10 November 2026  
**Project repository:**
https://github.com/mmunibafatima169-bit/geofactory-ai-documentary  
**Primary workflow:** GitHub repository + local Python-based production
pipeline  
**Target channel:** Geography and country documentaries for a primarily
US audience  
**Target video length:** Approximately 8--15 minutes for standard
documentaries  
**Production goal:** Highly automated, professional documentary
production with final human approval before publishing.

> **Important evidence note:** This document consolidates information
> from the available project conversations and prior handoff context. It
> distinguishes user decisions, previously reported repository
> capabilities, recommendations, and items that still require direct
> verification. Do not treat a previous assistant's description as proof
> that a feature is currently implemented or working. The actual
> repository, latest source code, logs, and rendered media are
> authoritative.

---

# 1. Project vision and objective

Build a mostly automated YouTube documentary production system that can
operate like a production agent:

1. Discover and select suitable documentary topics.
2. Research topics and collect credible sources.
3. Create engaging, original documentary scripts.
4. Fact-check important claims, dates, figures, and statistics.
5. Generate natural narration.
6. Plan visuals based on the meaning of each narration segment.
7. Acquire suitable legal/licensed stock footage and images.
8. Generate maps, charts, timelines, 2D motion graphics, and selected
   3D/technical animations.
9. Assemble and edit the documentary programmatically.
10. Create thumbnails, titles, descriptions, chapters, and Shorts.
11. Run technical, editorial, audio, and factual quality checks.
12. Present the finished video and report for human review.
13. Publish or schedule only after explicit human approval.

The desired result is a dependable, repeatable pipeline rather than a
one-off video generator.

## Quality ambition

The target is to approach the storytelling clarity, visual variety, map
quality, pacing, and production polish of leading geography documentary
channels such as **RealLifeLore**.

This is a quality reference only. The project must create original
scripts, research, graphics, animations, and editing. Do not copy
protected videos, scripts, branding, thumbnails, or assets.

## Human approval rule

The system may automate preparation and production, but it must stop
before public publishing and request human approval. Never upload,
schedule, publish, commit, push, deploy, or spend money without the
user's explicit approval for that action.

---

# 2. User's working preferences and constraints

These are project requirements, not optional suggestions:

- The user is not an experienced programmer and needs clear,
  step-by-step instructions.
- Prefer complete copy-paste prompts that can be handed to an AI
  coding agent.
- When giving advice, provide the technical details and a ready-to-use
  agent prompt together.
- Explain commands simply and specify exactly where to run them.
- Prefer free and open-source tools wherever practical; initial budget
  preference is ₹0.
- The user works on a laptop/PC and also uses an Android phone.
- The user wants very little manual work: monitor the process and
  approve the final output.
- The user has specified: **GitHub is the project workflow; Python is
  the final editing/orchestration environment.**
- Preserve existing working code and features. Audit before changing
  anything.
- Do not rebuild the repository from scratch unless there is
  compelling evidence and the user approves.
- Do not install packages or applications merely because they sound
  useful.
- Do not use fake placeholders or claim a feature works when it has
  not been tested.
- Do not expose API keys, tokens, passwords, OAuth secrets, or other
  credentials in source code, reports, logs, screenshots, or Git
  history.
- Local automation cannot run while the laptop is off or asleep; do
  not imply that local jobs run continuously in that state.
- The user wants final, actual rendered evidence---not just code or an
  agent's statement that a task is complete.

## Prompt delivery convention

Whenever recommending an installation, code change, architecture
decision, important rule, or next action, provide a single complete
copyable instruction block for the AI coding agent. Include: - objective
and reason; - current-state audit requirement; - exact proposed
changes; - tools/dependencies and installation commands only if
needed; - compatibility and preservation rules; - implementation
order; - tests and evidence required; - explicit stop/approval
conditions.

---

# 3. Repository and project setup

## Repository

`https://github.com/mmunibafatima169-bit/geofactory-ai-documentary`

The repository was downloaded locally and work was carried out in the
existing project rather than starting a new project.

## Environment details previously reported

The following were mentioned in earlier project conversations and must
be rechecked on the actual machine before relying on them:

- Windows laptop/PC environment.
- Git installed.
- Python 3.12 and a project `.venv` were previously reported.
- FFmpeg/FFprobe were previously reported as installed.
- A later conversation mentioned a different Python
  installation/version in another setup. Therefore, do not assume the
  active interpreter is Python 3.12. Verify the interpreter used by
  the repository.
- The user had installed/downloaded a YouTube Agentic AI
  Studio-related tool during an earlier setup, but its current
  role/status is not established here.

## Previously identified repository files

These paths were reported in prior repository inspection. Confirm they
still exist and inspect their current contents before modifying:

- `geofactory/media/video_editor.py`
- `geofactory/media/map_animation_engine.py`
- `geofactory/media/visual_builder.py`
- `geofactory/media/asset_manager.py`
- `geofactory/media/thumbnail_engine.py`
- `geofactory/quality/qa_engine.py`
- `geofactory/agents/script_agent.py`
- `geofactory/core/config.py`
- `tests/`
- `README.md`

Other repository folders/files may exist. Do not assume this list is
complete.

## Previously reported existing capabilities

Prior assistant/repository discussion described these as already present
or partially present:

- Python-based orchestration and video rendering.
- FFmpeg/FFprobe media handling.
- Ken Burns-style pan/zoom.
- Natural Earth-based animated country maps.
- Basic SVG charts/visuals.
- Pexels/Pixabay media integration.
- Narration and subtitle handling.
- Background music mixing.
- Thumbnail concept/generation workflow.
- QA checks.
- Human approval step.

**Verification requirement:** These are reported capabilities, not a
guarantee that each works in the current checkout. Inspect the
implementation and run it. Mark each as `VERIFIED`,
`PARTIALLY VERIFIED`, `NOT VERIFIED`, or `NOT PRESENT`.

---

# 4. Project history and decisions

## Early project planning

The initial goal was a machine-like geography/country documentary
channel where AI agents perform most of the workflow, from topic
selection and research through script, voice, visuals, editing,
thumbnail, metadata, and quality control.

The user wanted a copy-paste roadmap that an AI coding agent could use
against a public GitHub repository. The workflow should be
free/open-source where possible, and a human approval step is mandatory
before publishing.

A prior proposed workflow included:

`topic discovery → research → script → fact-check → narration → visual planning/assets → maps/graphics → render → thumbnail/SEO → QA → human approval → optional upload`

A possible initial local stack discussed included Python, Ollama for
local language-model tasks, Piper TTS, FFmpeg, SQLite,
licensed/Wikimedia-compatible media sources, Windows Task Scheduler, and
YouTube Data API/OAuth. These were architectural suggestions, not all
confirmed as installed or integrated. Reassess current model quality,
licensing, hardware capability, and actual repository needs before
adopting them.

## Existing repository upgrade strategy

The key decision was to upgrade the existing GeoFactory repository, not
replace it.

High-impact improvement areas previously identified: - narration-aware
scene selection; - visual relevance scoring; - more variety between
footage and graphics; - duplicate/repeated shot detection; - stronger
map animation; - cinematic transitions and camera movement; - 2.5D
parallax/depth; - better charts, timelines, labels, and infographics; -
engineering/technical explanatory animation; - narration-aware timing; -
voice processing, music ducking, and sound design; - frame-level
inspection and automated QA.

## Production architecture discussed

The recommended division of responsibilities was:

| Component | Intended responsibility | Status |
|---|---|---|
| Python | Main controller, agents, scene planning, pipeline orchestration | Core project choice |
| Remotion | Rich motion graphics, animated typography, compositions, transitions | Recommended integration; verify actual usage |
| Manim Community | Precise technical/scientific/math diagrams and explanatory animations | Optional/specific use; verify actual usage |
| Blender | Selective 3D terrain, structures, water, engineering cutaways | Optional/selective; verify installation and actual renders |
| FFmpeg | Final assembly, audio mix, encoding, media processing | Existing/reported core dependency |
| n8n | Optional external workflow orchestration | Not required for current visual-quality work |
| Google Flow | Optional cinematic AI-generated video clips | Separate creative asset source; not a replacement for editing |
| Stock providers | Relevant legal/licensed real-world footage and imagery | Existing Pexels/Pixabay integration reported; verify terms and implementation |

Do not install all tools automatically. First determine whether a given
tool is needed for a specific scene or capability and whether the
current hardware and project environment can support it.

### Why this architecture

- Python remains the central workflow and editing controller.
- Remotion can handle polished, repeatable 2D motion-graphics
  compositions.
- Manim is best reserved for technical/scientific explanations where
  its strengths matter.
- Blender should be used selectively when a real 3D scene materially
  improves understanding.
- FFmpeg remains the final assembly and encoding tool.
- Real footage, maps, charts, and animations should be mixed according
  to the narration---not used as repetitive decoration.

### Useful official references

- Remotion: https://www.remotion.dev/
- Remotion documentation: https://www.remotion.dev/docs/
- Remotion GitHub: https://github.com/remotion-dev/remotion
- Manim Community: https://www.manim.community/
- Manim documentation: https://docs.manim.community/
- Blender Python API: https://docs.blender.org/api/current/
- FFmpeg: https://ffmpeg.org/
- Google Flow: https://labs.google/fx/tools/flow
- n8n documentation: https://docs.n8n.io/

Licensing and pricing can change. Verify the current license and usage
terms before production or commercial use. Do not assume a tool is free
for every scale or type of use.

---

# 5. Earlier video audit and lessons

An earlier documentary sample was reviewed. The previous review
described an approximately 8:14 video at 1280×720, 25 FPS, with mono
22.05 kHz audio. It identified strengths in storytelling/script
foundation and weaknesses in visual storytelling, animation, geography
presentation, editing, and audio polish.

The previous review's subjective scores and specific factual statements
should not be treated as independently verified facts. Reinspect the
actual video and sources if those claims are important.

The review led to these lessons: - Avoid holding static visuals for too
long. - Use maps to explain geography rather than merely decorate. -
Match visuals to the exact narration segment. - Use a better balance of
real footage, maps, graphics, and technical animations. - Do not rate a
thumbnail if no thumbnail file has been supplied. - Inspect actual
audio; technical metadata alone does not establish voice quality. - A
successful render does not automatically mean a professionally edited
documentary.

---

# 6. First multi-engine sample decision

After an update, the AI coding agent asked the user to choose: - (a)
build a 60-second multi-engine sample assembler; - (b) push the current
commit to GitHub; - (c) do both.

The user was advised to choose **(a), sample first**. GitHub push was
deferred until the sample had been rendered and inspected. The user was
specifically instructed not to allow an automatic push without explicit
approval.

The agent was given instructions to: - audit current implementation and
dependencies; - preserve existing code; - use Python orchestration,
Remotion motion graphics, Manim technical animations, Blender
selectively, and FFmpeg final assembly; - create a 60-second geography
documentary sample; - include a cinematic opening, animated map, camera
movement/zoom, motion graphics/transitions, charts, at least one
technical explanation, narration synchronization, music/SFX, and
subtitles; - target 1080p, 16:9, 30 FPS if supported by the actual
environment; - render and inspect the actual output; - report changed
files, dependencies, tests, and exact output path; - never push without
approval.

---

# 7. 60-second sample: first review

A 60-second sample was uploaded in the conversation and reviewed. The
review described the sample as a meaningful improvement in design
direction.

The sample was reported as: - 1920×1080 (1080p); - 30 FPS; - 60
seconds; - stereo audio at 48 kHz; - rendered using Remotion 4.0.541.

The visual review discussed: - dark navy / gold / white visual
identity; - world map opening and geographic focus; - Venice lagoon and
inlet explanation; - wooden-pile engineering cross-section; - statistics
and chart sequence; - MOSE flood barrier explanation; - map-based
ending.

The prior review gave approximate subjective assessments: - visual
design: 8/10; - geography graphics: 8/10; - typography: 8/10; -
infographics: 7/10; - scene variety: 6/10; - cinematic storytelling:
6/10; - technical output: 9/10.

These scores are indicative editorial opinions, not objective test
results. The previous response also used example reference images; those
reference images were not frames extracted from the user's video. Do not
confuse reference images with video evidence.

### Issues flagged in the sample review

1. More real-world cinematic footage, aerial shots, and environmental
   visuals may be needed to balance graphics.
2. Some scenes may need stronger meaningful camera movement,
   transitions, and layered motion.
3. The chart showed 241 cm and 300 cm at different points. This might
   be an intentional animated transition, but the values must be
   checked against the actual narration and reliable sources.
4. The review did not establish a complete factual audit or audio
   listening test.

---

# 8. Improvement prompt already given to the agent

The agent was asked to improve the existing system without rebuilding
it. The requirements included:

## Visual storytelling

Select the visual format based on narration meaning: - real cinematic
footage; - aerial/satellite imagery; - animated maps; - 2D motion
graphics; - selective 3D scenes; - charts and statistical
infographics; - historical/archive visuals; - technical diagrams.

Avoid repeating the same visual treatment.

## Animation

Improve: - smooth camera movement and parallax; - map zooms and
geographic transitions; - animated labels/callouts; - shape morphing and
infographic transitions; - layered motion graphics; - depth, lighting,
and shadows where appropriate; - scene-specific transitions; -
narration-synchronized animation.

Animations must communicate information, not merely decorate the screen.

## Footage and assets

Integrate suitable legal/free stock sources and improve: - footage
relevance scoring; - duplicate-shot detection; - visual variety; -
aspect-ratio checks; - resolution checks; - asset source/licensing
tracking.

Do not assume an asset is legally reusable just because it is accessible
online.

## Fact-checking

- Verify statistics against reliable sources.
- Store source URLs and access dates.
- Detect conflicting numbers.
- Match displayed numbers to narration.
- Never invent statistics.
- Flag unverified claims for human approval.
- Specifically investigate the 241 cm and 300 cm values.

## Audio

- Synchronize animations with narration.
- Improve music ducking.
- Balance narration, music, and SFX.
- Add subtle, relevant sound design.
- Maintain consistent loudness.
- Detect silence, clipping, and abrupt transitions.

## QA

Check: - resolution/FPS; - black frames and frozen scenes; - repeated
visuals; - subtitle timing; - audio/video sync; - incorrect/inconsistent
text; - missing assets; - render errors; - factual verification flags.

---

# 9. Current delivery-report request

The user wanted all proof in one file/package so ChatGPT could read it,
instead of asking the agent for separate reports.

The agent was instructed to create these deliverables:

## Main report

`FINAL_DELIVERY_REPORT.md`

Expected sections: 1. Executive summary. 2. Latest rendered video
metadata and exact path. 3. Before/after comparison. 4. Complete
repository changes (modified/new/deleted files and Git diff summary). 5.
Installed tools and dependencies with versions and install commands. 6.
Actual engine usage evidence for Python, Remotion, Manim, Blender, and
FFmpeg. 7. Video QA results. 8. Factual accuracy and sources, including
241 cm and 300 cm. 9. Visual evidence. 10. Test results. 11. Final
assessment. 12. Recommended next steps.

## Evidence folder

`delivery_evidence/`

Expected evidence: - representative frame contact sheet; - screenshots
of important animations; - QA logs; - FFprobe metadata; - render logs; -
before/after frame comparisons where available.

## ZIP package

`DELIVERY_BUNDLE.zip`

Expected to contain the Markdown report and evidence folder. The MP4 may
be included if size is reasonable; otherwise the report must state the
exact MP4 path.

## Required safety and integrity rules

- Preserve previous video and working code.
- Do not push, commit, or deploy.
- Never expose credentials.
- Do not invent test results, timestamps, sources, or versions.
- Mark untested checks as `NOT TESTED`.
- Distinguish code presence from tested functionality.
- Avoid unnecessary package installation.
- Do not overwrite the earlier sample.
- Provide exact paths and a summary of failed/untested checks.

The user was then told that these files should be created in the
repository root, for example:

```text
geofactory-ai-documentary/
├── FINAL_DELIVERY_REPORT.md
├── DELIVERY_BUNDLE.zip
├── delivery_evidence/
│   ├── contact_sheet.jpg
│   ├── ffprobe_metadata.txt
│   ├── qa_report.txt
│   └── render_logs.txt
└── ...existing project files
```

The agent was asked to provide downloadable attachments or direct links
in its chat, not just filenames. These files have not yet been received
in this conversation as of this handoff.

---

# 10. Latest uploaded media

A video attachment was uploaded in this conversation: - Attachment
filename: `1000274196.mp4` - Runtime path in the original environment:
`/mnt/data/1000274196.mp4`

This is an uploaded video artifact, not proof that the complete delivery
report, ZIP, or QA evidence has been created. The exact relationship
between this file and the agent's latest render should be confirmed by
metadata and the agent's report.

Do not infer a different filename or reuse a sandbox link from another
session. If inspecting this media in a future session, use the actual
available attachment/path and verify it.

---

# 11. What has NOT yet been confirmed

The following must remain open until evidence is provided:

- Whether the latest improvement pass was actually implemented in
  code.
- Whether a new post-upgrade MP4 was rendered.
- Whether the latest MP4 differs materially from the earlier 60-second
  sample.
- Whether Manim actually rendered any scene.
- Whether Blender actually rendered any scene.
- Whether Remotion was used beyond the previously reported sample.
- Whether FFmpeg assembled the final deliverable.
- Whether all dependencies are installed and compatible.
- Whether the 241 cm and 300 cm values are factually correct and
  correctly represented.
- Whether QA checks were executed and passed.
- Whether `FINAL_DELIVERY_REPORT.md` exists.
- Whether `DELIVERY_BUNDLE.zip` exists.
- Whether the contact sheet, logs, metadata, and screenshots exist.
- Whether any tests failed or were skipped.
- Whether the latest video is ready for a full editorial review.
- Whether the repository has uncommitted changes or commits awaiting
  approval.

Never turn an unknown item into a success claim.

---

# 12. Recommended next workflow

Follow this sequence. Do not skip ahead.

## Step 1 --- Get the delivery package from the coding agent

Ask the agent to confirm and attach: - `FINAL_DELIVERY_REPORT.md` -
`DELIVERY_BUNDLE.zip` - latest rendered MP4

Ask for exact repository paths and downloadable attachments. No GitHub
push is required to share local files.

## Step 2 --- Review the report and evidence

Read the Markdown report and inspect the ZIP contents. Verify: - source
file paths and changes; - dependency versions; - commands and logs; -
actual engine use; - QA results; - factual sources; - video metadata.

A report is not proof by itself: cross-check important claims against
logs, code, and the MP4.

## Step 3 --- Inspect the latest video

Review: - opening hook; - story structure and pacing; - scene-by-scene
visual relevance; - map accuracy and legibility; - animation
smoothness; - footage variety; - chart accuracy; - subtitles; - voice
and music balance; - transitions; - ending.

If needed, extract a contact sheet and inspect specific
frames/timestamps.

## Step 4 --- Classify the result

Use three outcomes: - `PASS`: required work was implemented and evidence
supports it. - `PARTIAL PASS`: some work is complete, but important
requirements remain. - `FAIL`: the output or implementation does not
meet the requirements, or evidence is insufficient for a pass.

Distinguish a technical pass from an editorial-quality pass.

## Step 5 --- Only then decide on GitHub

If the changes are verified: - review `git status`; - inspect
`git diff`; - inspect untracked files; - check for secrets; - run
tests; - create a commit only with approval; - push only with explicit
approval.

Do not push tokens or secrets. Do not let an agent use an old token
simply because it appears to still work.

## Step 6 --- Continue incremental improvements

Use measured weaknesses from the review. Avoid adding more engines or
packages without a specific requirement. Keep the current workflow
stable and improve one high-impact area at a time.

---

# 13. Standard instruction for future AI coding agents

Use the following as the standing project rule:

> You are working on the existing GeoFactory AI Documentary repository.
> First inspect the actual current repository, environment, tests, and
> existing implementation. Do not assume that previous reports are
> accurate or current.
>
> Preserve working code and architecture. Python remains the main
> controller and final editing/orchestration environment. Keep FFmpeg
> for final media assembly/encoding. Use Remotion, Manim, and Blender
> only where they add a demonstrated benefit and are compatible with the
> current environment.
>
> Before installing anything, explain why it is required, whether an
> equivalent already exists, its license/cost implications,
> compatibility, and exact installation command. Do not install
> unnecessary tools.
>
> Make changes incrementally. Do not use placeholders. Do not claim a
> feature works until it has been executed and tested. Render a real
> sample and inspect it. Keep prior samples for comparison.
>
> For every task, provide one complete Markdown delivery report with
> changed files, dependencies and versions, exact commands, tests, QA
> results, evidence paths, known limitations, and the exact rendered
> output path.
>
> Never expose credentials. Never commit, push, deploy, upload, or
> publish without explicit user approval. Stop and ask for approval
> before any irreversible or externally visible action.

---

# 14. Quick project status snapshot

| Area | Current consolidated status |
|---|---|
| Project goal and target audience | Defined |
| Repository selected | Defined |
| Python as final editing/orchestration | User-confirmed |
| Existing repository audit | Previously discussed; recheck current state |
| FFmpeg pipeline | Previously reported; recheck |
| Remotion sample | A 60-second sample was reported as rendered |
| Manim integration | Not yet independently confirmed |
| Blender integration | Not yet independently confirmed |
| Cinematic footage improvements | Needs evidence from latest render |
| Narration-aware scene selection | Improvement requested; implementation unconfirmed |
| Factual QA | Requested; latest results unconfirmed |
| Audio QA | Requested; latest results unconfirmed |
| Contact sheet/logs/metadata | Requested; receipt unconfirmed |
| `FINAL_DELIVERY_REPORT.md` | Requested; receipt unconfirmed |
| `DELIVERY_BUNDLE.zip` | Requested; receipt unconfirmed |
| Latest post-upgrade video | Attachment exists, identity/version to confirm |
| GitHub push | Not approved; do not push |
| Public publishing | Human approval required |

---

# 15. The immediate next action

**Do not install more tools or start another major upgrade yet.**

First obtain the complete delivery package from the coding agent: 1.
`FINAL_DELIVERY_REPORT.md` 2. `DELIVERY_BUNDLE.zip` 3. latest rendered
MP4

Upload those files in ChatGPT. The next review should cross-check the
report, ZIP evidence, source changes, test logs, and actual video, then
give a clear `PASS / PARTIAL PASS / FAIL` verdict and one consolidated
copy-paste prompt for the next improvement.

---

**End of project handoff.**
