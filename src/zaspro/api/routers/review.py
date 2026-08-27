"""Review queue endpoints (SPEC §9). The dashboard home is built entirely from
these: one item per screen, keyboard decisions, no page reloads."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from zaspro.api.deps import get_db
from zaspro.api.schemas import (
    BatchApproveIn,
    BatchGroupView,
    DecisionIn,
    DecisionResult,
    QueueStatsView,
    ReviewItemView,
)
from zaspro.api.views import item_view
from zaspro.review import (
    ReviewError,
    agreement_curve,
    batch_approve,
    batch_groups,
    next_item,
    queue_stats,
    record_decision,
)

router = APIRouter(prefix="/review", tags=["review"])


def _stats_view(db: Session) -> QueueStatsView:
    return QueueStatsView(**queue_stats(db).__dict__)


def _result(db: Session) -> DecisionResult:
    nxt = next_item(db)
    return DecisionResult(
        ok=True,
        stats=_stats_view(db),
        next=item_view(db, nxt, with_candidates=True) if nxt else None,
    )


@router.get("/queue", response_model=QueueStatsView)
def get_queue(db: Session = Depends(get_db)) -> QueueStatsView:
    return _stats_view(db)


@router.get("/calibration")
def get_calibration(db: Session = Depends(get_db)) -> dict:
    cal = agreement_curve(db)
    return {
        "resolved": cal.resolved,
        "pending": cal.pending,
        "excluded_defective": cal.excluded_defective,
        "target": cal.target,
        "recommended_threshold": cal.recommended_threshold,
        "notes": cal.notes,
        "bands": [
            {
                "lo": b.lo,
                "hi": b.hi,
                "n": b.n,
                "agree": b.agree,
                "disagree": b.disagree,
                "audit": b.audit,
                "agreement": b.agreement,
            }
            for b in cal.bands
        ],
    }


@router.get("/next", response_model=ReviewItemView | None)
def get_next(
    response: Response,
    exclude: str = Query("", description="comma-separated review_item ids to skip"),
    db: Session = Depends(get_db),
) -> ReviewItemView | None:
    skip = {int(x) for x in exclude.split(",") if x.strip().isdigit()}
    item = next_item(db, exclude_ids=skip)
    if item is None:
        response.status_code = 204
        return None
    return item_view(db, item, with_candidates=True)


@router.get("/batches", response_model=list[BatchGroupView])
def get_batches(db: Session = Depends(get_db)) -> list[BatchGroupView]:
    return [
        BatchGroupView(
            topic_id=g.topic_id,
            source_document_id=g.source_document_id,
            item_ids=g.item_ids,
            min_confidence=g.min_confidence,
        )
        for g in batch_groups(db)
    ]


@router.post("/{item_id}/decision", response_model=DecisionResult)
def post_decision(
    item_id: int, body: DecisionIn, db: Session = Depends(get_db)
) -> DecisionResult:
    try:
        record_decision(
            db,
            item_id,
            reviewer=body.reviewer,
            decision=body.decision,
            reason_code=body.reason_code,
            note=body.note,
            edit=body.edit,
        )
    except ReviewError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    return _result(db)


@router.post("/batch-approve", response_model=DecisionResult)
def post_batch_approve(
    body: BatchApproveIn, db: Session = Depends(get_db)
) -> DecisionResult:
    try:
        batch_approve(db, body.item_ids, reviewer=body.reviewer)
    except ReviewError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    return _result(db)
