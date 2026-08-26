"""Figure-count attribution from synthetic OOXML (no real source material)."""

from zaspro.extraction.figures import _attribute, count_drawings_in_xml

_W = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'


def _doc(body: str) -> str:
    return f"<w:document {_W}><w:body>{body}</w:body></w:document>"


def _p(*runs: str) -> str:
    return "<w:p>" + "".join(f"<w:r><w:t>{r}</w:t></w:r>" for r in runs) + "</w:p>"


def _p_with_drawing(*, nested_textbox_para: str | None = None) -> str:
    inner = ""
    if nested_textbox_para is not None:
        inner = f"<w:txbxContent>{_p(nested_textbox_para)}</w:txbxContent>"
    return f"<w:p><w:r><w:drawing>{inner}</w:drawing></w:r></w:p>"


def test_drawing_attributed_to_current_task():
    xml = _doc(
        _p_with_drawing()  # cover chrome, before any marker
        + _p("Zadanie 1. (0–1)")
        + _p("some text")
        + _p("Zadanie 2. (0–2)")
        + _p_with_drawing()  # belongs to task 2
        + _p("Koniec")
        + _p_with_drawing()  # footer chrome, after Koniec
    )
    counts, boilerplate, total = _attribute(xml)
    assert total == 3
    assert boilerplate == 2  # cover + footer
    assert counts == {"1": 0, "2": 1}


def test_marker_split_across_runs_is_recognised():
    xml = _doc(
        _p("Zadanie ", "3", ". (0–1)")
        + _p_with_drawing()
        + _p("Zadanie ", "4", ". (0–1)")
    )
    assert count_drawings_in_xml(xml) == {"3": 1, "4": 0}


def test_textbox_paragraph_inside_drawing_is_not_a_marker():
    # A figure whose textbox literally contains "Zadanie 9." must not open a task.
    xml = _doc(
        _p("Zadanie 5. (0–1)")
        + _p_with_drawing(nested_textbox_para="Zadanie 9.")
    )
    counts = count_drawings_in_xml(xml)
    assert counts == {"5": 1}
    assert "9" not in counts


def test_subtask_parent_ranges_are_distinct():
    xml = _doc(
        _p("Zadanie 12.")  # parent, no points
        + _p_with_drawing()  # parent's figure
        + _p("Zadanie 12.1. (0–2)")
        + _p("Zadanie 12.2. (0–2)")
        + _p_with_drawing()  # 12.2's own figure
    )
    assert count_drawings_in_xml(xml) == {"12": 1, "12.1": 0, "12.2": 1}
