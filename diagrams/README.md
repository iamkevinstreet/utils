# kds.diagrams

Draws the architecture and flow diagrams in every README from a TOML file, in one dark house style:
a serif title, a bold one-line subtitle, dashed zones, rounded components, grey arrows, one blue
accent for the paths that matter, and a foundation band. Diagrams are data, so a layout change is a
reviewable diff, and the SVGs are never edited by hand.

## Install

Pin a commit of this repository (see [installing](../README.md#installing-a-package)). It has no dependencies beyond Python 3.12.

```sh
pip install "kds-diagrams @ git+https://github.com/iamkevinstreet/utils@<commit>#subdirectory=diagrams"
```

## Use

```sh
kds-diagrams docs/diagrams.toml      # writes each [[diagram]]'s file beside the spec
```

```toml
[[diagram]]
file = "architecture.svg"
width = 1000
height = 720
title = "Grounded Q&A at a glance"
subtitle = "Answers come only from approved sources, or not at all."
caption = "Grey arrows: requests. Blue: data that leaves your environment."

[[diagram.zone]]
box = [28, 150, 944, 160]            # left, top, width, height
title = "Your environment"
rule = "nothing leaves it unlabelled"

[[diagram.component]]
box = [48, 190, 300, 96]
name = "Retriever"
details = ["approved sources only", "BM25 over chunks"]
note = "new"                         # or "to build"

[[diagram.arrow]]
points = [[348, 238], [420, 238]]
label = "passages"
at = [356, 228]
accent = false
```

## Conventions

- Text never wraps in SVG, so every line is measured against its box; a line that would overflow
  fails with a message saying how wide it needs to be.
- One accent colour, for data crossing a trust boundary or the one path the reader must follow.
- Diagrams show the design, never private infrastructure: no hostnames, addresses or device
  names.
