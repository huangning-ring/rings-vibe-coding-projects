#!/usr/bin/env python3
"""Personal Format — safe, deterministic Markdown normalization."""

from __future__ import annotations

import argparse
import codecs
import difflib
import os
import re
import shutil
import sys
import tempfile
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Iterable


YAML_SCAN_LINES = 15
HEADING_RE = re.compile(r"^(#{1,6})[ \t]+(.+?)\s*$")
EMPTY_QUOTE_RE = re.compile(r"^>\s*$")
FENCE_OPEN_RE = re.compile(r"^(\s*)(`{3,}|~{3,})(.*)$")


class FormatError(Exception):
    """A safe formatting precondition was not met."""


@dataclass
class ChangeSummary:
    line_endings_normalized: int = 0
    bom_removed: int = 0
    dividers_replaced: int = 0
    blank_lines_removed: int = 0
    empty_quote_lines_removed: int = 0
    table_blank_lines_inserted: int = 0
    callout_blank_lines_inserted: int = 0
    mermaid_literal_newlines_expanded: int = 0
    first_h1_removed: int = 0
    headings_promoted: int = 0

    def report(self) -> str:
        labels = {
            "line_endings_normalized": "line_endings",
            "bom_removed": "bom_removed",
            "dividers_replaced": "dividers",
            "blank_lines_removed": "blank_lines_removed",
            "empty_quote_lines_removed": "empty_quote_lines_removed",
            "table_blank_lines_inserted": "table_blanks_added",
            "callout_blank_lines_inserted": "callout_blanks_added",
            "mermaid_literal_newlines_expanded": "mermaid_literal_newlines",
            "first_h1_removed": "h1_removed",
            "headings_promoted": "headings_promoted",
        }
        return ", ".join(f"{labels[item.name]}={getattr(self, item.name)}" for item in fields(self))


@dataclass(frozen=True)
class H1Candidate:
    line_number: int
    title: str
    reason: str


@dataclass(frozen=True)
class FenceBlock:
    start: int
    end: int
    marker: str
    marker_length: int
    is_mermaid: bool
    closed: bool


@dataclass
class TransformResult:
    content: str
    summary: ChangeSummary
    h1_candidate: H1Candidate | None


@dataclass
class SourceDocument:
    raw_bytes: bytes
    content: str
    summary: ChangeSummary


@dataclass
class FileResult:
    path: Path
    status: str
    changed: bool = False
    summary: ChangeSummary | None = None
    candidate: H1Candidate | None = None
    diff: str = ""
    error: str = ""


def read_source(path: Path) -> SourceDocument:
    raw = path.read_bytes()
    had_bom = raw.startswith(codecs.BOM_UTF8)
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise FormatError(f"不是有效的 UTF-8 文件：{exc}") from exc

    crlf_count = text.count("\r\n")
    without_crlf = text.replace("\r\n", "\n")
    lone_cr_count = without_crlf.count("\r")
    normalized = without_crlf.replace("\r", "\n")
    return SourceDocument(
        raw_bytes=raw,
        content=normalized,
        summary=ChangeSummary(
            line_endings_normalized=crlf_count + lone_cr_count,
            bom_removed=int(had_bom),
        ),
    )


def _detect_frontmatter(lines: list[str]) -> tuple[int, int] | None:
    window_end = min(YAML_SCAN_LINES, len(lines))
    first_nonempty = next((i for i in range(window_end) if lines[i].strip()), None)
    if first_nonempty is None or lines[first_nonempty].strip() != "---":
        return None

    for i in range(first_nonempty + 1, window_end):
        if lines[i].strip() == "---":
            return first_nonempty, i
    raise FormatError("疑似 YAML frontmatter，但结束分隔线未出现在文件前15个物理行内")


def _is_fence_close(line: str, marker: str, marker_length: int) -> bool:
    pattern = rf"^\s*{re.escape(marker)}{{{marker_length},}}\s*$"
    return bool(re.match(pattern, line))


def _find_fence_blocks(
    lines: list[str], frontmatter: tuple[int, int] | None
) -> list[FenceBlock]:
    blocks: list[FenceBlock] = []
    i = 0
    yaml_start, yaml_end = frontmatter if frontmatter else (-1, -1)
    while i < len(lines):
        if yaml_start <= i <= yaml_end:
            i += 1
            continue
        match = FENCE_OPEN_RE.match(lines[i])
        if not match:
            i += 1
            continue

        marker_text = match.group(2)
        marker = marker_text[0]
        marker_length = len(marker_text)
        info = match.group(3).strip()
        language = info.split(maxsplit=1)[0].lower() if info else ""
        is_mermaid = language == "mermaid"
        end = len(lines) - 1
        closed = False
        j = i + 1
        while j < len(lines):
            if _is_fence_close(lines[j], marker, marker_length):
                end = j
                closed = True
                break
            j += 1
        blocks.append(
            FenceBlock(
                start=i,
                end=end,
                marker=marker,
                marker_length=marker_length,
                is_mermaid=is_mermaid,
                closed=closed,
            )
        )
        i = end + 1
    return blocks


def _protected_kinds(
    line_count: int,
    frontmatter: tuple[int, int] | None,
    fences: Iterable[FenceBlock],
) -> list[str | None]:
    kinds: list[str | None] = [None] * line_count
    if frontmatter:
        for i in range(frontmatter[0], frontmatter[1] + 1):
            kinds[i] = "yaml"
    for block in fences:
        kind = "mermaid" if block.is_mermaid else "code"
        for i in range(block.start, block.end + 1):
            kinds[i] = kind
    return kinds


def _apply_inline_code_protection(
    lines: list[str], kinds: list[str | None]
) -> list[str | None]:
    """Protect lines whose structural-looking content is wholly inside code spans."""
    protected = kinds.copy()
    delimiter_length: int | None = None
    for i, line in enumerate(lines):
        if kinds[i] is not None:
            delimiter_length = None
            continue

        mask = [False] * len(line)
        active_at_start = delimiter_length is not None
        j = 0
        while j < len(line):
            if line[j] != "`":
                if delimiter_length is not None:
                    mask[j] = True
                j += 1
                continue

            end = j + 1
            while end < len(line) and line[end] == "`":
                end += 1
            run_length = end - j
            if delimiter_length is None:
                delimiter_length = run_length
                for k in range(j, end):
                    mask[k] = True
            elif run_length == delimiter_length:
                for k in range(j, end):
                    mask[k] = True
                delimiter_length = None
            else:
                for k in range(j, end):
                    mask[k] = True
            j = end

        nonspace_indices = [index for index, char in enumerate(line) if not char.isspace()]
        entirely_inside_code = bool(nonspace_indices) and all(mask[index] for index in nonspace_indices)
        blank_inside_code = not nonspace_indices and active_at_start
        if entirely_inside_code or blank_inside_code:
            protected[i] = "inline-code"
    return protected


def _expand_mermaid_literal_newlines(
    lines: list[str],
    fences: list[FenceBlock],
    summary: ChangeSummary,
) -> list[str]:
    content_indices: set[int] = set()
    for block in fences:
        if not block.is_mermaid:
            continue
        end = block.end if block.closed else block.end + 1
        content_indices.update(range(block.start + 1, end))

    expanded: list[str] = []
    for i, line in enumerate(lines):
        if i not in content_indices:
            expanded.append(line)
            continue
        count = line.count("\\n")
        summary.mermaid_literal_newlines_expanded += count
        expanded.extend(line.replace("\\n", "\n").split("\n"))
    return expanded


def _headings(lines: list[str], kinds: list[str | None]) -> list[tuple[int, int, str]]:
    found: list[tuple[int, int, str]] = []
    for i, line in enumerate(lines):
        if kinds[i] is not None:
            continue
        match = HEADING_RE.match(line)
        if match:
            found.append((i, len(match.group(1)), match.group(2)))
    return found


def _analyze_h1(headings: list[tuple[int, int, str]]) -> H1Candidate | None:
    first_h1_position = next((i for i, item in enumerate(headings) if item[1] == 1), None)
    if first_h1_position is None:
        return None
    first_h1 = headings[first_h1_position]
    later = headings[first_h1_position + 1 :]
    if any(level == 1 for _, level, _ in later):
        reason = "首个 H1 后仍有其他 H1"
    elif any(level >= 2 for _, level, _ in later):
        reason = "全文由 H2–H6 承担后续分节"
    else:
        return None
    return H1Candidate(line_number=first_h1[0] + 1, title=first_h1[2], reason=reason)


def _remove_h1_and_maybe_promote(
    lines: list[str],
    kinds: list[str | None],
    headings: list[tuple[int, int, str]],
    candidate: H1Candidate | None,
    summary: ChangeSummary,
) -> list[str]:
    if candidate is None:
        raise FormatError("--remove-first-h1 只能用于存在后续分节标题的候选 H1")

    first_h1 = next(item for item in headings if item[1] == 1)
    first_h1_index = first_h1[0]
    remaining_h1 = any(i != first_h1_index and level == 1 for i, level, _ in headings)
    heading_by_line = {i: (level, title) for i, level, title in headings}

    output: list[str] = []
    for i, line in enumerate(lines):
        if i == first_h1_index:
            summary.first_h1_removed += 1
            continue
        if not remaining_h1 and kinds[i] is None and i in heading_by_line:
            level, title = heading_by_line[i]
            if level >= 2:
                line = f"{'#' * (level - 1)} {title}"
                summary.headings_promoted += 1
        output.append(line)
    return output


def _is_table_row(line: str, kind: str | None) -> bool:
    return kind is None and line.startswith("|")


def _is_table_start(lines: list[str], kinds: list[str | None], index: int) -> bool:
    if index < 0 or index >= len(lines) or not _is_table_row(lines[index], kinds[index]):
        return False
    if index > 0 and _is_table_row(lines[index - 1], kinds[index - 1]):
        return False
    count = 0
    i = index
    while i < len(lines) and _is_table_row(lines[i], kinds[i]):
        count += 1
        i += 1
    return count >= 2


def _remove_empty_quote_lines(
    lines: list[str], kinds: list[str | None], summary: ChangeSummary
) -> list[str]:
    output: list[str] = []
    for i, line in enumerate(lines):
        if kinds[i] is None and EMPTY_QUOTE_RE.match(line):
            summary.empty_quote_lines_removed += 1
            continue
        output.append(line)
    return output


def _canonicalize_blank_runs(
    lines: list[str], kinds: list[str | None], summary: ChangeSummary
) -> list[str]:
    output: list[str] = []
    i = 0
    while i < len(lines):
        if kinds[i] is not None or lines[i].strip():
            output.append(lines[i])
            i += 1
            continue

        start = i
        while i < len(lines) and kinds[i] is None and not lines[i].strip():
            i += 1
        run_length = i - start
        previous_is_quote = start > 0 and kinds[start - 1] is None and lines[start - 1].startswith(">")
        next_is_table = i < len(lines) and _is_table_start(lines, kinds, i)
        next_exists = i < len(lines)
        keep_one = next_is_table or (previous_is_quote and next_exists)
        if keep_one:
            output.append("")
        summary.blank_lines_removed += run_length - int(keep_one)
    return output


def _insert_table_blanks(
    lines: list[str], kinds: list[str | None], summary: ChangeSummary
) -> list[str]:
    output: list[str] = []
    for i, line in enumerate(lines):
        if _is_table_start(lines, kinds, i) and output and output[-1].strip():
            output.append("")
            summary.table_blank_lines_inserted += 1
        output.append(line)
    return output


def _insert_quote_blanks(
    lines: list[str], kinds: list[str | None], summary: ChangeSummary
) -> list[str]:
    output: list[str] = []
    i = 0
    while i < len(lines):
        if kinds[i] is None and lines[i].startswith(">"):
            while i < len(lines) and kinds[i] is None and lines[i].startswith(">"):
                output.append(lines[i])
                i += 1
            if (
                i < len(lines)
                and lines[i].strip()
                and not _is_table_start(lines, kinds, i)
            ):
                output.append("")
                summary.callout_blank_lines_inserted += 1
            continue
        output.append(lines[i])
        i += 1
    return output


def _structure(lines: list[str]) -> tuple[tuple[int, int] | None, list[FenceBlock], list[str | None]]:
    frontmatter = _detect_frontmatter(lines)
    fences = _find_fence_blocks(lines, frontmatter)
    kinds = _protected_kinds(len(lines), frontmatter, fences)
    kinds = _apply_inline_code_protection(lines, kinds)
    return frontmatter, fences, kinds


def transform_content(
    content: str,
    *,
    remove_first_h1: bool = False,
    initial_summary: ChangeSummary | None = None,
) -> TransformResult:
    summary = initial_summary or ChangeSummary()
    lines = content.split("\n")

    frontmatter, fences, kinds = _structure(lines)
    lines = _expand_mermaid_literal_newlines(lines, fences, summary)
    frontmatter, fences, kinds = _structure(lines)

    headings = _headings(lines, kinds)
    candidate = _analyze_h1(headings)
    if remove_first_h1:
        lines = _remove_h1_and_maybe_promote(lines, kinds, headings, candidate, summary)
        frontmatter, fences, kinds = _structure(lines)

    for i, line in enumerate(lines):
        if kinds[i] is None and line.strip() == "---":
            lines[i] = "***"
            summary.dividers_replaced += 1

    frontmatter, fences, kinds = _structure(lines)
    lines = _remove_empty_quote_lines(lines, kinds, summary)
    frontmatter, fences, kinds = _structure(lines)
    lines = _canonicalize_blank_runs(lines, kinds, summary)
    frontmatter, fences, kinds = _structure(lines)
    lines = _insert_table_blanks(lines, kinds, summary)
    frontmatter, fences, kinds = _structure(lines)
    lines = _insert_quote_blanks(lines, kinds, summary)

    return TransformResult(content="\n".join(lines), summary=summary, h1_candidate=candidate)


def _unified_diff(before: str, after: str, path: Path) -> str:
    return "".join(
        difflib.unified_diff(
            before.splitlines(keepends=True),
            after.splitlines(keepends=True),
            fromfile=f"a/{path}",
            tofile=f"b/{path}",
            lineterm="\n",
        )
    )


def _validate_temp_file(path: Path, expected_content: str) -> None:
    raw = path.read_bytes()
    if raw.startswith(codecs.BOM_UTF8):
        raise FormatError("临时输出意外包含 UTF-8 BOM")
    try:
        decoded = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise FormatError(f"临时输出不是有效 UTF-8：{exc}") from exc
    if decoded != expected_content:
        raise FormatError("临时输出回读结果与预期不一致")
    second_pass = transform_content(decoded)
    if second_pass.content != expected_content:
        raise FormatError("格式化结果未通过幂等性验证")


def _atomic_write(path: Path, content: str) -> None:
    temp_path: Path | None = None
    try:
        descriptor, temp_name = tempfile.mkstemp(
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
        )
        temp_path = Path(temp_name)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content.encode("utf-8"))
            handle.flush()
            os.fsync(handle.fileno())
        if path.exists():
            shutil.copymode(path, temp_path)
        _validate_temp_file(temp_path, content)
        os.replace(temp_path, path)
        temp_path = None
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()


def format_file(
    path: Path,
    *,
    dry_run: bool = False,
    backup: bool = False,
    remove_first_h1: bool = False,
) -> FileResult:
    try:
        source = read_source(path)
        if not source.content.strip():
            return FileResult(path=path, status="skipped")
        transformed = transform_content(
            source.content,
            remove_first_h1=remove_first_h1,
            initial_summary=source.summary,
        )
        desired_bytes = transformed.content.encode("utf-8")
        changed = desired_bytes != source.raw_bytes
        diff = _unified_diff(source.content, transformed.content, path) if changed else ""
        if changed and not dry_run:
            if backup:
                shutil.copy2(path, Path(f"{path}.bak"))
            _atomic_write(path, transformed.content)
        return FileResult(
            path=path,
            status="modified" if changed else "unchanged",
            changed=changed,
            summary=transformed.summary,
            candidate=transformed.h1_candidate,
            diff=diff,
        )
    except (OSError, FormatError) as exc:
        return FileResult(path=path, status="failed", error=str(exc))


def _print_file_result(result: FileResult, *, dry_run: bool, remove_first_h1: bool) -> None:
    if result.status == "failed":
        print(f"[ERR] {result.path} — {result.error}", file=sys.stderr)
        return
    if result.status == "skipped":
        print(f"[Skip] {result.path} — 空文件或仅含空白")
        return

    prefix = "[Preview]" if dry_run and result.changed else "[OK]"
    state = "将发生修改" if dry_run and result.changed else ("已修改" if result.changed else "无需更改")
    print(f"{prefix} {result.path} — {state}")
    if result.summary is not None:
        print(f"   stats: {result.summary.report()}")
    if dry_run and result.diff:
        print(result.diff, end="" if result.diff.endswith("\n") else "\n")
    if result.candidate is not None and not remove_first_h1:
        print(
            "H1_CONFIRMATION_REQUIRED "
            f"{result.path}:{result.candidate.line_number} "
            f"“{result.candidate.title}” — {result.candidate.reason}；"
            "如确认删除，请使用 --remove-first-h1"
        )


def _iter_markdown_files(path: Path) -> list[Path]:
    return sorted(item for item in path.rglob("*.md") if item.is_file())


def _directory_summary(results: list[FileResult]) -> str:
    modified = sum(result.status == "modified" for result in results)
    unchanged = sum(result.status == "unchanged" for result in results)
    skipped = sum(result.status == "skipped" for result in results)
    failed = sum(result.status == "failed" for result in results)
    successful = modified + unchanged
    return (
        f"total={len(results)}, success={successful}, modified={modified}, "
        f"unchanged={unchanged}, skipped={skipped}, failed={failed}"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Personal Format — 安全 Markdown 格式标准化")
    parser.add_argument("path", help="要处理的 Markdown 文件或目录")
    parser.add_argument("--dry-run", action="store_true", help="输出完整差异，不写入文件")
    parser.add_argument("--backup", action="store_true", help="修改前创建同目录 .bak 备份")
    parser.add_argument(
        "--remove-first-h1",
        action="store_true",
        help="经用户确认后删除候选首个 H1，并在必要时提升其余标题",
    )
    args = parser.parse_args(argv)
    target = Path(args.path)

    if target.is_file():
        result = format_file(
            target,
            dry_run=args.dry_run,
            backup=args.backup,
            remove_first_h1=args.remove_first_h1,
        )
        _print_file_result(result, dry_run=args.dry_run, remove_first_h1=args.remove_first_h1)
        return int(result.status == "failed")

    if target.is_dir():
        files = _iter_markdown_files(target)
        results = [
            format_file(
                file,
                dry_run=args.dry_run,
                backup=args.backup,
                remove_first_h1=args.remove_first_h1,
            )
            for file in files
        ]
        for result in results:
            _print_file_result(result, dry_run=args.dry_run, remove_first_h1=args.remove_first_h1)
        print(f"[Summary] {_directory_summary(results)}")
        return int(any(result.status == "failed" for result in results))

    print(f"[ERR] 路径不存在：{target}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
