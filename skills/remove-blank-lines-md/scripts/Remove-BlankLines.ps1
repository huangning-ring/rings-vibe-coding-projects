<#
.SYNOPSIS
    Remove all blank/whitespace-only lines from Markdown files.

.DESCRIPTION
    Removes empty or whitespace-only lines from .md files. Supports
    single-file, recursive-directory, backup (.bak), and dry-run modes.
    Preserves UTF-8 encoding and content structure.

.PARAMETER Path
    Path to a .md file or a directory containing .md files.

.PARAMETER Backup
    Create a .bak copy before modifying each file.

.PARAMETER Recurse
    Process .md files in subdirectories recursively (only when Path is a directory).

.PARAMETER Force
    Process non-.md files as well.

.PARAMETER WhatIf
    Show what would be removed without modifying files.

.EXAMPLE
    Remove-BlankLines.ps1 -Path "note.md"
    Remove-BlankLines.ps1 -Path "folder/" -Recurse -Backup
    Remove-BlankLines.ps1 -Path "note.md" -WhatIf
#>

[CmdletBinding(SupportsShouldProcess)]
param(
    [Parameter(Mandatory, Position = 0)]
    [string]$Path,

    [switch]$Backup,

    [switch]$Recurse,

    [switch]$Force
)

function Remove-BlankLinesFromFile {
    param(
        [string]$FilePath,
        [bool]$DoBackup,
        [switch]$WhatIf
    )

    if (-not (Test-Path $FilePath)) {
        Write-Warning "File not found: $FilePath"
        return
    }

    # Read original content
    try {
        $original = Get-Content -Path $FilePath -Raw -Encoding UTF8
    }
    catch {
        Write-Error "Failed to read $FilePath : $_"
        return
    }

    if ([string]::IsNullOrEmpty($original)) {
        Write-Host "[SKIP] $FilePath — empty file" -ForegroundColor Yellow
        return
    }

    # Count blank lines before removal
    $blankCount = [regex]::Matches($original, '(?m)^\s*$[\r\n]*').Count

    if ($blankCount -eq 0) {
        Write-Host "[OK] $FilePath — 0 blank lines (nothing to remove)" -ForegroundColor Green
        return
    }

    $newContent = $original -replace '(?m)^\s*$[\r\n]*', ''

    if ($WhatIf) {
        Write-Host "[WHATIF] $FilePath — would remove $blankCount blank line(s)" -ForegroundColor Cyan
        return
    }

    # Backup if requested
    if ($DoBackup) {
        $backupPath = $FilePath + '.bak'
        try {
            Copy-Item -Path $FilePath -Destination $backupPath -Force
        }
        catch {
            Write-Error "Failed to create backup for $FilePath : $_"
            return
        }
    }

    # Write cleaned content
    try {
        $newContent | Set-Content -Path $FilePath -NoNewline -Encoding UTF8
    }
    catch {
        Write-Error "Failed to write $FilePath : $_"
        return
    }

    $backupMsg = if ($DoBackup) { " (backup: $((Split-Path $backupPath -Leaf))" } else { "" }
    Write-Host "[OK] $FilePath — $blankCount blank line(s) removed$backupMsg" -ForegroundColor Green
}

# Resolve the path
$resolvedPath = Resolve-Path $Path -ErrorAction SilentlyContinue
if (-not $resolvedPath) {
    Write-Error "Path not found: $Path"
    exit 1
}

$item = Get-Item $resolvedPath

if ($item.PSIsContainer) {
    # Directory mode
    $searchOption = if ($Recurse) { [System.IO.SearchOption]::AllDirectories } else { [System.IO.SearchOption]::TopDirectoryOnly }
    $pattern = if ($Force) { '*.*' } else { '*.md' }

    $files = [System.IO.Directory]::EnumerateFiles($item.FullName, $pattern, $searchOption)

    $count = 0
    foreach ($file in $files) {
        if ($PSCmdlet.ShouldProcess($file, 'Remove blank lines')) {
            Remove-BlankLinesFromFile -FilePath $file -DoBackup:$Backup -WhatIf:$WhatIf
            $count++
        }
    }
    Write-Host "`nProcessed $count file(s) in $($item.FullName)" -ForegroundColor Gray
}
else {
    # Single file mode
    if ($Force -or $item.Extension -eq '.md') {
        if ($PSCmdlet.ShouldProcess($item.FullName, 'Remove blank lines')) {
            Remove-BlankLinesFromFile -FilePath $item.FullName -DoBackup:$Backup -WhatIf:$WhatIf
        }
    }
    else {
        Write-Warning "Skipping non-.md file: $($item.FullName). Use -Force to process."
    }
}
