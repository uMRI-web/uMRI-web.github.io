$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$Root = 'D:\MRI-AI-study'
$Src  = Join-Path $Root '98_download'
$Docs = Join-Path $Root '00_PROJECT_DOCS'
$Exp  = Join-Path $Root '04_EXPERIMENTS\A2a_FA_atlas_deformation\20261009_poc'
$Pre  = Join-Path $Root '02_PREPROCESSING\SynthSeg\subject_final_20261009'
$Viewer = Join-Path $Root '05_VIEWER\A2a_subject_20261009'
$Tools = Join-Path $Root '09_TOOLS'
$Archive = Join-Path $Root '99_ARCHIVE\20261009_98_download_cleanup'
$Conflict = Join-Path $Archive 'CONFLICTS_NONIDENTICAL'
$Partial = Join-Path $Archive 'partial_runpod_archives'
$OldTools = Join-Path $Archive 'old_inventory_tools'
$Log = Join-Path $Docs '98_download_cleanup_log_20261009.txt'
$Summary = Join-Path $Docs '98_download_cleanup_summary_20261009.txt'

function Ensure-Dir([string]$p) {
    if (-not (Test-Path -LiteralPath $p)) { New-Item -ItemType Directory -Path $p -Force | Out-Null }
}

foreach ($d in @(
    $Docs,$Exp,$Pre,$Viewer,$Tools,$Archive,$Conflict,$Partial,$OldTools,
    (Join-Path $Exp 'final_outputs'),
    (Join-Path $Exp 'qc'),
    (Join-Path $Exp 'scripts'),
    (Join-Path $Exp 'failed_attempts\legacy_synthseg_registration'),
    (Join-Path $Viewer 'release'),
    (Join-Path $Tools 'rebuild'),
    (Join-Path $Tools 'inventory')
)) { Ensure-Dir $d }

"=== MRI-AI-study 98_download cleanup 2026-10-09 ===" | Set-Content -LiteralPath $Log -Encoding UTF8
"Start: $(Get-Date -Format o)" | Add-Content -LiteralPath $Log -Encoding UTF8

function Write-Log([string]$msg) {
    $line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')  $msg"
    $line | Tee-Object -FilePath $Log -Append
}

function Hash-File([string]$p) {
    return (Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash
}

function Unique-ConflictPath([string]$name) {
    $candidate = Join-Path $Conflict $name
    if (-not (Test-Path -LiteralPath $candidate)) { return $candidate }
    $base = [System.IO.Path]::GetFileNameWithoutExtension($name)
    $ext  = [System.IO.Path]::GetExtension($name)
    return Join-Path $Conflict ("{0}_{1}{2}" -f $base,(Get-Date -Format 'yyyyMMdd_HHmmssfff'),$ext)
}

function Move-Safe([string]$sourcePath, [string]$destPath) {
    if (-not (Test-Path -LiteralPath $sourcePath)) {
        Write-Log "SKIP_MISSING  $sourcePath"
        return
    }
    Ensure-Dir (Split-Path -Parent $destPath)
    if (Test-Path -LiteralPath $destPath) {
        $hs = Hash-File $sourcePath
        $hd = Hash-File $destPath
        if ($hs -eq $hd) {
            Remove-Item -LiteralPath $sourcePath -Force
            Write-Log "DUPLICATE_DELETE  $sourcePath  ==  $destPath  SHA256=$hs"
        } else {
            $c = Unique-ConflictPath ([System.IO.Path]::GetFileName($sourcePath))
            Move-Item -LiteralPath $sourcePath -Destination $c
            Write-Log "CONFLICT_ARCHIVE  $sourcePath  ->  $c  (destination differs: $destPath)"
        }
    } else {
        Move-Item -LiteralPath $sourcePath -Destination $destPath
        Write-Log "MOVE  $sourcePath  ->  $destPath"
    }
}

function Src([string]$name) { return (Join-Path $Src $name) }

if (-not (Test-Path -LiteralPath $Src)) { throw "Source folder not found: $Src" }

# Normalize any viewer ZIP manually saved earlier.
$viewerFinal = Join-Path $Viewer 'release\nougazounoatarashiibennkyoubonnver_READY_20261009.zip'
$oldViewerCandidates = @(
    (Join-Path $Exp 'viewer_release\nougazounoatarashiibennkyoubonnver (1).zip'),
    (Join-Path $Exp 'viewer_release\nougazounoatarashiibennkyoubonnver.zip')
)
foreach ($p in $oldViewerCandidates) {
    if (Test-Path -LiteralPath $p) { Move-Safe $p $viewerFinal }
}

# Canonical subject/source data.
Move-Safe (Src 'DTI261009.zip') (Join-Path $Root '01_SUBJECT_DATA\book_sample_001\diffusion\source_archive\DTI261009.zip')

# Final SynthSeg outputs from the final T1 geometry.
$preT1 = Join-Path $Pre 'subject_T1_synthseg_1mm.nii.gz'
Move-Safe (Src 'subject_T1_synthseg_1mm.nii.gz') $preT1
Move-Safe (Src 'subject_T1_synthseg_1mm (1).nii.gz') $preT1
Move-Safe (Src 'subject_seg_parc_1mm.nii.gz') (Join-Path $Pre 'subject_seg_parc_1mm.nii.gz')

# Final A2a outputs, QC, failed-attempt evidence, and scripts.
Move-Safe (Src 'results_T1_final.nii.gz') (Join-Path $Exp 'final_outputs\results_T1_final.nii.gz')
Move-Safe (Src 'CST_bilat_prob_T1_final.nii.gz') (Join-Path $Exp 'final_outputs\CST_bilat_prob_T1_final.nii.gz')
Move-Safe (Src 'CST_core_bilat.nii.gz') (Join-Path $Exp 'qc\CST_core_bilat.nii.gz')
Move-Safe (Src 'A2a_QC_representative_20261009.zip') (Join-Path $Exp 'qc\A2a_QC_representative_20261009.zip')
Move-Safe (Src 'legacySynthT1_in_finalT1.nii.gz') (Join-Path $Exp 'failed_attempts\legacy_synthseg_registration\legacySynthT1_in_finalT1.nii.gz')
Move-Safe (Src 'run_all_tracts_A2a.zip') (Join-Path $Exp 'scripts\run_all_tracts_A2a.zip')
Move-Safe (Src 'ARCHIVE_A2a_ALL.sh') (Join-Path $Exp 'scripts\ARCHIVE_A2a_ALL.sh')

# Final viewer release.
Move-Safe (Src 'nougazounoatarashiibennkyoubonnver.zip') $viewerFinal

# Project maintenance tools.
Move-Safe (Src 'MRI_AI_STUDY_REBUILD_20261009.zip') (Join-Path $Tools 'rebuild\MRI_AI_STUDY_REBUILD_20261009.zip')
Move-Safe (Src 'check_synthseg_inventory_v2.bat') (Join-Path $Tools 'inventory\check_synthseg_inventory_v2.bat')
Move-Safe (Src 'check_synthseg_inventory.zip') (Join-Path $OldTools 'check_synthseg_inventory.zip')

# Preserve intermediate RunPod snapshots instead of deleting them.
# They are redundant for normal use, but may contain historical/debug state or FSL reference trees.
foreach ($name in @(
    'out (2).zip','out (1).zip','work (1).zip','A2a.zip','workspace.zip','out.zip','work.zip','logs.zip'
)) {
    Move-Safe (Src $name) (Join-Path $Partial $name)
}

# Record the published state that may not be inside the pre-noindex viewer ZIP.
$published = @'
Published subject viewer (2026-10-09)
URL: https://umri-web.github.io/tract-viewer/nougazounoatarashiibennkyoubonnver/
Status: public GitHub Pages research demo; URL is not being distributed.
Search indexing: index.html on GitHub was updated with:
  <meta name="robots" content="noindex, nofollow, noarchive, nosnippet" />
Noindex commit: 69669a34352d374cbd7d0026dad3346fbc424dd7
Note: noindex is not access control. Anyone who knows/guesses the URL can access the page.
'@
$published | Set-Content -LiteralPath (Join-Path $Docs 'PUBLISHED_VIEWER_STATE_20261009.txt') -Encoding UTF8
Write-Log "WRITE  $(Join-Path $Docs 'PUBLISHED_VIEWER_STATE_20261009.txt')"

# Final summary and remaining-file check.
$remaining = @(Get-ChildItem -LiteralPath $Src -Force -File -ErrorAction SilentlyContinue)
$summaryLines = @(
    'MRI-AI-study cleanup completed: 2026-10-09',
    '',
    'Canonical destinations:',
    "  Subject/source DTI: $Root\01_SUBJECT_DATA\book_sample_001\diffusion\source_archive",
    "  Final SynthSeg:     $Pre",
    "  A2a experiment:     $Exp",
    "  Viewer release:     $Viewer\release",
    "  Tools:              $Tools",
    "  Historical zips:    $Archive",
    "  Log:                $Log",
    '',
    "Remaining files in 98_download: $($remaining.Count)"
)
if ($remaining.Count -gt 0) {
    $summaryLines += ($remaining | ForEach-Object { '  ' + $_.Name })
}
$summaryLines | Set-Content -LiteralPath $Summary -Encoding UTF8
Write-Log "WRITE  $Summary"
Write-Log "END remaining_files=$($remaining.Count)"

Write-Host ''
Write-Host '============================================================'
Write-Host 'CLEANUP COMPLETE'
Write-Host "Remaining files in 98_download: $($remaining.Count)"
Write-Host "Log:     $Log"
Write-Host "Summary: $Summary"
Write-Host '============================================================'
if ($remaining.Count -gt 0) {
    Write-Host 'Remaining files were NOT deleted automatically:'
    $remaining | ForEach-Object { Write-Host ('  ' + $_.Name) }
}
