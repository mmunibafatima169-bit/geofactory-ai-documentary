"""Factual verification gate for narration and on-screen numbers.

Consumes a source/claim ledger shared with motion templates. It cannot establish
truth by itself; it enforces provenance, catches conflicts, checks narration ↔
display consistency, and blocks unverified numerical claims pending a human.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from urllib.parse import urlparse


@dataclass(frozen=True)
class FactFinding:
    level: str
    code: str
    message: str
    claim_id: str | None = None

    def to_dict(self) -> dict:
        out = {"level": self.level, "code": self.code, "message": self.message}
        if self.claim_id:
            out["claim_id"] = self.claim_id
        return out


def _number_tokens(text: str) -> set[float]:
    return {float(v.replace(",", "")) for v in re.findall(r"(?<![\w.])\d[\d,]*(?:\.\d+)?", text)}


def verify_fact_ledger(path: Path, displayed_text: str = "", narration_text: str = "") -> dict:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    sources = data.get("sources", [])
    claims = data.get("claims", [])
    findings: list[FactFinding] = []
    source_ids: set[str] = set()

    for source in sources:
        sid = str(source.get("id", ""))
        if not sid or sid in source_ids:
            findings.append(FactFinding("critical", "source_id_invalid", f"Missing/duplicate source id: {sid!r}"))
            continue
        source_ids.add(sid)
        url = urlparse(str(source.get("url", "")))
        if url.scheme != "https" or not url.netloc:
            findings.append(FactFinding("critical", "source_url_invalid", f"{sid} lacks a valid HTTPS URL"))
        accessed = str(source.get("accessed_at", ""))
        try:
            date.fromisoformat(accessed)
        except ValueError:
            findings.append(FactFinding("critical", "access_date_invalid", f"{sid} needs YYYY-MM-DD access date"))
        if source.get("reliability") not in {"primary", "scientific", "research-lead"}:
            findings.append(FactFinding("warning", "source_reliability_missing", f"{sid} has no reliability class"))

    quantities: dict[str, tuple[float, str]] = {}
    allowed_display: set[float] = set()
    expected_narration: set[float] = set()
    for claim in claims:
        cid = str(claim.get("id", ""))
        refs = claim.get("source_ids", [])
        missing = [r for r in refs if r not in source_ids]
        if not refs or missing:
            findings.append(FactFinding("critical", "claim_source_missing", f"Claim references missing sources: {missing}", cid))
        try:
            value = float(claim["value"])
        except (KeyError, TypeError, ValueError):
            findings.append(FactFinding("critical", "claim_value_invalid", "Numeric claim needs a numeric value", cid))
            continue
        quantity = str(claim.get("quantity", ""))
        unit = str(claim.get("unit", ""))
        if quantity in quantities and quantities[quantity] != (value, unit):
            old_value, old_unit = quantities[quantity]
            findings.append(FactFinding(
                "critical", "conflicting_numbers",
                f"{quantity} conflicts: {old_value:g} {old_unit} vs {value:g} {unit}", cid,
            ))
        quantities[quantity] = (value, unit)
        if claim.get("display_value") is not None:
            display_value = float(claim["display_value"])
            allowed_display.add(display_value)
            if display_value != value:
                findings.append(FactFinding(
                    "critical", "display_value_mismatch",
                    f"Displayed {display_value:g} does not match sourced {value:g} {unit}", cid,
                ))
        if claim.get("narration_value") is not None:
            narration_value = float(claim["narration_value"])
            expected_narration.add(narration_value)
            if narration_value != value:
                findings.append(FactFinding(
                    "critical", "narration_value_mismatch",
                    f"Narrated {narration_value:g} does not match sourced {value:g} {unit}", cid,
                ))
        if not claim.get("verified"):
            findings.append(FactFinding(
                "warning", "human_verification_required",
                f"{cid} ({value:g} {unit}) is a research lead, not owner-verified", cid,
            ))
        if not str(claim.get("uncertainty", "")).strip():
            findings.append(FactFinding("warning", "uncertainty_missing", "Numeric claim needs context/uncertainty", cid))

    shown = _number_tokens(displayed_text)
    for number in sorted(shown - allowed_display):
        findings.append(FactFinding(
            "critical", "unsourced_display_number",
            f"On-screen number {number:g} is absent from the verified display ledger",
        ))
    spoken = _number_tokens(narration_text)
    missing_spoken = expected_narration - spoken
    # narration may spell numbers as words; call this a note, not a blocker.
    for number in sorted(missing_spoken):
        findings.append(FactFinding(
            "note", "narration_number_spelled_or_missing",
            f"Expected narration value {number:g} not found as digits; verify the spoken-word form",
        ))

    critical = sum(f.level == "critical" for f in findings)
    return {
        "sources": len(sources),
        "claims": len(claims),
        "critical_findings": critical,
        "approval_blocked": critical > 0 or any(f.code == "human_verification_required" for f in findings),
        "allowed_display_numbers": sorted(allowed_display),
        "findings": [f.to_dict() for f in findings],
        "animation_audit": data.get("animation_audit", {}),
        "limits": ["Automated checks validate consistency and provenance, not truth; human source review is mandatory."],
    }
