#!/usr/bin/env python3
"""Assemble the 60-second multi-engine documentary sample.

Python orchestration layer:
  1. synthesise narration per scene (Edge TTS, local fallback)
  2. fit each narration take into its scene slot (pad / gentle atempo)
  3. generate an original music bed and transition whooshes with FFmpeg
     (synthesised in-process — no third-party audio licensing)
  4. cross-fade the engine-rendered scene videos (xfade)
  5. mix narration + ducked music + sfx, normalise loudness
  6. build a timeline-accurate SRT and mux it as a soft subtitle track

Engines consumed here: Remotion (motion graphics scenes), optionally
Blender/Manim segments if present; FFmpeg performs the final assembly.

Usage:
    python3 studio/assemble_sample60.py [--scenes DIR] [--out FILE]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TOOLS = REPO / ".tools"
FFMPEG = str(TOOLS / "ffmpeg") if (TOOLS / "ffmpeg").exists() else "ffmpeg"
FFPROBE = str(TOOLS / "ffprobe") if (TOOLS / "ffprobe").exists() else "ffprobe"

FPS = 30
WIDTH, HEIGHT = 1920, 1080
XFADE = 0.5           # seconds of cross-dissolve between scenes
VOICE = "en-US-GuyNeural"


@dataclass
class Scene:
    scene_id: str
    composition: str
    seconds: float
    narration: str
    engine: str = "remotion"
    sfx: str | None = None


SCENES: list[Scene] = [
    Scene("sc-001", "S1ColdOpen", 8.433333333333334,
          "Venice is sinking. The most beautiful city ever built on water is "
          "slowly losing its fight against the sea.", sfx="sting"),
    Scene("sc-002", "S2LagoonMap", 10.433333333333334,
          "It sits inside a shallow lagoon on Italy's Adriatic coast, spread across "
          "more than a hundred islands, with three narrow inlets connecting it to the open sea.",
          sfx="whoosh"),
    Scene("sc-003", "S3Foundations", 12.4,
          "Beneath the stone, millions of wooden piles were driven down through mud and clay "
          "into a firmer layer. Starved of oxygen under the water, the timber never rotted. "
          "It hardened instead.", sfx="whoosh"),
    Scene("sc-004", "S4Stats", 12.4,
          "But the sediment keeps compacting. Industrial groundwater pumping accelerated the "
          "sinking until the nineteen seventies. In nineteen sixty-six, a record surge reached "
          "one hundred and ninety-four centimetres.", sfx="whoosh"),
    Scene("sc-005", "S5Mose", 10.433333333333334,
          "So Italy built MOSE: seventy-eight hollow steel gates that rest on the seabed, then "
          "swing upward on compressed air to lock the Adriatic out.", sfx="whoosh"),
    Scene("sc-006", "S6Closing", 8.4,
          "The shield works. But Venice still sinks, the sea still rises, and this city is only "
          "the first of many.", sfx="sting"),
]


def run(cmd: list[str], timeout: int = 1800) -> subprocess.CompletedProcess:
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"command failed ({proc.returncode}): {' '.join(cmd[:6])}…\n{proc.stderr[-700:]}")
    return proc


def probe_duration(path: Path) -> float:
    out = run([FFPROBE, "-v", "error", "-show_entries", "format=duration",
               "-of", "default=nw=1:nk=1", str(path)]).stdout.strip()
    return float(out)


# ------------------------------------------------------------------ #
# 1. narration                                                        #
# ------------------------------------------------------------------ #
async def _edge_tts(text: str, destination: Path) -> bool:
    try:
        import edge_tts
    except ImportError:
        return False
    try:
        communicate = edge_tts.Communicate(text, VOICE)
        await communicate.save(str(destination))
        return destination.is_file() and destination.stat().st_size > 2048
    except Exception:
        return False


def synthesise(text: str, destination: Path, attempts: int = 3) -> str:
    """Return the backend that produced audio; reuse valid cached takes."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.is_file() and destination.stat().st_size > 4096:
        return "cached-reviewed-take"
    mp3 = destination.with_suffix(".mp3")
    for _ in range(attempts):
        if asyncio.run(_edge_tts(text, mp3)):
            run([FFMPEG, "-y", "-v", "error", "-i", str(mp3), "-ac", "1", "-ar", "48000", str(destination)])
            mp3.unlink(missing_ok=True)
            return "edge-tts"
    espeak = shutil.which("espeak-ng") or str(TOOLS / "espeak-ng")
    if Path(espeak).exists():
        run([espeak, "-v", "en-us", "-s", "150", "-w", str(destination), text])
        return "espeak-ng"
    raise RuntimeError("No TTS backend produced narration audio")


def fit_audio(source: Path, target_seconds: float, destination: Path,
              head_pad: float = 0.35) -> None:
    """Fit a narration take into its scene slot: small head pad, gentle tempo
    correction when slightly long, silence padding when short."""
    duration = probe_duration(source)
    usable = max(0.5, target_seconds - head_pad - 0.15)
    filters = [f"adelay={int(head_pad * 1000)}|{int(head_pad * 1000)}"]
    if duration > usable:
        tempo = min(1.18, duration / usable)       # keep it natural: ≤ 1.18×
        filters.append(f"atempo={tempo:.4f}")
    filters.append(f"apad=whole_dur={target_seconds:.3f}")
    filters.append(f"atrim=0:{target_seconds:.3f}")
    # Micro-fades eliminate hard waveform cuts at scene/cross-fade boundaries.
    filters.append("afade=t=in:st=0:d=0.035")
    filters.append(f"afade=t=out:st={max(0.0, target_seconds - 0.14):.3f}:d=0.14")
    run([FFMPEG, "-y", "-v", "error", "-i", str(source),
         "-af", ",".join(filters), "-ac", "1", "-ar", "48000", str(destination)])


# ------------------------------------------------------------------ #
# 2. original score + sfx (synthesised, no third-party audio)         #
# ------------------------------------------------------------------ #
def make_music_bed(total: float, destination: Path) -> None:
    """Original ambient bed: three detuned sine pads + slow tremolo, low-passed."""
    expr = (
        f"sine=frequency=110:duration={total:.2f}:sample_rate=48000[a];"
        f"sine=frequency=164.81:duration={total:.2f}:sample_rate=48000[b];"
        f"sine=frequency=220:duration={total:.2f}:sample_rate=48000[c];"
        "[a]volume=0.5[a1];[b]volume=0.32[b1];[c]volume=0.18[c1];"
        "[a1][b1][c1]amix=inputs=3:normalize=0,"
        "tremolo=f=0.18:d=0.35,"
        "lowpass=f=900,"
        "aformat=channel_layouts=mono,"
        f"afade=t=in:st=0:d=2.5,afade=t=out:st={max(0.0, total - 3.0):.2f}:d=3.0"
        "[out]"
    )
    run([FFMPEG, "-y", "-v", "error", "-filter_complex", expr, "-map", "[out]",
         "-ar", "48000", "-ac", "1", str(destination)])


def make_sfx(kind: str, destination: Path) -> None:
    """Original transition sounds: filtered noise sweep / low sine sting."""
    if kind == "whoosh":
        expr = (
            "anoisesrc=d=0.9:c=pink:r=48000:a=0.5,"
            "highpass=f=300,lowpass=f=5200,"
            "afade=t=in:st=0:d=0.35,afade=t=out:st=0.4:d=0.5,"
            "volume=0.5"
        )
    else:  # sting
        expr = (
            "sine=frequency=74:duration=1.4:sample_rate=48000,"
            "afade=t=in:st=0:d=0.05,afade=t=out:st=0.3:d=1.1,"
            "volume=0.85"
        )
    run([FFMPEG, "-y", "-v", "error", "-filter_complex", f"{expr}[out]",
         "-map", "[out]", "-ar", "48000", "-ac", "1", str(destination)])


# ------------------------------------------------------------------ #
# 3. subtitles                                                        #
# ------------------------------------------------------------------ #
def srt_timestamp(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _caption_chunks(text: str, max_chars: int = 84) -> list[str]:
    """Sentence/clause-aware subtitle chunks that remain readable in two lines."""
    clauses = [part.strip() for part in re.split(r"(?<=[.!?;:])\s+|(?<=,)\s+", text) if part.strip()]
    chunks: list[str] = []
    for clause in clauses:
        if len(clause) <= max_chars:
            chunks.append(clause)
            continue
        words = clause.split()
        current: list[str] = []
        for word in words:
            candidate = " ".join([*current, word])
            if current and len(candidate) > max_chars:
                chunks.append(" ".join(current))
                current = [word]
            else:
                current.append(word)
        if current:
            chunks.append(" ".join(current))
    return chunks


def write_srt(starts: list[float], destination: Path) -> None:
    """Readable clause-level cues, timed proportionally inside each scene slot."""
    lines: list[str] = []
    index = 1
    for scene, start in zip(SCENES, starts, strict=True):
        captions = _caption_chunks(scene.narration)
        weights = [max(1, len(s)) for s in captions]
        total_w = sum(weights)
        speech_start = start + 0.35
        speech_span = scene.seconds - 0.5
        cursor = speech_start
        for caption, weight in zip(captions, weights, strict=True):
            span = speech_span * weight / total_w
            lines.append(str(index))
            lines.append(f"{srt_timestamp(cursor)} --> {srt_timestamp(cursor + span - 0.05)}")
            lines.append(caption)
            lines.append("")
            index += 1
            cursor += span
    destination.write_text("\n".join(lines), encoding="utf-8")


# ------------------------------------------------------------------ #
# 4. assembly                                                         #
# ------------------------------------------------------------------ #
def build(scene_dir: Path, work: Path, out_file: Path) -> dict:
    work.mkdir(parents=True, exist_ok=True)
    report: dict = {"scenes": [], "engines": {}, "warnings": []}

    clips: list[Path] = []
    for scene in SCENES:
        clip = scene_dir / f"{scene.composition}.mp4"
        if not clip.is_file():
            raise FileNotFoundError(f"Missing rendered scene: {clip}")
        clips.append(clip)
        report["engines"][scene.scene_id] = scene.engine

    # ---- narration ------------------------------------------------ #
    backends: set[str] = set()
    fitted: list[Path] = []
    for scene in SCENES:
        raw = work / f"{scene.scene_id}.raw.wav"
        fit = work / f"{scene.scene_id}.fit.wav"
        backends.add(synthesise(scene.narration, raw))
        fit_audio(raw, scene.seconds, fit)
        fitted.append(fit)
        report["scenes"].append({
            "scene_id": scene.scene_id,
            "composition": scene.composition,
            "engine": scene.engine,
            "seconds": scene.seconds,
            "narration_raw_s": round(probe_duration(raw), 3),
        })
    report["tts_backends"] = sorted(backends)

    # scene start times on the cross-faded timeline
    starts: list[float] = []
    cursor = 0.0
    for scene in SCENES:
        starts.append(cursor)
        cursor += scene.seconds - XFADE
    total = cursor + XFADE
    report["total_seconds"] = round(total, 3)

    # ---- narration track ------------------------------------------ #
    narration_track = work / "narration_track.wav"
    inputs: list[str] = []
    filters: list[str] = []
    for index, (fit, start) in enumerate(zip(fitted, starts, strict=True)):
        inputs.extend(["-i", str(fit)])
        filters.append(f"[{index}:a]adelay={int(start * 1000)}|{int(start * 1000)}[n{index}]")
    mix = "".join(f"[n{i}]" for i in range(len(fitted)))
    filters.append(f"{mix}amix=inputs={len(fitted)}:normalize=0:dropout_transition=0[nout]")
    run([FFMPEG, "-y", "-v", "error", *inputs, "-filter_complex", ";".join(filters),
         "-map", "[nout]", "-ar", "48000", "-ac", "1", str(narration_track)])

    # ---- music + sfx ---------------------------------------------- #
    music = work / "music_bed.wav"
    make_music_bed(total, music)
    whoosh, sting = work / "sfx_whoosh.wav", work / "sfx_sting.wav"
    make_sfx("whoosh", whoosh)
    make_sfx("sting", sting)

    sfx_inputs: list[str] = []
    sfx_filters: list[str] = []
    sfx_labels: list[str] = []
    for index, (scene, start) in enumerate(zip(SCENES, starts, strict=True)):
        if not scene.sfx:
            continue
        source = sting if scene.sfx == "sting" else whoosh
        at = max(0.0, start - 0.18)
        sfx_inputs.extend(["-i", str(source)])
        label = f"s{len(sfx_labels)}"
        sfx_filters.append(f"[{len(sfx_labels)}:a]adelay={int(at * 1000)}|{int(at * 1000)}[{label}]")
        sfx_labels.append(label)
    sfx_track = work / "sfx_track.wav"
    sfx_filters.append("".join(f"[{l}]" for l in sfx_labels) +
                       f"amix=inputs={len(sfx_labels)}:normalize=0:dropout_transition=0[sout]")
    run([FFMPEG, "-y", "-v", "error", *sfx_inputs, "-filter_complex", ";".join(sfx_filters),
         "-map", "[sout]", "-ar", "48000", "-ac", "1", str(sfx_track)])

    # ---- video: cross-faded scene chain --------------------------- #
    video_inputs: list[str] = []
    for clip in clips:
        video_inputs.extend(["-i", str(clip)])
    chain: list[str] = []
    label = "0:v"
    offset = 0.0
    for index in range(1, len(clips)):
        offset += SCENES[index - 1].seconds - XFADE
        out_label = f"x{index}"
        chain.append(
            f"[{label}][{index}:v]xfade=transition="
            f"{'fade' if index % 2 else 'smoothleft'}:duration={XFADE}:offset={offset:.3f}[{out_label}]"
        )
        label = out_label
    # consistent final grade across every engine's output
    chain.append(
        f"[{label}]eq=saturation=1.06:contrast=1.04:gamma=0.99,"
        f"unsharp=5:5:0.35,format=yuv420p[vout]"
    )
    silent_video = work / "video_graded.mp4"
    if silent_video.is_file() and silent_video.stat().st_size > 10_000:
        report["warnings"].append("reused cached video_graded.mp4 (delete it to force a re-grade)")
    else:
        run([FFMPEG, "-y", "-v", "error", *video_inputs, "-filter_complex", ";".join(chain),
             "-map", "[vout]", "-r", str(FPS), "-c:v", "libx264", "-preset", "medium",
             "-crf", "19", "-pix_fmt", "yuv420p", str(silent_video)], timeout=3600)

    # ---- audio mix: narration + ducked music + sfx ---------------- #
    audio_mix = work / "audio_mix.wav"
    run([FFMPEG, "-y", "-v", "error",
         "-i", str(narration_track), "-i", str(music), "-i", str(sfx_track),
         "-filter_complex",
         # narration is split: one copy keys the side-chain duck, one is mixed
         "[0:a]volume=1.0,highpass=f=85,"
         "acompressor=threshold=0.09:ratio=3:attack=12:release=240,asplit=2[narKey][narMix];"
         "[1:a]volume=0.16[mus];"
         "[2:a]volume=0.5[sfx];"
         "[mus][narKey]sidechaincompress=threshold=0.045:ratio=9:attack=8:release=320[duck];"
         "[duck][sfx]amix=inputs=2:normalize=0[bed];"
         "[bed][narMix]amix=inputs=2:normalize=0,"
         "loudnorm=I=-16:TP=-1.5:LRA=11,alimiter=limit=0.96[aout]",
         "-map", "[aout]", "-ar", "48000", "-ac", "2", str(audio_mix)], timeout=1800)

    # ---- subtitles + mux ------------------------------------------ #
    srt = work / "subtitles.srt"
    write_srt(starts, srt)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    run([FFMPEG, "-y", "-v", "error",
         "-i", str(silent_video), "-i", str(audio_mix), "-i", str(srt),
         "-map", "0:v", "-map", "1:a", "-map", "2:0",
         "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
         "-c:s", "mov_text", "-metadata:s:s:0", "language=eng",
         "-movflags", "+faststart", str(out_file)], timeout=1800)

    report["output"] = str(out_file)
    report["subtitles"] = str(srt)
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenes", type=Path, default=REPO / "studio/remotion/out/sample60")
    parser.add_argument("--work", type=Path, default=REPO / "studio/remotion/out/work60")
    parser.add_argument("--out", type=Path, default=REPO / "studio/remotion/out/venice_sample_60s.mp4")
    args = parser.parse_args()
    report = build(args.scenes, args.work, args.out)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
