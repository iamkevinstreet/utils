# kds.synthetic

Test data that is made up, repeatable and checkable: people and companies from a seed, the near
duplicates a careless intake produces (for testing fuzzy matching), and a PDF builder that records
the exact text on each page so a quoted span can be verified against the page it cites.

## Install

Pin a commit of this repository (see [installing](../README.md#installing-a-package)).

```sh
pip install "kds-synthetic @ git+https://github.com/iamkevinstreet/utils@<commit>#subdirectory=synthetic"
```

## Use

```python
from pathlib import Path

from kds.synthetic import NameGen, PdfDoc, near_duplicates
from kds.synthetic.pdftext import pages_text, span_in_page

gen = NameGen(seed=7)
gen.company()  # the same name every run with seed 7
near_duplicates("Acme Logistics LLC")  # ["Acme Logistics Inc.", "Acme Logistic LLC", ...]

doc = PdfDoc(Path("charge-001.pdf"))
doc.line("Charge No. 410-2026-10001")
doc.page_break()
doc.para("The particulars ...")
doc.write(rotate_pages={2})  # page 2 turned, like a careless scan
span_in_page("Charge No. 410-2026-10001", pages_text(doc.path)[0])  # True
```

## Conventions

Nothing here is drawn from real records. Seeds make every set regenerate identically; change a seed
only with a note in the project's changelog, because results depend on it.
