"""Reproducible Piper narration manifests and honest voice-quality gates."""

from __future__ import annotations

import hashlib
import json
import wave
from dataclasses import asdict, dataclass
from pathlib import Path


class NarrationError(RuntimeError):
    pass


@dataclass(frozen=True)
class NarrationChunk:
    scene_id: str
    chunk_index: int
    text: str
    text_sha256: str
    audio_sha256: str
    duration_s: float
    sample_rate: int
    channels: int


@dataclass(frozen=True)
class VoiceQualityReview:
    model_sha256: str
    pronunciation_approved: bool = False
    consistency_approved: bool = False
    naturalness_approved: bool = False
    reviewer: str = ""
    notes: str = ""

    @property
    def approved(self) -> bool:
        return bool(self.reviewer.strip()) and self.pronunciation_approved and self.consistency_approved and self.naturalness_approved


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def synthesize_piper_chunk(
    text: str,
    destination: Path,
    *,
    model_path: Path,
    model_config_path: Path,
    scene_id: str,
    chunk_index: int,
) -> NarrationChunk:
    """Synthesize speech only; never creates video or claims listening approval."""
    if not text.strip() or not model_path.is_file() or not model_config_path.is_file():
        raise NarrationError("Text, ONNX model and model JSON are required")
    try:
        from piper import PiperVoice
    except ImportError as exc:
        raise NarrationError("Piper runtime is unavailable") from exc
    destination.parent.mkdir(parents=True, exist_ok=True)
    voice = PiperVoice.load(str(model_path), config_path=str(model_config_path))
    with wave.open(str(destination), "wb") as output:
        voice.synthesize_wav(text, output)
    with wave.open(str(destination), "rb") as recorded:
        channels, sample_rate, frames = recorded.getnchannels(), recorded.getframerate(), recorded.getnframes()
    if channels != 1 or sample_rate <= 0 or frames <= 0:
        raise NarrationError("Piper produced invalid/empty WAV")
    return NarrationChunk(scene_id, chunk_index, text, hashlib.sha256(text.encode()).hexdigest(), file_sha256(destination), frames / sample_rate, sample_rate, channels)


def verify_chunk_manifest(chunks: list[NarrationChunk], model_path: Path, review: VoiceQualityReview) -> dict:
    if not chunks or not model_path.is_file():
        raise NarrationError("Narration chunks and model are required")
    model_hash = file_sha256(model_path)
    blockers = []
    if model_hash != review.model_sha256:
        blockers.append("Voice-quality review belongs to a different model")
    if not review.approved:
        blockers.append("Human pronunciation, consistency and naturalness review is incomplete")
    scene_rates = {(chunk.scene_id, chunk.sample_rate, chunk.channels) for chunk in chunks}
    global_rates = {(chunk.sample_rate, chunk.channels) for chunk in chunks}
    if len(global_rates) != 1:
        blockers.append("Narration chunks have inconsistent PCM formats")
    return {
        "model_sha256": model_hash,
        "chunk_count": len(chunks),
        "duration_s": sum(chunk.duration_s for chunk in chunks),
        "formats": sorted(scene_rates),
        "human_review_approved": review.approved,
        "blockers": blockers,
        "chunks": [asdict(chunk) for chunk in chunks],
        "video_generated": False,
    }


def save_narration_report(report: dict, destination: Path) -> None:
    Path(destination).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
