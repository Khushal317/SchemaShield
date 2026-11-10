from __future__ import annotations

import ast
from pathlib import Path

import sqlglot

from backend.code_models import AnalysisWarning, CodeAnalysisResult, SqlQueryReference
from backend.sql_analyzer import parse_sql_query, query_reference_from_expression


SQL_START_WORDS = {"SELECT", "INSERT", "UPDATE", "DELETE", "WITH"}
IGNORED_DIRECTORIES = {".git", ".venv", "__pycache__"}


def scan_project(project_path: str | Path) -> CodeAnalysisResult:
    """Scan Python and standalone SQL files without executing project code."""
    root = Path(project_path).resolve()
    if not root.is_dir():
        raise ValueError(f"Project path is not a directory: {root}")

    queries: list[SqlQueryReference] = []
    warnings: list[AnalysisWarning] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or _is_ignored(path.relative_to(root)):
            continue
        if path.suffix.lower() == ".py":
            file_queries, file_warnings = _scan_python_file(path, root)
        elif path.suffix.lower() == ".sql":
            file_queries, file_warnings = _scan_sql_file(path, root)
        else:
            continue
        queries.extend(file_queries)
        warnings.extend(file_warnings)

    return CodeAnalysisResult(
        queries=tuple(sorted(queries, key=lambda item: item.query_id)),
        warnings=tuple(
            sorted(
                warnings,
                key=lambda item: (
                    item.source_file,
                    item.function_name or "",
                    item.query_id or "",
                ),
            )
        ),
    )


def _scan_python_file(
    path: Path,
    root: Path,
) -> tuple[list[SqlQueryReference], list[AnalysisWarning]]:
    source_file = path.relative_to(root).as_posix()
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=source_file)
    except (OSError, UnicodeDecodeError, SyntaxError) as error:
        return [], [AnalysisWarning(source_file=source_file, message=str(error))]

    module_queries = _module_sql_constants(tree)
    used_constants: set[str] = set()
    queries: list[SqlQueryReference] = []
    warnings: list[AnalysisWarning] = []

    functions = [
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    for function in functions:
        dynamic_sql_lines = {
            node.lineno
            for node in ast.walk(function)
            if isinstance(node, (ast.JoinedStr, ast.BinOp))
            and _looks_like_dynamic_sql(node)
        }
        for line_number in sorted(dynamic_sql_lines):
            warnings.append(
                AnalysisWarning(
                    source_file=source_file,
                    function_name=function.name,
                    query_id=f"{source_file}:{function.name}:line-{line_number}",
                    message="Dynamic SQL cannot be resolved statically",
                )
            )

        referenced_names = {
            node.id
            for node in ast.walk(function)
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)
        }
        for constant_name in sorted(referenced_names & module_queries.keys()):
            used_constants.add(constant_name)
            query_id = f"{source_file}:{function.name}:{constant_name}"
            _parse_or_warn(
                module_queries[constant_name],
                query_id,
                source_file,
                function.name,
                queries,
                warnings,
            )

        for node in ast.walk(function):
            if (
                isinstance(node, ast.Constant)
                and isinstance(node.value, str)
                and _looks_like_sql(node.value)
                and node.lineno not in dynamic_sql_lines
            ):
                query_id = f"{source_file}:{function.name}:line-{node.lineno}"
                _parse_or_warn(
                    node.value,
                    query_id,
                    source_file,
                    function.name,
                    queries,
                    warnings,
                )

    for constant_name in sorted(module_queries.keys() - used_constants):
        query_id = f"{source_file}:<module>:{constant_name}"
        _parse_or_warn(
            module_queries[constant_name],
            query_id,
            source_file,
            None,
            queries,
            warnings,
        )

    for node in tree.body:
        value = None
        if isinstance(node, ast.Assign):
            value = node.value
        elif isinstance(node, ast.AnnAssign):
            value = node.value
        if value is not None and _looks_like_dynamic_sql(value):
            warnings.append(
                AnalysisWarning(
                    source_file=source_file,
                    query_id=f"{source_file}:<module>:line-{value.lineno}",
                    message="Dynamic SQL cannot be resolved statically",
                )
            )

    return queries, warnings


def _scan_sql_file(
    path: Path,
    root: Path,
) -> tuple[list[SqlQueryReference], list[AnalysisWarning]]:
    source_file = path.relative_to(root).as_posix()
    try:
        sql = path.read_text(encoding="utf-8")
        expressions = sqlglot.parse(sql, read="postgres")
    except (OSError, UnicodeDecodeError, sqlglot.errors.ParseError) as error:
        return [], [AnalysisWarning(source_file=source_file, message=str(error))]

    queries = []
    for index, expression in enumerate(expressions, start=1):
        if expression is None:
            continue
        queries.append(
            query_reference_from_expression(
                expression,
                sql=expression.sql(dialect="postgres"),
                query_id=f"{source_file}#{index}",
                source_file=source_file,
                function_name=None,
            )
        )
    return queries, []


def _module_sql_constants(tree: ast.Module) -> dict[str, str]:
    queries = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant):
            if isinstance(node.value.value, str) and _looks_like_sql(node.value.value):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        queries[target.id] = node.value.value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.value, ast.Constant):
            if (
                isinstance(node.target, ast.Name)
                and isinstance(node.value.value, str)
                and _looks_like_sql(node.value.value)
            ):
                queries[node.target.id] = node.value.value
    return queries


def _looks_like_sql(value: str) -> bool:
    stripped = value.lstrip()
    if not stripped:
        return False
    return stripped.split(None, 1)[0].upper() in SQL_START_WORDS


def _looks_like_dynamic_sql(node: ast.AST) -> bool:
    if isinstance(node, ast.JoinedStr):
        static_text = "".join(
            value.value
            for value in node.values
            if isinstance(value, ast.Constant) and isinstance(value.value, str)
        )
        return _looks_like_sql(static_text)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        static_parts = [
            child.value
            for child in ast.walk(node)
            if isinstance(child, ast.Constant) and isinstance(child.value, str)
        ]
        return _looks_like_sql("".join(static_parts))
    return False


def _parse_or_warn(
    sql: str,
    query_id: str,
    source_file: str,
    function_name: str | None,
    queries: list[SqlQueryReference],
    warnings: list[AnalysisWarning],
) -> None:
    try:
        queries.append(
            parse_sql_query(
                sql,
                query_id=query_id,
                source_file=source_file,
                function_name=function_name,
            )
        )
    except sqlglot.errors.ParseError as error:
        warnings.append(
            AnalysisWarning(
                source_file=source_file,
                function_name=function_name,
                query_id=query_id,
                message=str(error),
            )
        )


def _is_ignored(relative_path: Path) -> bool:
    return any(
        part in IGNORED_DIRECTORIES or part.startswith(".")
        for part in relative_path.parts[:-1]
    )
