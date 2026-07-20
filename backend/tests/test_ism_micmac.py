"""Tests for the user-input-only ISM-MICMAC analysis tool."""

import csv
import json
from pathlib import Path

import pytest

from scripts.ism_micmac import (
    InputValidationError,
    analyze_ism_micmac,
    load_matrix_csv,
    load_ssim_csv,
    main,
)


def _write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def test_ssim_transitive_reachability_powers_levels_and_classification(tmp_path):
    # User judgments: A -> B -> C, with no submitted direct A -> C link.
    input_path = _write(
        tmp_path / "relations.csv",
        "factor_i,factor_j,relation\n"
        "A,B,V\n"
        "A,C,O\n"
        "B,C,V\n",
    )
    factors, initial = load_ssim_csv(input_path)
    result = analyze_ism_micmac(factors, initial)

    assert factors == ["A", "B", "C"]
    assert result["initial_reachability_matrix"] == [
        [1, 1, 0],
        [0, 1, 1],
        [0, 0, 1],
    ]
    assert result["final_reachability_matrix"] == [
        [1, 1, 1],
        [0, 1, 1],
        [0, 0, 1],
    ]
    assert result["transitive_links_added"] == [{"from": "A", "to": "C"}]
    assert [partition["factors"] for partition in result["level_partitions"]] == [
        ["C"],
        ["B"],
        ["A"],
    ]

    analysis = {row["factor"]: row for row in result["factor_analysis"]}
    assert (analysis["A"]["driving_power"], analysis["A"]["dependence_power"]) == (3, 1)
    assert (analysis["B"]["driving_power"], analysis["B"]["dependence_power"]) == (2, 2)
    assert (analysis["C"]["driving_power"], analysis["C"]["dependence_power"]) == (1, 3)
    assert analysis["A"]["micmac_classification"] == "independent"
    assert analysis["B"]["micmac_classification"] == "linkage"
    assert analysis["C"]["micmac_classification"] == "dependent"


def test_mutual_relation_factors_share_an_ism_level(tmp_path):
    input_path = _write(
        tmp_path / "cycle.csv",
        "factor_i,factor_j,relation\n"
        "A,B,X\n"
        "A,C,V\n"
        "B,C,V\n",
    )
    factors, initial = load_ssim_csv(input_path)
    result = analyze_ism_micmac(factors, initial)
    assert [partition["factors"] for partition in result["level_partitions"]] == [
        ["C"],
        ["A", "B"],
    ]


@pytest.mark.parametrize(
    "csv_text,expected_message",
    [
        (
            "factor_i,factor_j,relation\nA,B,V\nA,C,O\n",
            "SSIM is incomplete",
        ),
        (
            "factor_i,factor_j,relation\nA,B,YES\n",
            "expected A, O, V, X",
        ),
        (
            "factor_i,factor_j,relation\nA,B,V\nB,A,A\n",
            "duplicate SSIM judgment",
        ),
    ],
)
def test_ssim_rejects_missing_invalid_or_duplicate_judgments(
    tmp_path, csv_text, expected_message
):
    input_path = _write(tmp_path / "invalid.csv", csv_text)
    with pytest.raises(InputValidationError, match=expected_message):
        load_ssim_csv(input_path)


def test_labeled_binary_matrix_is_loaded_in_header_order_and_validated(tmp_path):
    matrix_path = _write(
        tmp_path / "matrix.csv",
        "factor,A,B,C\n"
        "C,0,0,0\n"
        "A,0,1,0\n"
        "B,0,0,1\n",
    )
    factors, matrix = load_matrix_csv(matrix_path)
    assert factors == ["A", "B", "C"]
    # Input rows are reordered to match the headers and reflexive links are added.
    assert matrix == [[1, 1, 0], [0, 1, 1], [0, 0, 1]]

    bad_path = _write(
        tmp_path / "bad_matrix.csv",
        "factor,A,B\nA,1,maybe\nB,0,1\n",
    )
    with pytest.raises(InputValidationError, match="exactly 0 or 1"):
        load_matrix_csv(bad_path)


def test_cli_writes_complete_deterministic_json_and_csv_outputs(tmp_path):
    input_path = _write(
        tmp_path / "relations.csv",
        "factor_i,factor_j,relation\nA,B,V\nA,C,O\nB,C,V\n",
    )
    json_path = tmp_path / "out" / "analysis.json"
    csv_dir = tmp_path / "out" / "csv"

    assert main(
        [
            "--input",
            str(input_path),
            "--format",
            "ssim",
            "--json-output",
            str(json_path),
            "--csv-output-dir",
            str(csv_dir),
        ]
    ) == 0

    result = json.loads(json_path.read_text(encoding="utf-8"))
    assert result["final_reachability_matrix"][0][2] == 1
    expected_files = {
        "initial_reachability.csv",
        "final_reachability.csv",
        "factor_analysis.csv",
        "level_partitions.csv",
        "transitive_links.csv",
    }
    assert {path.name for path in csv_dir.iterdir()} == expected_files

    with (csv_dir / "factor_analysis.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        rows = list(csv.DictReader(handle))
    assert [row["factor"] for row in rows] == ["A", "B", "C"]
    assert [row["level"] for row in rows] == ["3", "2", "1"]


def test_committed_ssim_template_contains_no_invented_responses():
    template = (
        Path(__file__).resolve().parents[1]
        / "data"
        / "templates"
        / "ism_ssim_template.csv"
    )
    with template.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.reader(handle))
    assert rows == [["factor_i", "factor_j", "relation"]]
