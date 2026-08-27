"""zaspro.mapping.run batch driver — offline (stub agent, set in-process)."""

from __future__ import annotations

from tests.fixtures.mapping_world import build_world
from zaspro.mapping import StubMappingAgent, run as run_mod, set_agent


def test_batch_run_maps_and_reports_queue_depth(db, capsys):
    w = build_world(db)
    db.commit()
    ref = "SYNTH-P0-660-A-0000-arkusz.docx"

    set_agent(StubMappingAgent())
    try:
        # --review-all: threshold 1.01 -> every chunk queued
        rc = run_mod.run([ref], threshold=1.01)
    finally:
        set_agent(None)

    assert rc == 0
    out = capsys.readouterr().out
    assert "agent: StubMappingAgent" in out
    assert "preflight" not in out  # stub never preflights
    assert f"{ref}: mapped 4, queued 4" in out
    assert "review queue depth   : 4  (this run added 4)" in out
    assert "est. API cost" not in out  # stub -> no cost line


def test_batch_run_skips_already_mapped_paper(db, capsys):
    w = build_world(db)
    db.commit()
    ref = "SYNTH-P0-660-A-0000-arkusz.docx"

    set_agent(StubMappingAgent())
    try:
        run_mod.run([ref])
        capsys.readouterr()
        rc = run_mod.run([ref])  # second pass: nothing to do
    finally:
        set_agent(None)

    assert rc == 0
    out = capsys.readouterr().out
    assert "already mapped, nothing to do" in out
