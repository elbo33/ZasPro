from zaspro.extraction.corpus import _derive_sibling


def test_sibling_derivation_mmap_convention():
    assert (
        _derive_sibling("MMAP-P0-100-A-2605-arkusz.pdf")
        == "MMAP-P0-660-A-2605-arkusz.docx"
    )
    assert (
        _derive_sibling("MMAP-P0-100-2605-zasady.pdf")
        == "MMAP-P0-660-2605-zasady.docx"
    )


def test_sibling_derivation_informator_convention():
    assert (
        _derive_sibling("Informator_EM2024_matematyka_pp.pdf")
        == "Informator_EM2024_matematyka_pp_660.docx"
    )


def test_docx_has_no_sibling():
    assert _derive_sibling("MMAP-P0-660-A-2605-arkusz.docx") is None
