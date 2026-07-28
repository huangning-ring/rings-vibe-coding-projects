from __future__ import annotations

import codecs
import contextlib
import importlib.util
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT_PATH = Path(__file__).parents[1] / "scripts" / "personal_format.py"
SPEC = importlib.util.spec_from_file_location("personal_format_under_test", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
pf = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = pf
SPEC.loader.exec_module(pf)


class TransformTests(unittest.TestCase):
    def test_short_chinese_h1_is_preserved_and_reported(self) -> None:
        source = "# 怎么用\n\n## 第一节\n内容\n"
        result = pf.transform_content(source)
        self.assertIn("# 怎么用", result.content)
        self.assertIn("## 第一节", result.content)
        self.assertEqual(result.h1_candidate.title, "怎么用")
        self.assertEqual(result.summary.first_h1_removed, 0)

    def test_multiple_h1_default_preserves_every_heading(self) -> None:
        source = "# 文档标题\n正文\n# 第一章\n内容\n# 第二章\n内容"
        result = pf.transform_content(source)
        self.assertEqual(result.content, source)
        self.assertEqual(result.h1_candidate.reason, "首个 H1 后仍有其他 H1")

    def test_multiple_h1_confirmed_removal_does_not_promote(self) -> None:
        source = "# 文档标题\n正文\n# 第一章\n## 小节\n# 第二章"
        result = pf.transform_content(source, remove_first_h1=True)
        self.assertNotIn("# 文档标题", result.content)
        self.assertIn("# 第一章", result.content)
        self.assertIn("## 小节", result.content)
        self.assertIn("# 第二章", result.content)
        self.assertEqual(result.summary.first_h1_removed, 1)
        self.assertEqual(result.summary.headings_promoted, 0)

    def test_only_h1_with_lower_sections_is_removed_and_promoted(self) -> None:
        source = "# 文档标题\n引言\n## 第一节\n### 细节\n## 第二节"
        result = pf.transform_content(source, remove_first_h1=True)
        self.assertNotIn("# 文档标题", result.content)
        self.assertIn("# 第一节", result.content)
        self.assertIn("## 细节", result.content)
        self.assertIn("# 第二节", result.content)
        self.assertEqual(result.summary.headings_promoted, 3)

    def test_h1_without_later_headings_cannot_be_removed(self) -> None:
        source = "# 唯一标题\n正文"
        with self.assertRaisesRegex(pf.FormatError, "候选 H1"):
            pf.transform_content(source, remove_first_h1=True)

    def test_headings_in_yaml_and_code_are_never_candidates(self) -> None:
        source = (
            "---\n"
            "title: '# YAML title'\n"
            "---\n"
            "# 正文标题\n"
            "```text\n"
            "# code heading\n"
            "## code child\n"
            "```"
        )
        result = pf.transform_content(source)
        self.assertIsNone(result.h1_candidate)
        self.assertIn("# code heading", result.content)
        self.assertIn("## code child", result.content)

    def test_yaml_closing_delimiter_may_be_on_line_15(self) -> None:
        lines = ["---"] + [f"k{i}: v" for i in range(1, 14)] + ["---", "# 标题", "---"]
        result = pf.transform_content("\n".join(lines))
        self.assertEqual(result.content.splitlines()[14], "---")
        self.assertEqual(result.content.splitlines()[-1], "***")

    def test_yaml_closing_delimiter_on_line_16_is_rejected(self) -> None:
        lines = ["---"] + [f"k{i}: v" for i in range(1, 15)] + ["---", "# 标题"]
        with self.assertRaisesRegex(pf.FormatError, "前15个物理行"):
            pf.transform_content("\n".join(lines))

    def test_yaml_dividers_and_blank_lines_are_preserved(self) -> None:
        source = "---\ntitle: x\n\nvalue: '---'\n---\n正文\n---"
        result = pf.transform_content(source)
        self.assertTrue(result.content.startswith("---\ntitle: x\n\nvalue: '---'\n---"))
        self.assertTrue(result.content.endswith("正文\n***"))

    def test_code_blocks_are_protected_and_only_mermaid_expands_literal_newline(self) -> None:
        source = (
            "# 标题\n"
            "```python\n"
            "---\n"
            "# code heading\n"
            "value = \"\\n\"\n"
            "\n"
            "```\n"
            "```mermaid\n"
            "A\\nB\\n\\nC\n"
            "```\n"
            "正文 \\n 和 `\\n`\n"
            "---"
        )
        result = pf.transform_content(source)
        self.assertIn("```python\n---\n# code heading\nvalue = \"\\n\"\n\n```", result.content)
        self.assertIn("```mermaid\nA\nB\n\nC\n```", result.content)
        self.assertIn("正文 \\n 和 `\\n`", result.content)
        self.assertTrue(result.content.endswith("***"))
        self.assertEqual(result.summary.mermaid_literal_newlines_expanded, 3)

    def test_tilde_fence_is_protected(self) -> None:
        source = "~~~text\n---\n# heading\n~~~\n---"
        result = pf.transform_content(source)
        self.assertEqual(result.content, "~~~text\n---\n# heading\n~~~\n***")

    def test_multiline_inline_code_span_protects_blank_divider_and_heading(self) -> None:
        source = "`code starts\n---\n# not a heading\n\ncode ends`\n---"
        result = pf.transform_content(source)
        self.assertEqual(result.content, "`code starts\n---\n# not a heading\n\ncode ends`\n***")
        self.assertIsNone(result.h1_candidate)

    def test_heading_with_single_line_inline_code_still_participates(self) -> None:
        source = "# Use `code`\n## Child `value`"
        result = pf.transform_content(source)
        self.assertEqual(result.h1_candidate.title, "Use `code`")
        removed = pf.transform_content(source, remove_first_h1=True)
        self.assertEqual(removed.content, "# Child `value`")

    def test_table_and_quote_spacing_is_canonical_and_idempotent(self) -> None:
        source = (
            "正文\n\n\n"
            "| A | B |\n"
            "|---|---|\n"
            "| 1 | 2 |\n\n\n"
            "> ordinary quote\n"
            ">\n"
            "> continued\n\n\n"
            "结尾"
        )
        first = pf.transform_content(source)
        expected = (
            "正文\n\n"
            "| A | B |\n"
            "|---|---|\n"
            "| 1 | 2 |\n"
            "> ordinary quote\n"
            "> continued\n\n"
            "结尾"
        )
        self.assertEqual(first.content, expected)
        second = pf.transform_content(first.content)
        self.assertEqual(second.content, first.content)
        self.assertEqual(second.summary.blank_lines_removed, 0)
        self.assertEqual(second.summary.callout_blank_lines_inserted, 0)
        self.assertEqual(second.summary.table_blank_lines_inserted, 0)

    def test_missing_table_and_quote_blanks_are_inserted(self) -> None:
        source = "正文\n| A | B |\n|---|---|\n> quote\n结尾"
        result = pf.transform_content(source)
        self.assertEqual(result.content, "正文\n\n| A | B |\n|---|---|\n> quote\n\n结尾")
        self.assertEqual(result.summary.table_blank_lines_inserted, 1)
        self.assertEqual(result.summary.callout_blank_lines_inserted, 1)

    def test_transform_is_idempotent_for_combined_sample(self) -> None:
        source = (
            "---\ntitle: sample\n---\n"
            "# 总标题\n\n## 第一节\n"
            "```mermaid\nA\\\\nB\n```\n"
            "---\n"
            "| A |\n|---|\n"
            "> note\n正文"
        )
        first = pf.transform_content(source)
        second = pf.transform_content(first.content)
        self.assertEqual(second.content, first.content)

    def test_core_change_counts_are_reported(self) -> None:
        source = (
            "正文\n\n\n"
            "---\n"
            "| A |\n"
            "|---|\n"
            "> quote\n"
            ">\n"
            "结尾\n"
            "```mermaid\n"
            "A\\nB\n"
            "```"
        )
        result = pf.transform_content(source)
        self.assertEqual(result.summary.dividers_replaced, 1)
        self.assertEqual(result.summary.blank_lines_removed, 2)
        self.assertEqual(result.summary.empty_quote_lines_removed, 1)
        self.assertEqual(result.summary.table_blank_lines_inserted, 1)
        self.assertEqual(result.summary.callout_blank_lines_inserted, 1)
        self.assertEqual(result.summary.mermaid_literal_newlines_expanded, 1)


class FileAndCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_bom_and_crlf_are_removed_on_write(self) -> None:
        path = self.root / "bom.md"
        path.write_bytes(codecs.BOM_UTF8 + b"# Title\r\n\r\nText\r\n---\r\n")
        result = pf.format_file(path)
        self.assertEqual(result.status, "modified")
        raw = path.read_bytes()
        self.assertFalse(raw.startswith(codecs.BOM_UTF8))
        self.assertNotIn(b"\r", raw)
        self.assertEqual(result.summary.bom_removed, 1)
        self.assertGreater(result.summary.line_endings_normalized, 0)

    def test_empty_file_is_skipped_without_write(self) -> None:
        path = self.root / "empty.md"
        path.write_bytes(b"")
        result = pf.format_file(path)
        self.assertEqual(result.status, "skipped")
        self.assertEqual(path.read_bytes(), b"")

    def test_invalid_utf8_is_a_failure(self) -> None:
        path = self.root / "bad.md"
        path.write_bytes(b"\xff\xfe")
        result = pf.format_file(path)
        self.assertEqual(result.status, "failed")
        self.assertIn("UTF-8", result.error)

    def test_unclosed_yaml_failure_preserves_original_bytes(self) -> None:
        path = self.root / "unclosed-yaml.md"
        original = ("---\n" + "\n".join(f"k{i}: v" for i in range(1, 15)) + "\n正文").encode("utf-8")
        path.write_bytes(original)
        result = pf.format_file(path)
        self.assertEqual(result.status, "failed")
        self.assertIn("前15个物理行", result.error)
        self.assertEqual(path.read_bytes(), original)

    def test_missing_file_is_a_failure(self) -> None:
        result = pf.format_file(self.root / "missing.md")
        self.assertEqual(result.status, "failed")

    def test_dry_run_outputs_full_diff_and_does_not_write(self) -> None:
        path = self.root / "many.md"
        original = "\n".join(f"section {i}\n---" for i in range(30))
        path.write_text(original, encoding="utf-8")
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            exit_code = pf.main([str(path), "--dry-run"])
        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertEqual(path.read_text(encoding="utf-8"), original)
        self.assertIn("section 29", output)
        self.assertEqual(output.count("+***"), 30)
        self.assertNotIn("还有", output)

    def test_normal_run_reports_candidate_after_formatting(self) -> None:
        path = self.root / "candidate.md"
        path.write_text("# 标题\n\n## 第一节\n正文\n---", encoding="utf-8")
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            exit_code = pf.main([str(path)])
        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("H1_CONFIRMATION_REQUIRED", output)
        self.assertTrue(path.read_text(encoding="utf-8").startswith("# 标题\n## 第一节"))
        self.assertTrue(path.read_text(encoding="utf-8").endswith("***"))

    def test_explicit_h1_removal_without_candidate_fails_without_write(self) -> None:
        path = self.root / "single.md"
        original = "# 唯一标题\n正文"
        path.write_text(original, encoding="utf-8")
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            exit_code = pf.main([str(path), "--remove-first-h1"])
        self.assertEqual(exit_code, 1)
        self.assertIn("候选 H1", stderr.getvalue())
        self.assertEqual(path.read_text(encoding="utf-8"), original)

    def test_atomic_validation_failure_preserves_original_bytes(self) -> None:
        path = self.root / "atomic.md"
        original = b"# Title\n\nText\n---"
        path.write_bytes(original)
        with mock.patch.object(
            pf,
            "_validate_temp_file",
            side_effect=pf.FormatError("simulated validation failure"),
        ):
            result = pf.format_file(path)
        self.assertEqual(result.status, "failed")
        self.assertEqual(path.read_bytes(), original)
        self.assertEqual(list(self.root.glob("*.tmp")), [])

    def test_backup_is_created_before_atomic_replace(self) -> None:
        path = self.root / "backup.md"
        original = b"# Title\n\nText\n---"
        path.write_bytes(original)
        result = pf.format_file(path, backup=True)
        self.assertEqual(result.status, "modified")
        self.assertEqual(Path(f"{path}.bak").read_bytes(), original)

    def test_directory_mixed_results_return_nonzero_and_complete_summary(self) -> None:
        good = self.root / "good.md"
        bad = self.root / "bad.md"
        empty = self.root / "empty.md"
        good.write_text("# Title\n\nText\n---", encoding="utf-8")
        bad.write_bytes(b"\xff")
        empty.write_bytes(b"")
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            exit_code = pf.main([str(self.root)])
        self.assertEqual(exit_code, 1)
        self.assertIn("total=3", stdout.getvalue())
        self.assertIn("modified=1", stdout.getvalue())
        self.assertIn("skipped=1", stdout.getvalue())
        self.assertIn("failed=1", stdout.getvalue())
        self.assertIn("[ERR]", stderr.getvalue())

    def test_second_file_run_is_unchanged(self) -> None:
        path = self.root / "twice.md"
        path.write_text("# 标题\n\n## 第一节\n正文\n---", encoding="utf-8")
        first = pf.format_file(path)
        second = pf.format_file(path)
        self.assertEqual(first.status, "modified")
        self.assertEqual(second.status, "unchanged")
        self.assertFalse(second.changed)


if __name__ == "__main__":
    unittest.main()
