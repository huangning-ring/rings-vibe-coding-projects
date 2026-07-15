---
name: remove-blank-lines-md
description: >
  Remove all empty lines from one or more Markdown (.md) files, cleaning up
  formatting noise introduced by paste-from-web, note sync tools like
  "笔记同步助手" (WeChat Official Account sync), or imported articles.
  Uses a PowerShell script that preserves content structure and UTF-8
  encoding while deleting blank/whitespace-only lines. Supports single-file,
  recursive-directory, backup (.bak), and dry-run modes. Triggers when the
  user mentions notes with "too many blank lines", "空行太多", "clean up
  whitespace", "remove empty lines", articles synced from "笔记同步助手",
  WeChat sync articles, messy imported content, or files that look "spaced out".
---

# Remove Blank Lines from Markdown

Removes all empty or whitespace-only lines from `.md` files. Useful for cleaning up articles synced from WeChat Official Accounts via "笔记同步助手" or other paste-from-web sources that introduce excessive blank lines.

## Usage

Trigger this skill by saying something like:

- "把这篇笔记的空行去掉"
- "remove blank lines from this file"
- "clean up whitespace in the synced articles"
- 笔记同步助手同步的文章空行太多

The skill will invoke the `Remove-BlankLines.ps1` script to process the files.

## Script Options

The PowerShell script `scripts/Remove-BlankLines.ps1` supports:

| Parameter | Description |
|-----------|-------------|
| `-Path` | File or directory to process (required) |
| `-Backup` | Create a `.bak` backup before modifying |
| `-Recurse` | Process all `.md` files in subdirectories |
| `-WhatIf` | Dry-run — show what would be removed without changing files |
| `-Force` | Process non-`.md` files as well |

## Examples

```powershell
# Single file
Remove-BlankLines.ps1 -Path "note.md"

# With backup
Remove-BlankLines.ps1 -Path "note.md" -Backup

# Preview changes
Remove-BlankLines.ps1 -Path "folder/" -Recurse -WhatIf

# Recursive directory
Remove-BlankLines.ps1 -Path "笔记同步助手/" -Recurse
```
