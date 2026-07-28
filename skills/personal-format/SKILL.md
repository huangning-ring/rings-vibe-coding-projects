---
name: personal-format
description: >
  Standardize Markdown and Obsidian notes by removing excess blank lines,
  normalizing dividers, table and quote spacing, preserving protected Markdown
  structures, and handling heading hierarchy safely. Use when the user asks for
  “改个性格式”, “标准格式”, “个人格式”, “格式标准化”, “clean up this note”,
  “空行太多”, or wants to tidy Markdown from web pastes, WeChat sync tools,
  lecture notes, scripts, or imported articles.
---

# Personal Format

Use `scripts/personal_format.py` for deterministic Markdown formatting.

## Required workflow

1. Inspect the target scope and run `--dry-run`.
2. Review the complete unified diff and reported counts.
3. Run without `--remove-first-h1`. The script must preserve every H1 while applying the other formatting rules.
4. If the completed run reports `H1_CONFIRMATION_REQUIRED`, tell the user that the other formatting is complete and ask whether to delete the reported first H1.
5. Use `--remove-first-h1` only after explicit user confirmation.
6. Rerun `--dry-run`; require `无需更改` for each successfully formatted file.

Do not replace the bundled script with an improvised formatter. Do not infer consent to delete an H1 from its wording or length.

## Formatting contract

- Normalize CRLF and CR line endings to LF.
- Read UTF-8 with or without BOM; always write UTF-8 without BOM.
- Recognize YAML only when its opening delimiter is the first non-empty line and both delimiters occur within the first 15 physical lines. Stop without writing when such YAML is not closed within that window.
- Protect YAML, fenced code blocks, and inline code from body transformations.
- Replace body divider lines `---` with `***`.
- Remove ordinary blank lines and empty `>` rows while preserving code-block content.
- Keep exactly one blank line before table blocks and after consecutive `>` blocks when required.
- Replace exact literal `\n` sequences only inside Mermaid fenced-block content. Leave every `\n` outside Mermaid unchanged.
- Never delete an H1 automatically.
- Report `H1_CONFIRMATION_REQUIRED` when the first H1 has a later H1, or when it is the only H1 but later H2–H6 headings carry the sections.
- With confirmed `--remove-first-h1`, delete only the candidate H1 line. If another H1 remains, preserve all other heading levels. If no H1 remains, promote all remaining body headings by exactly one level.

## Commands

```bash
# Preview one file with a complete diff
python scripts/personal_format.py "note.md" --dry-run

# Format while preserving all H1 headings
python scripts/personal_format.py "note.md"

# Format and create note.md.bak
python scripts/personal_format.py "note.md" --backup

# Delete the reported candidate H1 only after user confirmation
python scripts/personal_format.py "note.md" --remove-first-h1

# Process a directory recursively
python scripts/personal_format.py "notes/"
```

Treat any `[ERR]` or nonzero exit status as a failure, not as an empty or unchanged result. For directories, verify `failed=0` in the final summary.
