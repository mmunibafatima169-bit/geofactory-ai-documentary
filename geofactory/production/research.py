"""Claim-to-scene research coverage checks; model prose is never evidence."""

from __future__ import annotations

from dataclasses import dataclass

from geofactory.production.models import ClaimEvidence, PreproductionPlan


@dataclass(frozen=True)
class ResearchFinding:
    severity: str
    code: str
    message: str


def audit_research(plan: PreproductionPlan, claims: list[ClaimEvidence]) -> list[ResearchFinding]:
    by_id = {claim.claim_id: claim for claim in claims}
    if len(by_id) != len(claims):
        return [ResearchFinding("blocker", "duplicate_claim_id", "Claim ids must be unique")]
    findings: list[ResearchFinding] = []
    used: set[str] = set()
    for scene in plan.scenes:
        if not scene.claim_ids:
            findings.append(ResearchFinding("blocker", "scene_without_claim", f"{scene.scene_id} has no linked factual claim"))
        for claim_id in scene.claim_ids:
            used.add(claim_id)
            claim = by_id.get(claim_id)
            if claim is None:
                findings.append(ResearchFinding("blocker", "unknown_claim", f"{scene.scene_id} references {claim_id}, absent from the ledger"))
                continue
            if not claim.source_ids:
                findings.append(ResearchFinding("blocker", "unsourced_claim", f"{claim_id} has no source"))
            if claim.review_status != "verified":
                findings.append(ResearchFinding("blocker", "claim_not_verified", f"{claim_id} is {claim.review_status}"))
            if claim.independent_source_count < 1:
                findings.append(ResearchFinding("blocker", "independence_unrecorded", f"{claim_id} has no reviewed independent-source count"))
            for brief in scene.asset_briefs:
                if brief.required_source_ids != scene.claim_ids:
                    findings.append(ResearchFinding("warning", "asset_claim_link_mismatch", f"{scene.scene_id} asset evidence links differ from narration"))
    for claim_id in sorted(set(by_id) - used):
        findings.append(ResearchFinding("note", "unused_claim", f"{claim_id} is researched but not used"))
    return findings
