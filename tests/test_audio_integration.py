import hashlib
import tempfile
import unittest
import wave
from pathlib import Path

import numpy as np

from geofactory.production.audio import AudioCue, AudioError, AudioMixPlan, SoundAsset, build_filter_graph
from geofactory.production.capabilities import Capability
from geofactory.production.direction import build_preproduction_plan
from geofactory.production.gates import evaluate_production_gates, readiness_summary
from geofactory.production.models import DocumentaryProfile
from geofactory.production.narration import NarrationChunk, VoiceQualityReview, verify_chunk_manifest
from geofactory.production.quality_standards import assess_plan_standards


def sound_asset(path: Path, role: str, asset_id: str, approved: bool = True) -> SoundAsset:
    return SoundAsset(asset_id, role, str(path), "https://example.com/asset", "Test creator", "CC0-1.0", "https://creativecommons.org/publicdomain/zero/1.0/", "Test attribution", hashlib.sha256(path.read_bytes()).hexdigest(), approved)


class AudioContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.paths = {}
        for role in ("narration", "music", "ambience", "sfx"):
            path = root / f"{role}.wav"
            with wave.open(str(path), "wb") as output:
                output.setnchannels(1); output.setsampwidth(2); output.setframerate(48000)
                output.writeframes(np.zeros(4800, dtype="<i2").tobytes())
            self.paths[role] = path

    def tearDown(self): self.temp.cleanup()

    def mix(self):
        cues = tuple(AudioCue(role, "scene-001", sound_asset(self.paths[role], role, role), gain_db=-12 if role != "narration" else 0) for role in ("narration", "music", "ambience", "sfx"))
        return AudioMixPlan("job", cues)

    def test_music_and_ambience_have_independent_sidechain_keys(self):
        graph = build_filter_graph(self.mix())
        self.assertIn("asplit=3", graph)
        self.assertEqual(graph.count("sidechaincompress"), 2)
        self.assertIn("loudnorm=I=-16.0:TP=-1.5", graph)
        self.mix().validate()

    def test_unapproved_sound_rights_are_rejected(self):
        asset = sound_asset(self.paths["music"], "music", "music", approved=False)
        with self.assertRaises(AudioError): asset.validate()

    def test_narration_quality_is_model_bound_and_human_gated(self):
        model = self.paths["music"]
        chunk = NarrationChunk("scene-001", 0, "Test", "text", "audio", 1.0, 22050, 1)
        review = VoiceQualityReview(hashlib.sha256(model.read_bytes()).hexdigest())
        report = verify_chunk_manifest([chunk], model, review)
        self.assertFalse(report["human_review_approved"])
        self.assertTrue(report["blockers"])

    def test_subject_standards_are_common_but_visuals_differ(self):
        plans = [build_preproduction_plan(DocumentaryProfile(subject, "Test", "Question"), [(0.0, 8.0, text)]) for subject, text in [("geography", "The border crosses the river. [clm-one]"), ("economics", "Inflation reached eight percent. [clm-one]")]]
        self.assertNotEqual(plans[0].scenes[0].visual_technique, plans[1].scenes[0].visual_technique)
        self.assertFalse(assess_plan_standards(plans[0]))

    def test_gates_detect_tools_assets_voice_and_satellite(self):
        plan = build_preproduction_plan(DocumentaryProfile("geography", "Test", "Question"), [(0.0, 8.0, "Viewed from above, the satellite coastline changes. [clm-one]")])
        findings = evaluate_production_gates(plan, {}, resolved_assets={}, approved_assets=set())
        codes = {finding.code for finding in findings}
        self.assertIn("engine_unavailable", codes)
        self.assertIn("asset_brief_unresolved", codes)
        self.assertIn("voice_quality_unapproved", codes)
        self.assertIn("live_imagery_unverified", codes)
        self.assertFalse(readiness_summary(findings)["ready"])


if __name__ == "__main__": unittest.main()
