from kds.evals.metrics import exact_match, field_accuracy, null_metrics, percentile, precision_recall


def test_exact_match_normalises():
    assert exact_match("  Acme   Logistics LLC ", "acme logistics llc")
    assert exact_match(["race", "sex"], ["Sex", "Race"])
    assert not exact_match("2026-01-02", "2026-01-03")


def test_field_accuracy():
    pred = {"a": "x", "b": "wrong", "c": None}
    gold = {"a": "X", "b": "right", "c": None}
    r = field_accuracy(pred, gold, ["a", "b", "c"])
    assert r["correct"] == 2 and r["total"] == 3
    assert abs(r["accuracy"] - 2 / 3) < 1e-9
    assert r["per_field"] == {"a": True, "b": False, "c": True}


def test_null_metrics_counts_guesses_and_false_abstentions():
    pred = {"a": None, "b": "guess", "c": None, "d": "v"}
    gold = {"a": None, "b": None, "c": "truth", "d": "v"}
    r = null_metrics(pred, gold, ["a", "b", "c", "d"])
    assert r["tp"] == 1 and r["guesses"] == 1 and r["false_abstentions"] == 1
    assert r["precision"] == 0.5 and r["recall"] == 0.5


def test_precision_recall():
    r = precision_recall(["Acme LLC", "beta inc"], ["acme llc", "Gamma Co"])
    assert r["tp"] == 1 and r["precision"] == 0.5 and r["recall"] == 0.5


def test_percentile_nearest_rank():
    vals = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
    assert percentile(vals, 50) == 50
    assert percentile(vals, 95) == 100
    assert percentile([], 50) == 0.0
