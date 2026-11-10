from backend.evaluation import evaluate_detection, verify_impacts


def test_perfect_detection_metrics_include_explicit_true_negatives():
    changes = [
        {"change_type": "table_added", "table": "audit_logs"},
        {
            "change_type": "column_removed",
            "table": "customers",
            "column": "phone",
        },
    ]

    metrics = evaluate_detection(
        changes,
        changes,
        ["customers.id", "orders.id"],
        processing_time_ms=12.3456,
    )

    assert metrics.true_positives == 2
    assert metrics.true_negatives == 2
    assert metrics.false_positives == 0
    assert metrics.false_negatives == 0
    assert metrics.accuracy == 1.0
    assert metrics.precision == 1.0
    assert metrics.recall == 1.0
    assert metrics.false_positive_rate == 0.0
    assert metrics.processing_time_ms == 12.346


def test_detection_metrics_count_missing_and_false_changes():
    expected = [
        {"change_type": "table_added", "table": "audit_logs"},
        {
            "change_type": "column_removed",
            "table": "customers",
            "column": "phone",
        },
    ]
    predicted = [
        {"change_type": "table_added", "table": "audit_logs"},
        {
            "change_type": "column_modified",
            "table": "customers",
            "column": "id",
            "property": "is_nullable",
            "old_value": False,
            "new_value": True,
        },
    ]

    metrics = evaluate_detection(
        predicted,
        expected,
        ["customers.id", "orders.id"],
        processing_time_ms=5,
    )

    assert metrics.true_positives == 1
    assert metrics.true_negatives == 1
    assert metrics.false_positives == 1
    assert metrics.false_negatives == 1
    assert metrics.accuracy == 0.5
    assert metrics.precision == 0.5
    assert metrics.recall == 0.5
    assert metrics.false_positive_rate == 0.5


def test_impact_verification_reports_exact_links():
    predicted = [
        {
            "database_object": "customers.phone",
            "affected_code": [
                {
                    "source_file": "customer_repository.py",
                    "function_name": "get_customer_profile",
                }
            ],
        }
    ]
    expected = [
        {
            "database_object": "customers.phone",
            "references": [
                {
                    "source_file": "customer_repository.py",
                    "function_name": "get_customer_profile",
                }
            ],
        }
    ]

    verification = verify_impacts(predicted, expected)

    assert verification.passed is True
    assert verification.expected_links == 1
    assert verification.matched_links == 1
