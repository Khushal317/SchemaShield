from __future__ import annotations

import json
from typing import Any

import requests
import streamlit as st


DEFAULT_API_URL = "http://localhost:8000"


class ApiClientError(RuntimeError):
    pass


def api_request(
    method: str,
    url: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    try:
        response = requests.request(method, url, json=payload, timeout=60)
    except requests.RequestException as error:
        raise ApiClientError(f"Could not reach the FastAPI backend: {error}") from error

    try:
        body = response.json()
    except ValueError:
        body = {}

    if not response.ok:
        detail = body.get("detail", {}) if isinstance(body, dict) else {}
        if isinstance(detail, dict):
            message = detail.get("message", "The backend returned an error")
        else:
            message = str(detail) or "The backend returned an error"
        raise ApiClientError(message)
    if not isinstance(body, dict):
        raise ApiClientError("The backend returned an invalid response")
    return body


def build_impact_rows(report: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for finding in report.get("findings", []):
        affected_code = finding.get("affected_code", [])
        if not affected_code:
            rows.append(
                {
                    "database_object": finding.get("database_object", ""),
                    "severity": finding.get("severity", ""),
                    "source_file": "",
                    "function": "",
                    "query_type": "",
                }
            )
            continue
        for item in affected_code:
            rows.append(
                {
                    "database_object": finding.get("database_object", ""),
                    "severity": finding.get("severity", ""),
                    "source_file": item.get("source_file", ""),
                    "function": item.get("function_name", ""),
                    "query_type": item.get("statement_type", ""),
                }
            )
    return rows


def main() -> None:
    st.set_page_config(page_title="SchemaShield", layout="wide")
    st.title("SchemaShield")
    st.write("Detect PostgreSQL schema drift and find potentially affected Python code.")

    api_url = st.sidebar.text_input("FastAPI URL", DEFAULT_API_URL).rstrip("/")
    database_url = st.text_input(
        "PostgreSQL URL",
        value="postgresql+psycopg://postgres:postgres@localhost:5432/schemashield_demo",
        type="password",
    )
    schema_name = st.text_input("Schema name", value="schemashield_demo")
    project_path = st.text_input("Python project folder", value="samples/python_project")
    baseline_path = st.text_input("Baseline JSON file", value="baseline.json")

    request_data = {
        "database_url": database_url,
        "schema_name": schema_name,
        "baseline_path": baseline_path,
    }

    baseline_column, analysis_column = st.columns(2)
    with baseline_column:
        if st.button("Capture baseline", use_container_width=True):
            try:
                result = api_request(
                    "POST",
                    f"{api_url}/baseline/capture",
                    request_data,
                )
                st.success(
                    f"Saved {result['table_count']} tables to {result['baseline_path']}"
                )
            except ApiClientError as error:
                st.error(str(error))

    with analysis_column:
        if st.button("Run drift detection", use_container_width=True):
            try:
                report = api_request(
                    "POST",
                    f"{api_url}/analysis/run",
                    {**request_data, "project_path": project_path},
                )
                st.session_state["drift_report"] = report
            except ApiClientError as error:
                st.error(str(error))

    report = st.session_state.get("drift_report")
    if report:
        st.subheader("Schema changes")
        changes = report.get("changes", [])
        if changes:
            st.dataframe(changes, use_container_width=True, hide_index=True)
        else:
            st.success("No schema drift detected")

        st.subheader("Affected code")
        impact_rows = build_impact_rows(report)
        if impact_rows:
            st.dataframe(impact_rows, use_container_width=True, hide_index=True)
        else:
            st.info("No affected code was found")

        warnings = report.get("warnings", [])
        if warnings:
            st.subheader("Analysis warnings")
            st.dataframe(warnings, use_container_width=True, hide_index=True)

        st.download_button(
            "Download drift report",
            data=json.dumps(report, indent=2),
            file_name="schemashield_drift_report.json",
            mime="application/json",
        )


if __name__ == "__main__":
    main()

