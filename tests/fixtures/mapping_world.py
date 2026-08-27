"""Minimal DB world for M3 mapping/review tests — no pandoc, no files.

`build_world(session)` seeds:
  * a Subject + one Unit "VIII" with three podstawowy leaf requirements
    VIII.1 / VIII.2 / VIII.3 (plus one rozszerzony VIII.R1 that must never be
    offered as a mapping target)
  * a SourceDocument with four EXERCISE chunks + matching Exercise rows:
      - chunk "Zadanie 1." cites "VIII.2)" in its text  -> confident stub map
      - chunk "Zadanie 2." cites nothing, prose overlaps VIII.1 weakly
      - chunk "Zadanie 3." cites nothing, no overlap    -> unmapped, low conf
      - chunk "Zadanie 4." cites "VIII.2)" too           -> for batch grouping
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from zaspro.db.models import (
    ContentType,
    Exercise,
    ExerciseOrigin,
    ExtractionMethod,
    ExtractionStatus,
    Source,
    SourceChunk,
    SourceDocument,
    Subject,
    Topic,
    TopicLevel,
    Unit,
    VerificationStatus,
)


@dataclass
class World:
    document_id: int
    topic_ids: dict[str, int]
    chunk_ids: dict[str, int]


def build_world(session: Session) -> World:
    subject = Subject(name="Matematyka", slug="matematyka", level="podstawowy, rozszerzony")
    unit = Unit(subject=subject, code="VIII", slug="planimetria", name="Planimetria", order_index=8)
    session.add_all([subject, unit])
    session.flush()

    reqs = {
        "VIII.1": ("oblicza pole trójkąta", TopicLevel.PODSTAWOWY),
        "VIII.2": ("stosuje twierdzenie Pitagorasa", TopicLevel.PODSTAWOWY),
        "VIII.3": ("wykorzystuje własności okręgu", TopicLevel.PODSTAWOWY),
        "VIII.R1": ("dowodzi twierdzeń planimetrycznych", TopicLevel.ROZSZERZONY),
    }
    topic_ids: dict[str, int] = {}
    for i, (code, (name, level)) in enumerate(reqs.items(), start=1):
        t = Topic(
            unit=unit,
            name=name,
            slug=code.lower().replace(".", "-"),
            level=level,
            order_index=i,
            official_requirement_code=code,
        )
        session.add(t)
        session.flush()
        topic_ids[code] = t.id

    src = Source(
        source_type="EXAM",
        title="synthetic arkusz",
        publisher="CKE",
        url="https://example.invalid/synth",
        file_ref="SYNTH-P0-660-A-0000-arkusz.docx",
        licence_status="CKE_UNSPECIFIED",
        verbatim_ok=True,
    )
    session.add(src)
    session.flush()

    doc = SourceDocument(
        source_id=src.id,
        file_ref="SYNTH-P0-660-A-0000-arkusz.docx",
        session_code="0000",
        paper_version="A",
        extraction_status=ExtractionStatus.VALIDATED,
    )
    session.add(doc)
    session.flush()

    chunk_specs = [
        ("1", "W trójkącie prostokątnym VIII.2) przyprostokątne mają długość 3 i 4."),
        ("2", "Oblicza pole trójkąta o podstawie 6 i wysokości 4."),
        ("3", "Wpisz wynik do tabeli i zaznacz odpowiedź na karcie."),
        ("4", "Zastosuj VIII.2) twierdzenie Pitagorasa dla przekątnej prostokąta."),
    ]
    chunk_ids: dict[str, int] = {}
    for order, (num, text) in enumerate(chunk_specs):
        ch = SourceChunk(
            source_document_id=doc.id,
            heading=f"Zadanie {num}.",
            section=num,
            content_type=ContentType.EXERCISE,
            text=text,
            latex=text,
            order_index=order,
            extraction_method=ExtractionMethod.pandoc_omml,
            confidence=None,  # deterministic
        )
        session.add(ch)
        session.flush()
        chunk_ids[num] = ch.id
        session.add(
            Exercise(
                source_document_id=doc.id,
                exercise_number=num,
                statement=text,
                statement_latex_raw=text,
                origin=ExerciseOrigin.OFFICIAL,
                verbatim_ok=True,
                points_available=1,
                verification_status=VerificationStatus.DRAFT,
            )
        )
    session.flush()
    return World(document_id=doc.id, topic_ids=topic_ids, chunk_ids=chunk_ids)
