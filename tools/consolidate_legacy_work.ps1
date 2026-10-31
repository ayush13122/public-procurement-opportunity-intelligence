param(
    [string]$OldRoot = "D:\b2b_opportunity_intelligence\b2b_opportunity_intelligence",
    [switch]$RemoveTemporaryPatchArtifacts
)
$ErrorActionPreference = 'Stop'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$OldRoot = [System.IO.Path]::GetFullPath($OldRoot)

if (-not (Test-Path (Join-Path $RepoRoot '.git'))) {
    throw "Target is not a Git repository root: $RepoRoot. Run this helper from the tools folder inside your existing GitHub project."
}
if (-not (Test-Path $OldRoot)) {
    Write-Warning "Old folder not found: $OldRoot. Known documentation/tests are already included in this consolidation package; local-only files were not copied."
}

function Get-Hash([string]$Path) {
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash
}
function Get-ExistingHashes {
    $ignored = '\\(\.git|\.venv|venv|\.idea|__pycache__|\.pytest_cache)(\\|$)'
    $set = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
    Get-ChildItem -LiteralPath $RepoRoot -Recurse -File -ErrorAction SilentlyContinue |
        Where-Object { $_.FullName -notmatch $ignored } |
        ForEach-Object { [void]$set.Add((Get-Hash $_.FullName)) }
    return ,$set
}
$existingHashes = Get-ExistingHashes
$log = [System.Collections.Generic.List[object]]::new()
function Copy-IfUnique([string]$Source, [string]$Destination) {
    if (-not (Test-Path -LiteralPath $Source -PathType Leaf)) { return }
    $src = (Resolve-Path -LiteralPath $Source).Path
    $dest = [System.IO.Path]::GetFullPath($Destination)
    $hash = Get-Hash $src
    if (Test-Path -LiteralPath $dest -PathType Leaf) {
        if ((Get-Hash $dest) -eq $hash) {
            $script:log.Add([pscustomobject]@{Status='SKIP_IDENTICAL';Source=$src;Destination=$dest})
            return
        }
        if ($script:existingHashes.Contains($hash)) {
            $script:log.Add([pscustomobject]@{Status='SKIP_DUPLICATE_CONTENT';Source=$src;Destination=$dest})
            return
        }
        # Preserve genuinely different legacy content as a clearly labelled archive version; never overwrite current code/docs.
        if ($dest.StartsWith((Join-Path $RepoRoot 'reports'), [System.StringComparison]::OrdinalIgnoreCase)) {
            $variantRoot = Join-Path $RepoRoot 'reports\archive\legacy_variants'
        } else {
            $variantRoot = Join-Path $RepoRoot 'docs\project_history\local_variants'
        }
        $ext = [System.IO.Path]::GetExtension($dest)
        $base = [System.IO.Path]::GetFileNameWithoutExtension($dest)
        $variantName = ($base + '_legacy_' + $hash.Substring(0,8) + $ext)
        $variantDest = Join-Path $variantRoot $variantName
        New-Item -ItemType Directory -Force -Path $variantRoot | Out-Null
        if (-not (Test-Path -LiteralPath $variantDest)) { Copy-Item -LiteralPath $src -Destination $variantDest }
        [void]$script:existingHashes.Add($hash)
        $script:log.Add([pscustomobject]@{Status='ARCHIVED_DIFFERENT_VERSION';Source=$src;Destination=$variantDest})
        Write-Warning "A different legacy version was preserved at $variantDest; the current canonical file was not overwritten."
        return
    }
    if ($script:existingHashes.Contains($hash)) {
        $script:log.Add([pscustomobject]@{Status='SKIP_DUPLICATE_CONTENT';Source=$src;Destination=$dest})
        return
    }
    $parent = Split-Path -Parent $dest
    New-Item -ItemType Directory -Force -Path $parent | Out-Null
    Copy-Item -LiteralPath $src -Destination $dest
    [void]$script:existingHashes.Add($hash)
    $script:log.Add([pscustomobject]@{Status='COPIED';Source=$src;Destination=$dest})
    Write-Host "Copied: $src -> $dest" -ForegroundColor Green
}

if (Test-Path $OldRoot) {
    # Important local-only files identified during the folder comparison.
    Copy-IfUnique (Join-Path $OldRoot 'src\config.py') (Join-Path $RepoRoot 'src\config.py')
    Copy-IfUnique (Join-Path $OldRoot 'src\__init__.py') (Join-Path $RepoRoot 'src\__init__.py')
    Copy-IfUnique (Join-Path $OldRoot 'app\README.md') (Join-Path $RepoRoot 'docs\app\APP_MODULE_NOTES.md')
    Copy-IfUnique (Join-Path $OldRoot 'data\README.md') (Join-Path $RepoRoot 'data\README.md')
    Copy-IfUnique (Join-Path $OldRoot 'notebooks\README.md') (Join-Path $RepoRoot 'notebooks\README.md')
    Copy-IfUnique (Join-Path $OldRoot 'tests\README.md') (Join-Path $RepoRoot 'tests\README.md')
    Copy-IfUnique (Join-Path $OldRoot 'reports\eda\14_missing_or_zero_tender_values_for_review.pdf') (Join-Path $RepoRoot 'reports\eda\14_missing_or_zero_tender_values_for_review.pdf')

    # Preserve the real local historical planning/docs if they are not already present in the curated locations.
    $docMap = @(
        @{From='docs\PROJECT_CHARTER.md'; To='docs\project_history\INITIAL_PROJECT_CHARTER.md'},
        @{From='docs\EXECUTION_PLAN.md'; To='docs\project_history\INITIAL_EXECUTION_PLAN.md'},
        @{From='docs\EDA_ANALYSIS_PLAN.md'; To='docs\analysis\EDA_ANALYSIS_PLAN.md'},
        @{From='docs\CATEGORY_TAXONOMY_NOTES.md'; To='docs\taxonomy\CATEGORY_TAXONOMY_NOTES.md'},
        @{From='cleaning_step_pack\docs\CLEANING_DECISIONS.md'; To='docs\data_cleaning\CLEANING_DECISIONS.md'},
        @{From='niche_taxonomy_review_pack\docs\TAXONOMY_REVIEW_GUIDE.md'; To='docs\taxonomy\TAXONOMY_REVIEW_GUIDE.md'},
        @{From='taxonomy_rule_refinement_pack\docs\TAXONOMY_RULE_DECISIONS.md'; To='docs\taxonomy\decisions\TAXONOMY_RULE_DECISIONS.md'},
        @{From='source_title_conflict_refinement_pack\docs\SOURCE_TITLE_CONFLICT_DECISIONS.md'; To='docs\taxonomy\decisions\SOURCE_TITLE_CONFLICT_DECISIONS.md'}
    )
    foreach ($m in $docMap) { Copy-IfUnique (Join-Path $OldRoot $m.From) (Join-Path $RepoRoot $m.To) }

    # Keep unique earlier terminal checks as clearly marked archive snapshots; deduplicate by SHA-256.
    $oldChecks = Join-Path $OldRoot 'reports\terminal_checks'
    if (Test-Path $oldChecks) {
        Get-ChildItem -LiteralPath $oldChecks -Recurse -File |
            Where-Object { $_.FullName -notmatch '\\(\.pytest_cache|__pycache__)(\\|$)' -and $_.Extension -in '.csv','.md','.txt','.json' } |
            ForEach-Object {
                $relative = $_.FullName.Substring($oldChecks.Length).TrimStart('\\')
                $dest = Join-Path (Join-Path $RepoRoot 'reports\archive\terminal_checks') $relative
                Copy-IfUnique $_.FullName $dest
            }
    }
}

# Temporary patch artifacts were copies of canonical files, not source-of-truth modules.
if ($RemoveTemporaryPatchArtifacts) {
    $required = @('src\train_procurement_category_model.py','tests\test_procurement_category_model.py','docs\ML_BROAD_CATEGORY_CLASSIFIER.md','app\tender_copilot.py','app\bid_fit_engine.py')
    $missing = @($required | Where-Object { -not (Test-Path (Join-Path $RepoRoot $_)) })
    if ($missing.Count -gt 0) {
        Write-Warning "Not removing patch artifacts because canonical files are missing: $($missing -join ', ')"
    } else {
        $patchDir = Join-Path $RepoRoot 'milestone1_missing_files_patch'
        if (Test-Path $patchDir) {
            Remove-Item -LiteralPath $patchDir -Recurse -Force
            Write-Host "Removed duplicate temporary folder: milestone1_missing_files_patch" -ForegroundColor Yellow
        }
        foreach ($name in @('PATCH_README.md','PATCH_README_MILESTONE2.txt','PATCH_README_MILESTONE3.txt','README_PATCH_INSTRUCTIONS.md')) {
            $p = Join-Path $RepoRoot $name
            if (Test-Path $p -PathType Leaf) {
                Remove-Item -LiteralPath $p -Force
                Write-Host "Removed temporary patch note: $name" -ForegroundColor Yellow
            }
        }
    }
}

$logPath = Join-Path $env:TEMP 'procurement_project_consolidation_log.csv'
$log | Export-Csv -LiteralPath $logPath -NoTypeInformation -Encoding UTF8
Write-Host "`nRepository root: $RepoRoot" -ForegroundColor Cyan
Write-Host "Old folder was not deleted or modified: $OldRoot" -ForegroundColor Cyan
Write-Host "Migration log: $logPath" -ForegroundColor Cyan
Write-Host "Run tests next: python -m pytest tests -q" -ForegroundColor Cyan
if (-not $RemoveTemporaryPatchArtifacts) {
    Write-Host "When ready to remove duplicate patch artifacts, rerun with -RemoveTemporaryPatchArtifacts." -ForegroundColor Yellow
}
