# kds.evals

Evaluation cases, metrics plain enough to check by hand, a runner that times and prices every case
and writes JSON and Markdown results (overall and by tag), a model judge with a calibration check
against human grades, and a comparison that writes changelog lines.

## Install

Pin a commit of this repository (see [installing](../README.md#installing-a-package)).

```sh
pip install "kds-evals @ git+https://github.com/iamkevinstreet/utils@<commit>#subdirectory=evals" \
  "kds-llm @ git+https://github.com/iamkevinstreet/utils@<commit>#subdirectory=llm" \
  "kds-logs @ git+https://github.com/iamkevinstreet/utils@<commit>#subdirectory=logs" \
  "kds-settings @ git+https://github.com/iamkevinstreet/utils@<commit>#subdirectory=settings"
```

`kds-evals` needs the other kds packages listed, from the same commit.

## Use

```python
from kds.evals import field_accuracy, load_cases, run_eval

run = run_eval(
    name="extraction-v0.2",
    cases=load_cases("data/samples/cases.jsonl"),
    adapter=adapter,
    system_fn=lambda case: extract(case.input),
    scorer_fn=lambda case, out: field_accuracy(out, case.expected, FIELDS),
    out_dir="results",
)
run.summary  # also in results/extraction-v0.2-latest.md
```

## Conventions

- A project supplies `system_fn(case)` and `scorer_fn(case, output)`; the runner owns timing, cost,
  failures and reports. A failing case is recorded, never raised.
- Each case runs under its own request id, `<run name>:<case id>`.
- Scores are averaged over the cases that ran; failures count in the failure rate, latency and cost.
- A judged metric is reported beside the judge's agreement with human grades (`calibrate`).
