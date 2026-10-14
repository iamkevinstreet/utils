# kds.synthetic

Made-up people and companies from a seed, near-duplicate variants of a name for testing fuzzy matching, and a PDF builder that records the exact text on each page so a cited span can be verified against the page it names.

## Install

```toml
# in a project's pyproject.toml
dependencies = ["kds-synthetic @ git+https://github.com/iamkevinstreet/utils.git@main#subdirectory=synthetic"]
```

```sh
# or directly
pip install "kds-synthetic @ git+https://github.com/iamkevinstreet/utils.git@main#subdirectory=synthetic"
```

## Use

```python
from kds.synthetic import NameGen, PdfDoc, near_duplicates

gen = NameGen(seed=7)
gen.company()  # "Harbor Foods Inc."
near_duplicates("Acme Logistics LLC")  # ["Acme Logistics Inc.", "Acme Logistic LLC", "ACME LOGISTICS", ...]

doc = PdfDoc(Path("charge-001.pdf"))
doc.line("Charge No. 410-2026-10001")
doc.page_break()
doc.para("The particulars ...")
doc.write(rotate_pages={2})
doc.page_text(1)
```

## Develop

```sh
# from the repository root
pytest synthetic/tests
```

Apache License 2.0. See the repository `LICENSE` and `NOTICE`.
