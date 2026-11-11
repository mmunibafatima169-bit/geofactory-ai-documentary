#!/usr/bin/env python3
"""Reproducible delivery checks; requires Pillow and the FFprobe/FFmpeg binaries."""
from __future__ import annotations
import hashlib
import json
import re
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "delivery_evidence"
VIDEO = ROOT / "examples/studio-sample-v2/venice_sample_60s_v2.mp4"
SRT = ROOT / "examples/studio-sample-v2/subtitles.srt"
FFMPEG = ROOT / "studio/remotion/node_modules/@ffmpeg-installer/linux-x64/ffmpeg"
FFPROBE = ROOT / "studio/remotion/node_modules/@ffprobe-installer/linux-x64/ffprobe"


def command(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run([str(x) for x in args], text=True, capture_output=True, check=False)


def timestamp(value: float) -> str:
    return f"{int(value // 60):02d}:{value % 60:06.3f}"


def parse_time(value: str) -> float:
    h, m, rest = value.split(":")
    s, ms = rest.split(",")
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000


probe = command([FFPROBE, "-v", "error", "-show_format", "-show_streams", "-of", "json", VIDEO])
metadata = json.loads(probe.stdout)
video_stream = next(s for s in metadata["streams"] if s["codec_type"] == "video")
audio_stream = next(s for s in metadata["streams"] if s["codec_type"] == "audio")

# A full second decode is independent of the black/freeze filter decode.
decode = command([FFMPEG, "-v", "error", "-xerror", "-i", VIDEO, "-map", "0:v:0", "-map", "0:a:0", "-f", "null", "-"])
(EVIDENCE / "logs/full_decode.log").write_text(
    "$ ffmpeg -v error -xerror -i VIDEO -map 0:v:0 -map 0:a:0 -f null -\n" + decode.stdout + decode.stderr,
    encoding="utf-8")

# Exact decoded-frame hashes expose consecutive duplicates without judging intent.
framemd5 = command([FFMPEG, "-v", "error", "-i", VIDEO, "-map", "0:v:0", "-an", "-f", "framemd5", "-"])
(EVIDENCE / "logs/framemd5.log").write_text(
    "$ ffmpeg -v error -i VIDEO -map 0:v:0 -an -f framemd5 -\n" + framemd5.stdout + framemd5.stderr,
    encoding="utf-8")
hashes = []
for line in framemd5.stdout.splitlines():
    if line and not line.startswith("#"):
        hashes.append(line.rsplit(",", 1)[-1].strip())
consecutive = sum(a == b for a, b in zip(hashes, hashes[1:]))
unique = len(set(hashes))

# Validate the sidecar SRT and compare cue text with the embedded subtitle packets.
pattern = re.compile(r"(\d+)\n(\d\d:\d\d:\d\d,\d{3}) --> (\d\d:\d\d:\d\d,\d{3})\n(.*?)(?=\n\n|\Z)", re.S)
cues = []
for match in pattern.finditer(SRT.read_text(encoding="utf-8").strip()):
    start, end = parse_time(match[2]), parse_time(match[3])
    text = match[4].replace("\n", " ")
    cues.append({"index": int(match[1]), "start": start, "end": end, "text": text})
subtitle_errors = []
for expected, cue in enumerate(cues, 1):
    if cue["index"] != expected:
        subtitle_errors.append(f"nonsequential index {cue['index']}")
    if not 0 <= cue["start"] < cue["end"] <= 60:
        subtitle_errors.append(f"bad bounds cue {expected}")
    if expected > 1 and cue["start"] < cues[expected - 2]["end"]:
        subtitle_errors.append(f"overlap cue {expected}")
long_cues = [c["index"] for c in cues if len(c["text"]) > 84]
embedded = command([FFMPEG, "-v", "error", "-i", VIDEO, "-map", "0:s:0", "-f", "srt", "-"])
(EVIDENCE / "embedded_subtitles.srt").write_text(embedded.stdout, encoding="utf-8")
embedded_text = re.sub(r"\d+\n\d\d:\d\d:\d\d,\d{3} --> \d\d:\d\d:\d\d,\d{3}\n", "", embedded.stdout)
embedded_words = re.findall(r"[A-Za-z']+", embedded_text)
source_words = re.findall(r"[A-Za-z']+", " ".join(c["text"] for c in cues))

# Extract lossless representative frames and key animation stills.
frames = EVIDENCE / "frames"
times = [1, 5, 9, 13, 17, 21, 25, 29, 33, 37, 41, 45, 49, 53, 57, 59]
for t in times:
    destination = frames / f"frame_{t:05.1f}s.png"
    result = command([FFMPEG, "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", VIDEO, "-frames:v", "1", destination])
    if result.returncode:
        raise RuntimeError(result.stderr)

# Labelled 4x4 contact sheet; thumbnails retain 16:9.
thumb_w, thumb_h, label_h = 480, 270, 30
sheet = Image.new("RGB", (thumb_w * 4, (thumb_h + label_h) * 4), "#0b111a")
draw = ImageDraw.Draw(sheet)
font = ImageFont.load_default(size=18)
for index, t in enumerate(times):
    image = Image.open(frames / f"frame_{t:05.1f}s.png").convert("RGB").resize((thumb_w, thumb_h))
    x, y = (index % 4) * thumb_w, (index // 4) * (thumb_h + label_h)
    sheet.paste(image, (x, y))
    draw.text((x + 10, y + thumb_h + 5), f"{timestamp(t)}  |  latest v2", fill="white", font=font)
sheet.save(EVIDENCE / "contact_sheet_latest.jpg", quality=92)

summary = {
    "video": str(VIDEO.relative_to(ROOT)),
    "sha256": hashlib.sha256(VIDEO.read_bytes()).hexdigest(),
    "metadata": {
        "duration_s": float(metadata["format"]["duration"]),
        "size_bytes": int(metadata["format"]["size"]),
        "video": {k: video_stream.get(k) for k in ["codec_name", "profile", "width", "height", "sample_aspect_ratio", "display_aspect_ratio", "r_frame_rate", "avg_frame_rate", "nb_frames", "pix_fmt"]},
        "audio": {k: audio_stream.get(k) for k in ["codec_name", "profile", "sample_rate", "channels", "channel_layout", "duration"]},
    },
    "decode": {"exit_code": decode.returncode, "stderr": decode.stderr, "result": "PASS" if decode.returncode == 0 and not decode.stderr else "FAIL"},
    "frame_hashes": {"decoded_frames": len(hashes), "unique_hashes": unique, "consecutive_exact_duplicates": consecutive},
    "subtitles": {"cue_count": len(cues), "syntax_bounds_overlap_errors": subtitle_errors, "cues_over_84_chars": long_cues, "embedded_sidecar_word_sequences_match": embedded_words == source_words, "actual_speech_alignment": "NOT TESTED", "dictionary_spelling": "NOT TESTED"},
    "limits": ["Freeze detections are heuristic and may be intentional static holds.", "No ASR/forced alignment or listening test was performed.", "Frame-hash duplication does not by itself establish editorially inappropriate repetition."],
}
(EVIDENCE / "qa_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
print(json.dumps(summary, indent=2))
