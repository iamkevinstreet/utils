from kds.synthetic.names import NameGen, near_duplicates
from kds.synthetic.pdf import PdfDoc
from kds.synthetic.pdftext import pages_text, span_in_page


def test_namegen_is_deterministic():
    a, b = NameGen(seed=3), NameGen(seed=3)
    assert [a.person() for _ in range(5)] == [b.person() for _ in range(5)]
    assert a.company() == b.company()


def test_near_duplicates_cover_the_classic_traps():
    variants = near_duplicates("Acme Logistics LLC")
    assert "Acme Logistics Inc." in variants
    assert any(v.startswith("Acme Logistic ") for v in variants)  # dropped trailing s
    assert "ACME LOGISTICS" in variants
    assert "Acme Logistics LLC" not in variants


def test_pdf_roundtrip_and_span_check(tmp_path):
    doc = PdfDoc(tmp_path / "charge.pdf")
    doc.line("CHARGE OF DISCRIMINATION")
    doc.line("Charge No. 510-2026-01234")
    doc.page_break()
    doc.para(
        "The particulars of the charge continue on this second page and describe the alleged conduct in detail."
    )
    doc.write(rotate_pages={2})
    pages = pages_text(doc.path)
    assert len(pages) == 2
    assert span_in_page("Charge No. 510-2026-01234", pages[0])
    assert not span_in_page("Charge No. 510-2026-01234", pages[1])
    assert span_in_page("second   page", pages[1])
