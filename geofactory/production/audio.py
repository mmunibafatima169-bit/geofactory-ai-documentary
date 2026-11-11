"""Scene-linked, rights-aware audio mixing with dialogue-keyed ducking."""

from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import urlparse

from geofactory.production.models import PreproductionPlan


class AudioError(RuntimeError):
    pass


ALLOWED_SOUND_LICENCES = {"CC0-1.0", "CC-BY-3.0", "CC-BY-4.0", "CC-BY-SA-3.0", "CC-BY-SA-4.0", "Public Domain", "Pexels License", "Pixabay Content License", "Owner Licensed"}


@dataclass(frozen=True)
class SoundAsset:
    asset_id: str
    role: str  # narration | music | ambience | sfx
    path: str
    source_url: str
    creator: str
    licence: str
    licence_url: str
    attribution: str
    sha256: str
    rights_approved: bool = False

    def validate(self) -> None:
        if self.role not in {"narration", "music", "ambience", "sfx"}:
            raise AudioError(f"Unsupported sound role: {self.role}")
        if self.licence not in ALLOWED_SOUND_LICENCES:
            raise AudioError(f"Unapproved sound licence: {self.licence}")
        for url in (self.source_url, self.licence_url):
            parsed = urlparse(url)
            if parsed.scheme != "https" or not parsed.hostname:
                raise AudioError("Sound provenance URLs must use HTTPS")
        if not self.creator.strip() or not self.attribution.strip() or not self.rights_approved:
            raise AudioError("Sound rights, creator and attribution require approval")
        path = Path(self.path)
        if not path.is_file() or path.stat().st_size == 0:
            raise AudioError(f"Sound asset missing: {path}")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != self.sha256:
            raise AudioError(f"Sound hash mismatch: {self.asset_id}")


@dataclass(frozen=True)
class AudioCue:
    cue_id: str
    scene_id: str
    asset: SoundAsset
    start_s: float = 0.0
    gain_db: float = 0.0
    trim_start_s: float = 0.0


@dataclass(frozen=True)
class AudioMixPlan:
    job_id: str
    cues: tuple[AudioCue, ...]
    sample_rate: int = 48000
    target_lufs: float = -16.0
    true_peak_dbtp: float = -1.5

    def validate(self, plan: PreproductionPlan | None = None) -> None:
        if not any(cue.asset.role == "narration" for cue in self.cues):
            raise AudioError("Dialogue is required for sidechain-keyed mixing")
        if len({cue.cue_id for cue in self.cues}) != len(self.cues):
            raise AudioError("Audio cue IDs must be unique")
        scene_ids = {scene.scene_id for scene in plan.scenes} if plan else None
        for cue in self.cues:
            cue.asset.validate()
            if cue.start_s < 0 or cue.trim_start_s < 0 or not -60 <= cue.gain_db <= 12:
                raise AudioError(f"Invalid cue timing/gain: {cue.cue_id}")
            if scene_ids is not None and cue.scene_id not in scene_ids:
                raise AudioError(f"Cue references unknown scene: {cue.scene_id}")


def _gain(value: float) -> float:
    return 10 ** (value / 20)


def build_filter_graph(plan: AudioMixPlan) -> str:
    """Build one FFmpeg graph; music and ambience share the narration sidechain."""
    filters = []
    narration_inputs = [index for index, cue in enumerate(plan.cues) if cue.asset.role == "narration"]
    if len(narration_inputs) != 1:
        raise AudioError("This mix contract requires one concatenated narration input")
    narration = narration_inputs[0]
    ducked_roles = [cue.asset.role for cue in plan.cues if cue.asset.role in {"music", "ambience"}]
    duck_labels = [f"[duck_key_{index}]" for index in range(len(ducked_roles))]
    filters.append(f"[{narration}:a]aresample={plan.sample_rate},aformat=channel_layouts=stereo,asplit={1 + len(duck_labels)}[narration]" + "".join(duck_labels))
    mix_labels = ["[narration]"]
    duck_cursor = 0
    for index, cue in enumerate(plan.cues):
        if cue.asset.role == "narration":
            continue
        label = f"cue_{index}"
        delay = round(cue.start_s * 1000)
        filters.append(f"[{index}:a]aresample={plan.sample_rate},aformat=channel_layouts=stereo,atrim=start={cue.trim_start_s:.3f},asetpts=PTS-STARTPTS,volume={_gain(cue.gain_db):.8f},adelay={delay}:all=1[{label}]")
        if cue.asset.role in {"music", "ambience"}:
            ratio = 8 if cue.asset.role == "music" else 4
            ducked = f"{label}_ducked"
            filters.append(f"[{label}]{duck_labels[duck_cursor]}sidechaincompress=threshold=0.03:ratio={ratio}:attack=20:release=400:makeup=1[{ducked}]")
            duck_cursor += 1
            mix_labels.append(f"[{ducked}]")
        else:
            mix_labels.append(f"[{label}]")
    filters.append("".join(mix_labels) + f"amix=inputs={len(mix_labels)}:duration=longest:normalize=0,loudnorm=I={plan.target_lufs}:TP={plan.true_peak_dbtp}:LRA=11,alimiter=limit=0.84:level=false,aresample={plan.sample_rate}[aout]")
    return ";".join(filters)


def execute_audio_mix(plan: AudioMixPlan, destination: Path, *, ffmpeg: str, production_plan: PreproductionPlan | None = None) -> dict:
    """Execute audio-only assembly. No video input/output is permitted."""
    plan.validate(production_plan)
    command = [ffmpeg, "-y", "-hide_banner"]
    for cue in plan.cues:
        if Path(cue.asset.path).suffix.lower() in {".mp4", ".mov", ".mkv", ".webm"}:
            raise AudioError("Audio mix accepts audio assets, not video containers")
        command += ["-i", cue.asset.path]
    command += ["-filter_complex", build_filter_graph(plan), "-map", "[aout]", "-vn", "-c:a", "pcm_s24le", str(destination)]
    result = subprocess.run(command, capture_output=True, text=True, timeout=300, check=False)
    if result.returncode or not destination.is_file():
        raise AudioError(f"Audio mix failed: {result.stderr[-1200:]}")
    return {"command": command, "output": str(destination), "video_output": False, "cues": [asdict(cue) for cue in plan.cues]}


def write_sound_manifest(plan: AudioMixPlan, destination: Path) -> None:
    payload = {"job_id": plan.job_id, "sample_rate": plan.sample_rate, "target_lufs": plan.target_lufs, "true_peak_dbtp": plan.true_peak_dbtp, "cues": [asdict(cue) for cue in plan.cues], "rights_notice": "All assets require owner rights approval; automated licence allowlists are not legal clearance."}
    Path(destination).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
