# kds.evals

Cases, metrics, a runner that times and prices every case and writes a Markdown results table (overall and by tag), a model judge with a calibration check against hand-graded samples, and a comparison tool that produces changelog lines.

## Install

```toml
# in a project's pyproject.toml
dependencies = ["kds-evals @ git+https://github.com/iamkevinstreet/utils.git@main#subdirectory=evals"]
```

```sh
# or directly
pip install "kds-evals @ git+https://github.com/iamkevinstreet/utils.git@main#subdirectory=evals"
```

## Use

```python
from kds.evals import load_cases, run_eval
from kds.evals.metrics import field_accuracy

run = run_eval(
    name="extraction-v0.1",
    cases=load_cases("evals/cases/sample.jsonl"),
    adapter=adapter,
    system_fn=lambda case: my_system(case.input),
    scorer_fn=lambda case, out: {"accuracy": field_accuracy(out, case.expected, FIELDS)["accuracy"]},
    out_dir="evals/results",
)
run.summary  # also written to evals/results/extraction-v0.1-latest.md
```

## Develop

```sh
# from the repository root
pytest evals/tests
```

Apache License 2.0. See the repository `LICENSE` and `NOTICE`.
