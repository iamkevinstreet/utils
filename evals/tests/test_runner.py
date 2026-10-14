import json

from kds.evals.case import EvalCase, load_cases
from kds.evals.metrics import field_accuracy
from kds.evals.report import changelog_line, compare
from kds.evals.runner import run_eval
from kds.llm.adapter import ModelAdapter
from kds.llm.fake import FakeProvider


def _cases():
    return [
        EvalCase(id="c1", input={"doc": "A"}, expected={"name": "Acme LLC"}, tags=["clean"]),
        EvalCase(id="c2", input={"doc": "B"}, expected={"name": "Beta Inc"}, tags=["hard"]),
        EvalCase(id="c3", input={"doc": "C"}, expected={"name": "Gamma Co"}, tags=["hard"]),
    ]


def test_run_eval_end_to_end(tmp_path):
    provider = FakeProvider(['{"name": "Acme LLC"}', '{"name": "wrong"}', "boom"])
    adapter = ModelAdapter(provider, model="fake-model")

    def system_fn(case):
        text = adapter.complete(case.input["doc"]).text
        if text == "boom":
            raise RuntimeError("provider exploded")
        return json.loads(text)

    def scorer_fn(case, output):
        return {"accuracy": field_accuracy(output, case.expected, ["name"])["accuracy"]}

    run = run_eval(
        name="demo",
        cases=_cases(),
        adapter=adapter,
        system_fn=system_fn,
        scorer_fn=scorer_fn,
        out_dir=tmp_path,
    )
    assert run.cases == 3 and run.failures == 1
    assert run.summary["accuracy"] == 0.5
    assert run.summary["failure_rate"] == round(1 / 3, 4)
    assert (tmp_path / "demo-latest.md").exists()
    md = (tmp_path / "demo-latest.md").read_text()
    assert "| accuracy | 0.5 |" in md and "provider exploded" in md and "| hard | 2 |" in md


def test_load_cases_rejects_duplicate_ids(tmp_path):
    p = tmp_path / "cases.jsonl"
    p.write_text('{"id": "a", "input": {}}\n{"id": "a", "input": {}}\n')
    try:
        load_cases(p)
    except ValueError as e:
        assert "duplicate" in str(e)
    else:
        raise AssertionError("expected ValueError")


def test_compare_and_changelog(tmp_path):
    adapter = ModelAdapter(FakeProvider(['{"name": "x"}'] * 6), model="fake-model")
    run_a = run_eval(
        name="v1",
        cases=_cases(),
        adapter=adapter,
        system_fn=lambda c: {"name": "x"},
        scorer_fn=lambda c, o: {"acc": 0.0},
        out_dir=tmp_path,
    )
    run_b = run_eval(
        name="v2",
        cases=_cases(),
        adapter=adapter,
        system_fn=lambda c: c.expected,
        scorer_fn=lambda c, o: {"acc": 1.0},
        out_dir=tmp_path,
    )
    table = compare(run_a, run_b, ["acc"])
    assert "| acc | 0 | 1 | +1 |" in table
    line = changelog_line("v0.2", "Oct 20, 2026", "Added span verification", run_a, run_b, "acc")
    assert line.startswith("- **v0.2, Oct 20, 2026.** Added span verification: acc 0 -> 1.")
