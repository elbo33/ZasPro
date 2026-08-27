"""Agreement-vs-confidence curve for the Mapping Agent (SPEC §10, ADR 0009).

After a calibration pass — `zaspro.mapping.run <arkusz> --review-all`, then work
the whole queue by keyboard — this turns the recorded decisions into data:
for each confidence band, how often did the reviewer accept the agent's mapping
unchanged? That curve is what `AUTO_APPROVE_THRESHOLD` should be set from,
instead of a guess.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from zaspro.db.models import (
    ChunkMapping,
    ReviewDecision,
    ReviewDecisionType,
    ReviewItem,
    ReviewItemType,
    ReviewStatus,
)

# lower bound of each band; last band is [0.9, 1.0]
_BANDS = [0.0, 0.5, 0.7, 0.8, 0.9]
_TARGET_AGREEMENT = 0.95


@dataclass
class Band:
    lo: float
    hi: float
    n: int = 0
    agree: int = 0  # approved, never edited
    disagree: int = 0  # rejected, or approved only after an edit
    audit: int = 0  # of n, how many were audit-sampled (vs low-confidence)

    @property
    def agreement(self) -> float | None:
        return self.agree / self.n if self.n else None


@dataclass
class Calibration:
    bands: list[Band]
    resolved: int
    pending: int
    recommended_threshold: float | None
    target: float = _TARGET_AGREEMENT
    notes: list[str] = field(default_factory=list)


def _band_for(conf: float) -> tuple[float, float]:
    lo = _BANDS[0]
    for b in _BANDS:
        if conf >= b:
            lo = b
    hi = next((x for x in _BANDS if x > lo), 1.0)
    return lo, hi


def agreement_curve(session: Session) -> Calibration:
    bands = [Band(lo, next((x for x in _BANDS if x > lo), 1.0)) for lo in _BANDS]
    by_lo = {b.lo: b for b in bands}

    items = session.scalars(
        select(ReviewItem).where(
            ReviewItem.item_type == ReviewItemType.CURRICULUM_MAPPING
        )
    ).all()

    resolved = pending = 0
    for item in items:
        if item.status is ReviewStatus.OPEN:
            pending += 1
            continue
        resolved += 1

        decs = session.scalars(
            select(ReviewDecision)
            .where(ReviewDecision.review_item_id == item.id)
            .order_by(ReviewDecision.id)
        ).all()
        conf = next(
            (d.mapping_confidence for d in decs if d.mapping_confidence is not None),
            item.confidence,
        )
        if conf is None:
            m = session.get(ChunkMapping, item.ref_id)
            conf = m.confidence if m else 0.0

        edited = any(d.decision is ReviewDecisionType.EDIT for d in decs)
        agree = item.status is ReviewStatus.APPROVED and not edited

        lo, _ = _band_for(float(conf))
        b = by_lo[lo]
        b.n += 1
        b.audit += 1 if item.audit_sample else 0
        if agree:
            b.agree += 1
        else:
            b.disagree += 1

    # recommended threshold: the lowest band boundary at/above which every band
    # meets the target (and has enough data to mean something)
    recommended: float | None = None
    for b in bands:
        higher = [x for x in bands if x.lo >= b.lo and x.n >= 5]
        if higher and all(
            (x.agreement or 0.0) >= _TARGET_AGREEMENT for x in higher
        ):
            recommended = b.lo
            break

    notes: list[str] = []
    thin = [f"[{b.lo:.1f},{b.hi:.1f})" for b in bands if 0 < b.n < 5]
    if thin:
        notes.append(
            "thin data in " + ", ".join(thin) + " — review more mappings before trusting these"
        )
    if pending:
        notes.append(f"{pending} mapping review items still open — curve is partial")
    if resolved == 0:
        notes.append("no resolved mapping reviews yet — run a calibration pass")

    return Calibration(
        bands=bands,
        resolved=resolved,
        pending=pending,
        recommended_threshold=recommended,
        notes=notes,
    )
