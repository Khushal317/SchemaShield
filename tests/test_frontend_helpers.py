import pytest

from frontend import app


class FakeResponse:
    def __init__(self, body, ok=True):
        self.body = body
        self.ok = ok

    def json(self):
        return self.body


def test_api_request_returns_json_object(monkeypatch):
    monkeypatch.setattr(
        app.requests,
        "request",
        lambda *args, **kwargs: FakeResponse({"status": "ok"}),
    )

    assert app.api_request("GET", "http://localhost:8000/health") == {
        "status": "ok"
    }


def test_api_request_uses_structured_backend_error(monkeypatch):
    monkeypatch.setattr(
        app.requests,
        "request",
        lambda *args, **kwargs: FakeResponse(
            {"detail": {"code": "database_error", "message": "Database unavailable"}},
            ok=False,
        ),
    )

    with pytest.raises(app.ApiClientError, match="Database unavailable"):
        app.api_request("POST", "http://localhost:8000/analysis/run", {})


def test_build_impact_rows_shows_affected_and_unaffected_changes():
    rows = app.build_impact_rows(
        {
            "findings": [
                {
                    "database_object": "customers.full_name",
                    "severity": "high",
                    "affected_code": [
                        {
                            "source_file": "customer_repository.py",
                            "function_name": "get_customer_profile",
                            "statement_type": "SELECT",
                        }
                    ],
                },
                {
                    "database_object": "customers.is_active",
                    "severity": "low",
                    "affected_code": [],
                },
            ]
        }
    )

    assert rows == [
        {
            "database_object": "customers.full_name",
            "severity": "high",
            "source_file": "customer_repository.py",
            "function": "get_customer_profile",
            "query_type": "SELECT",
        },
        {
            "database_object": "customers.is_active",
            "severity": "low",
            "source_file": "",
            "function": "",
            "query_type": "",
        },
    ]

