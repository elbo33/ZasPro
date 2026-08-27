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
_MIN_SAMPLES = 5  # a band with fewer than this cannot, on its own, set the cutoff


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
    resolved: int  # decisions that count toward the curve
    pending: int
    recommended_threshold: float | None
    excluded_defective: int = 0  # resolved but on known-defective agent input
    target: float = _TARGET_AGREEMENT
    notes: list[str] = field(default_factory=list)


def _band_for(conf: float) -> tuple[float, float]:
    lo = _BANDS[0]
    for b in _BANDS:
        if conf >= b:
            lo = b
    hi = next((x for x in _BANDS if x > lo), 1.0)
    return lo, hi


def recommend_threshold(bands: list[Band]) -> tuple[float | None, str | None]:
    """The lowest band boundary `t` such that every band at or above `t` is safe
    to auto-approve. Returns `(threshold, None)` on success, `(None, reason)`
    otherwise.

    * A band at/above `t` whose agreement is below the target **blocks** `t` —
      no matter how few samples it has. A thin band at 0% agreement is still
      evidence that auto-approving there is wrong. (This is the bug fix: the
      first version skipped bands with n<5 when scanning, so an n=1 band at 0%
      and an n=4 band at 75% were ignored and it returned 0.00.)
    * If nothing blocks `t` but the lowest non-empty band at/above `t` is thin
      (< `_MIN_SAMPLES`), there isn't enough evidence to stand a cutoff on it —
      report "insufficient data", never a number.

    The number returned is the lower bound of the lowest band that actually
    carries evidence — never a level whose band range has zero samples (that
    would repeat the original bug in the other direction: "clean" by absence of
    data).
    """

    hit_thin_cutoff: Band | None = None
    for b in bands:
        at_or_above = [x for x in bands if x.lo >= b.lo]
        blocking = [
            x for x in at_or_above
            if x.n > 0 and (x.agreement or 0.0) < _TARGET_AGREEMENT
        ]
        if blocking:
            continue
        cutoff_band = next((x for x in at_or_above if x.n > 0), None)
        if cutoff_band is None:
            continue  # no data at all at/above here
        if cutoff_band.n < _MIN_SAMPLES:
            hit_thin_cutoff = hit_thin_cutoff or cutoff_band
            continue  # never recommend a cutoff we can't stand on; look higher
        return cutoff_band.lo, None

    if hit_thin_cutoff is not None:
        return None, (
            "insufficient data: the band(s) that would set the cutoff are thin "
            f"(e.g. [{hit_thin_cutoff.lo:.1f}, {hit_thin_cutoff.hi:.1f}) "
            f"n={hit_thin_cutoff.n})"
        )
    return None, f"no confidence band clears {_TARGET_AGREEMENT:.0%} agreement"


def agreement_curve(session: Session) -> Calibration:
    bands = [Band(lo, next((x for x in _BANDS if x > lo), 1.0)) for lo in _BANDS]
    by_lo = {b.lo: b for b in bands}

    items = session.scalars(
        select(ReviewItem).where(
            ReviewItem.item_type == ReviewItemType.CURRICULUM_MAPPING
        )
    ).all()

    resolved = pending = excluded = 0
    for item in items:
        if item.status is ReviewStatus.OPEN:
            pending += 1
            continue
        if item.input_defect:
            excluded += 1  # decided on broken input — not evidence about the agent
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

        # an EDIT or a PROMOTE means the agent's primary needed changing —
        # disagreement, even though the item ends APPROVED
        changed = any(
            d.decision in (ReviewDecisionType.EDIT, ReviewDecisionType.PROMOTE)
            for d in decs
        )
        agree = item.status is ReviewStatus.APPROVED and not changed

        lo, _ = _band_for(float(conf))
        b = by_lo[lo]
        b.n += 1
        b.audit += 1 if item.audit_sample else 0
        if agree:
            b.agree += 1
        else:
            b.disagree += 1

    recommended, reason = recommend_threshold(bands)

    notes: list[str] = []
    if recommended is None and reason:
        notes.append(reason)
    thin = [f"[{b.lo:.1f},{b.hi:.1f})" for b in bands if 0 < b.n < _MIN_SAMPLES]
    if thin:
        notes.append(
            "thin data in " + ", ".join(thin) + " — review more mappings before trusting these"
        )
    below = [
        f"[{b.lo:.1f},{b.hi:.1f}) {b.agreement:.0%} (n={b.n})"
        for b in bands
        if b.n > 0 and (b.agreement or 0.0) < _TARGET_AGREEMENT
    ]
    if below:
        notes.append("below target: " + ", ".join(below))
    if pending:
        notes.append(f"{pending} mapping review items still open — curve is partial")
    if excluded:
        notes.append(
            f"{excluded} resolved decisions excluded (input_defect) — the agent's "
            "input was broken; those chunks need remapping and re-review"
        )
    if resolved == 0:
        notes.append("no resolved mapping reviews yet — run a calibration pass")

    return Calibration(
        bands=bands,
        resolved=resolved,
        pending=pending,
        recommended_threshold=recommended,
        excluded_defective=excluded,
        notes=notes,
    )
