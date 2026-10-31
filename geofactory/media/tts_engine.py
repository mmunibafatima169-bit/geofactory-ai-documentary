"""Sentence-chunked offline TTS with FFprobe verification and measured SRT timing."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path

from geofactory.core.config import FactoryConfig

MAX_CHUNK_CHARS = 180
MAX_NARRATION_CHARS = 200_000
SILENCE_PEAK_DBFS = -55.0
SUBTITLE_LINE_CHARS = 42


class TTSError(RuntimeError):
    """Raised when local speech generation is unavailable or fails."""


def split_sentences(text: str, max_chars: int = MAX_CHUNK_CHARS) -> list[str]:
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        raise TTSError("Narration text is empty.")
    if len(text) > MAX_NARRATION_CHARS:
        raise TTSError(f"Narration exceeds the {MAX_NARRATION_CHARS}-character safety limit.")
    if max_chars < 40:
        raise ValueError("max_chars must be at least 40.")
    sentences = re.split(r"(?<=[.!?])\s+", text)
    chunks: list[str] = []
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        parts = re.split(r"(?<=[,;:])\s+", sentence)
        current = ""
        for part in parts:
            if len(part) > max_chars:
                words = part.split()
                for word in words:
                    if len(word) > max_chars:
                        raise TTSError("A narration word exceeds the maximum chunk size.")
                    if current and len(current) + len(word) + 1 > max_chars:
                        chunks.append(current)
                        current = ""
                    current = f"{current} {word}".strip()
                continue
            candidate = f"{current} {part}".strip()
            if current and len(candidate) > max_chars:
                chunks.append(current)
                current = part
            else:
                current = candidate
        if current:
            chunks.append(current)
    if not chunks:
        raise TTSError("Narration contains no synthesizable text.")
    return chunks


def _ffprobe_audio(path: Path, ffprobe: str = "ffprobe") -> dict[str, object]:
    executable = shutil.which(ffprobe)
    if not executable:
        raise TTSError(f"FFprobe executable not found: {ffprobe}")
    result = subprocess.run(
        [
            executable, "-v", "error", "-show_entries",
            "format=duration:stream=codec_type,sample_rate,channels",
            "-of", "json", str(path),
        ],
        capture_output=True, text=True, timeout=30, check=False,
    )
    if result.returncode:
        raise TTSError(f"FFprobe could not read {path}: {result.stderr[-1000:]}")
    try:
        info = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise TTSError(f"FFprobe returned invalid audio metadata for {path}.") from exc
    streams = info.get("streams", [])
    audio = next(
        (stream for stream in streams if stream.get("codec_type") == "audio"),
        None,
    ) if isinstance(streams, list) else None
    try:
        duration = float(info.get("format", {}).get("duration", 0))
    except (TypeError, ValueError, AttributeError) as exc:
        raise TTSError(f"FFprobe returned invalid audio duration for {path}.") from exc
    if audio is None or duration <= 0 or int(audio.get("sample_rate", 0)) <= 0:
        raise TTSError(f"Audio chunk is missing a valid stream or duration: {path}")
    return {"duration": duration, "stream": audio}


def audio_duration_seconds(path: Path, ffprobe: str = "ffprobe") -> float:
    """Measure playable audio duration with FFprobe, not a filename/size estimate."""
    return float(_ffprobe_audio(path, ffprobe)["duration"])


def _validate_audio_chunk(path: Path, config: FactoryConfig) -> float:
    info = _ffprobe_audio(path, config.ffprobe)
    ffmpeg = shutil.which(config.ffmpeg)
    if not ffmpeg:
        raise TTSError(f"FFmpeg executable not found: {config.ffmpeg}")
    decoded = subprocess.run(
        [ffmpeg, "-v", "error", "-i", str(path), "-f", "null", "-"],
        capture_output=True, text=True, timeout=60, check=False,
    )
    if decoded.returncode:
        raise TTSError(f"Audio chunk failed full decode: {decoded.stderr[-1000:]}")
    levels = subprocess.run(
        [
            ffmpeg, "-hide_banner", "-nostats", "-i", str(path),
            "-af", "volumedetect", "-f", "null", "-",
        ],
        capture_output=True, text=True, timeout=60, check=False,
    )
    if levels.returncode:
        raise TTSError(f"Could not inspect audio levels: {levels.stderr[-1000:]}")
    peak_match = re.search(r"max_volume:\s*(-inf|-?\d+(?:\.\d+)?) dB", levels.stderr)
    if not peak_match:
        raise TTSError(f"FFmpeg did not report peak audio level for {path}.")
    peak = float("-inf") if peak_match.group(1) == "-inf" else float(peak_match.group(1))
    if peak <= SILENCE_PEAK_DBFS:
        raise TTSError(
            f"Audio chunk is silent or nearly silent (peak {peak:g} dBFS): {path.name}"
        )
    return float(info["duration"])


def _synthesize_chunk(
    text: str, destination: Path, config: FactoryConfig
) -> None:
    if config.tts_backend == "espeak-ng":
        executable = shutil.which(config.espeak_executable)
        if not executable:
            raise TTSError(f"eSpeak NG executable not found: {config.espeak_executable}")
        command = [
            executable, "-w", str(destination), "-v", config.espeak_voice,
            "-s", str(config.espeak_speed), "--stdin",
        ]
    elif config.tts_backend == "piper":
        executable = shutil.which(config.piper_executable)
        if not executable:
            raise TTSError(f"Piper executable not found: {config.piper_executable}")
        if not config.piper_voice_model or not config.piper_voice_license.strip():
            raise TTSError("Piper voice model and verified licence are required.")
        command = [
            executable, "--model", str(config.piper_voice_model),
            "--output_file", str(destination),
        ]
    else:
        raise TTSError(
            "No audio TTS backend is configured. Use tts_backend='espeak-ng' or 'piper'; "
            "the CLI's none mode only saves a clearly labelled text script."
        )
    try:
        result = subprocess.run(
            command, input=text, text=True, capture_output=True, timeout=120, check=False
        )
    except subprocess.TimeoutExpired as exc:
        raise TTSError(f"TTS chunk exceeded the 120-second timeout: {text[:80]!r}") from exc
    if result.returncode:
        raise TTSError(
            f"TTS backend failed ({result.returncode}): {result.stderr[-1000:]}"
        )
    if not destination.is_file() or destination.stat().st_size == 0:
        raise TTSError("TTS backend reported success but produced no audio chunk.")


def synthesize(
    text: str,
    destination: Path,
    config: FactoryConfig,
    subtitle_destination: Path | None = None,
) -> float:
    """Synthesize and validate each sentence, join WAV chunks, optionally write aligned SRT."""
    chunks = split_sentences(text)
    if config.tts_backend == "none":
        raise TTSError("Text-only mode does not produce audio; use the CLI narration script output.")
    if config.tts_backend == "piper":
        if not config.piper_voice_model or not config.piper_voice_model.is_file():
            raise TTSError("Piper needs an existing piper_voice_model path.")
        if not config.piper_voice_license.strip():
            raise TTSError("Record the voice model's verified licence before use.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg = shutil.which(config.ffmpeg)
    if not ffmpeg:
        raise TTSError(f"FFmpeg executable not found: {config.ffmpeg}")

    subtitle_entries: list[tuple[str, float, float]] = []
    with tempfile.TemporaryDirectory(
        prefix=".geofactory-tts-", dir=destination.parent
    ) as temporary:
        work_dir = Path(temporary)
        chunk_paths: list[Path] = []
        elapsed = 0.0
        for index, chunk in enumerate(chunks, 1):
            chunk_path = work_dir / f"chunk-{index:05d}.wav"
            _synthesize_chunk(chunk, chunk_path, config)
            duration = _validate_audio_chunk(chunk_path, config)
            chunk_paths.append(chunk_path)
            subtitle_entries.append((chunk, elapsed, elapsed + duration))
            elapsed += duration

        concat_list = work_dir / "concat.txt"
        entries = [
            f"file '{str(chunk_path).replace(chr(39), chr(39) + chr(92) + chr(39) + chr(39))}'"
            for chunk_path in chunk_paths
        ]
        concat_list.write_text("\n".join(entries) + "\n", encoding="utf-8")
        temporary_output = work_dir / "narration.wav"
        joined = subprocess.run(
            [
                ffmpeg, "-v", "error", "-f", "concat", "-safe", "0",
                "-i", str(concat_list), "-c:a", "pcm_s16le", str(temporary_output),
            ],
            capture_output=True, text=True, timeout=600, check=False,
        )
        if joined.returncode:
            raise TTSError(f"Could not join narration chunks: {joined.stderr[-1500:]}")
        total_duration = _validate_audio_chunk(temporary_output, config)
        if abs(total_duration - elapsed) > max(0.25, len(chunks) * 0.01):
            raise TTSError("Joined narration duration does not match the measured chunks.")
        staged_output = destination.with_name(
            f".{destination.stem}.{uuid.uuid4().hex}.complete.wav"
        )
        try:
            shutil.copyfile(temporary_output, staged_output)
            staged_output.replace(destination)
        except Exception:
            staged_output.unlink(missing_ok=True)
            raise

    if subtitle_destination is not None:
        write_aligned_srt(subtitle_entries, subtitle_destination)
    return audio_duration_seconds(destination, config.ffprobe)


def _wrap_subtitle(text: str) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current: list[str] = []
    for word in words:
        if len(word) > SUBTITLE_LINE_CHARS:
            raise TTSError("A word cannot fit within the subtitle line limit.")
        if current and len(" ".join([*current, word])) > SUBTITLE_LINE_CHARS:
            lines.append(" ".join(current))
            current = []
        current.append(word)
    if current:
        lines.append(" ".join(current))
    return lines


def write_aligned_srt(
    entries: list[tuple[str, float, float]], destination: Path
) -> None:
    """Split measured sentence timings into short, readable caption cues."""
    if not entries:
        raise ValueError("Cannot create subtitles without measured narration chunks.")
    blocks: list[str] = []
    cue_number = 1
    for text, sentence_start, sentence_end in entries:
        lines = _wrap_subtitle(text)
        groups = [lines[index:index + 2] for index in range(0, len(lines), 2)]
        weights = [max(1, len(" ".join(group).split())) for group in groups]
        total_weight = sum(weights)
        duration = sentence_end - sentence_start
        cursor = sentence_start
        accumulated = 0
        for group, weight in zip(groups, weights, strict=True):
            accumulated += weight
            cue_end = (
                sentence_end if accumulated == total_weight
                else sentence_start + duration * accumulated / total_weight
            )
            if cue_end <= cursor:
                raise ValueError("Measured audio produced a non-positive subtitle interval.")
            blocks.append(
                f"{cue_number}\n{_timestamp(cursor)} --> {_timestamp(cue_end)}\n"
                f"{chr(10).join(group)}"
            )
            cue_number += 1
            cursor = cue_end
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.write_text("\n\n".join(blocks) + "\n", encoding="utf-8")
    temporary.replace(destination)


def write_estimated_srt(text: str, destination: Path, words_per_minute: int = 145) -> None:
    """Write estimated caption timing when audio is unavailable; QA treats it as draft only."""
    if words_per_minute < 60 or words_per_minute > 240:
        raise ValueError("words_per_minute must be between 60 and 240.")
    chunks = split_sentences(text)
    entries = []
    elapsed = 0.0
    for chunk in chunks:
        duration = max(0.5, len(chunk.split()) * 60.0 / words_per_minute)
        entries.append((chunk, elapsed, elapsed + duration))
        elapsed += duration
    write_aligned_srt(entries, destination)


def write_text_only_narration(text: str, destination: Path) -> None:
    """Save explicit narration text without implying that audio was generated."""
    if not text.strip():
        raise TTSError("Narration text is empty.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.write_text(
        "# TEXT-ONLY NARRATION — no speech audio generated\n\n"
        "> This file is a script only. Audio and synchronized subtitles are absent.\n\n"
        + text.strip() + "\n",
        encoding="utf-8",
    )
    temporary.replace(destination)


def _timestamp(seconds: float) -> str:
    millis = round(seconds * 1000)
    hours, remainder = divmod(millis, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    whole_seconds, milliseconds = divmod(remainder, 1000)
    return f"{hours:02}:{minutes:02}:{whole_seconds:02},{milliseconds:03}"
