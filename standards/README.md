# kds.standards

`kds-standards` holds a repository to one code standard. It runs in pre-commit and CI and exits
non-zero on any finding, so the standard is checked by a tool rather than by memory.

## Install

Pin a commit of this repository (see [installing](../README.md#installing-a-package)). It has no dependencies beyond Python 3.12 and git.

```sh
pip install "kds-standards @ git+https://github.com/iamkevinstreet/utils@<commit>#subdirectory=standards"
```

## Use

```sh
kds-standards check .                # every rule below
kds-standards stamp [files]          # rewrite header titles and dates from git
kds-standards header <file> --purpose "What the file is for."   # add a header box
kds-standards trace on <path>        # turn the logger lines on in a working copy
kds-standards trace off <path>       # and off again before committing
```

```text
backend/grounded_qa/answer.py:42: logger-line: needs a logger line directly above it
backend/grounded_qa/answer.py:1: header: Last modified on must be 2026-10-29; run kds-standards stamp
.gitignore:0: layout: must ignore *.pfx
```

## What it checks

| Rule | Finding |
| --- | --- |
| `header` | the 72-character box is missing, malformed, or its title, dates or purpose are wrong |
| `logger-line` | a statement has no commented logger line above it, or one sits above `else` |
| `trace-off` | a logger line was left switched on |
| `width` | code over 99 characters, or a comment or docstring over 72 |
| `literal` | a string or number repeats inside functions instead of being a named constant |
| `layout` | a file is over 500 lines or too deep; a required file, folder README or ignore rule is missing |
| `docs` | a Markdown file other than a README.md, the root CHANGELOG.md and SECURITY.md, or data under `data/`; a link in a published file to something the repository does not hold |

Dates come from git, following renames: "Created on" is the first commit that held the file, "Last
modified on" its latest, and a file changed since then must show today.

## Develop

```sh
make test     # from the repository root
make check    # the checker also runs on itself
```
