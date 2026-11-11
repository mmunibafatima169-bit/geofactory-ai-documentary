import unittest

from geofactory.production.direction import build_preproduction_plan, classify_subject
from geofactory.production.models import ClaimEvidence, ContractError, DocumentaryProfile
from geofactory.production.readiness import evaluate_preproduction, readiness_decision
from geofactory.production.research import audit_research


class ProductionDirectionTests(unittest.TestCase):
    def profile(self, subject="geography"):
        return DocumentaryProfile(subject, "Test", "Why does this system change?")

    def test_subjects_do_not_share_one_visual_template(self):
        narration = [(0.0, 8.0, "The border crosses the river. [clm-one]")]
        geography = build_preproduction_plan(self.profile("geography"), narration)
        economics = build_preproduction_plan(self.profile("economics"), [(0.0, 8.0, "Inflation reached eight percent. [clm-one]")])
        infrastructure = build_preproduction_plan(self.profile("infrastructure"), [(0.0, 8.0, "The foundation sits underground. [clm-one]")])
        disaster = build_preproduction_plan(self.profile("disaster"), [(0.0, 8.0, "The flood forced an evacuation. [clm-one]")])
        techniques = {p.scenes[0].visual_technique for p in (geography, economics, infrastructure, disaster)}
        self.assertEqual(len(techniques), 4)

    def test_engine_fallback_is_explicit(self):
        plan = build_preproduction_plan(self.profile("infrastructure"), [(0.0, 8.0, "The gate mechanism opens. [clm-one]")], available_engines={"remotion", "ffmpeg"})
        scene = plan.scenes[0]
        self.assertEqual(scene.fallback_from, "blender")
        self.assertIn("QUALITY DOWNGRADE", scene.rationale)

    def test_research_requires_scene_claims_and_review(self):
        plan = build_preproduction_plan(self.profile(), [(0.0, 8.0, "The border crosses the river.")])
        codes = {finding.code for finding in audit_research(plan, [])}
        self.assertIn("scene_without_claim", codes)
        plan = build_preproduction_plan(self.profile(), [(0.0, 8.0, "The border crosses the river. [clm-one]")])
        codes = {finding.code for finding in audit_research(plan, [])}
        self.assertIn("unknown_claim", codes)

    def test_readiness_does_not_pass_on_planning_alone(self):
        plan = build_preproduction_plan(self.profile(), [(0.0, 8.0, "The border crosses the river. [clm-one]")])
        claims = [ClaimEvidence("clm-one", "A sourced statement", ("src-one",), "verified", 1)]
        checks = evaluate_preproduction(plan, claims, runtime_verified_engines={"remotion", "ffmpeg"})
        statuses = {check.category: check.status for check in checks}
        self.assertEqual(statuses["factual_accuracy"], "MET")
        self.assertEqual(statuses["cinematic_footage"], "NOT_TESTED")
        self.assertEqual(readiness_decision(checks), "NOT_READY")

    def test_invalid_runtime_is_rejected(self):
        with self.assertRaises(ContractError):
            DocumentaryProfile("geography", "Test", "Question", target_runtime_s=60).validate()

    def test_subject_classifier(self):
        self.assertEqual(classify_subject("Inflation debt GDP and markets"), "economics")
        self.assertEqual(classify_subject("Borders rivers and islands"), "geography")


if __name__ == "__main__":
    unittest.main()
