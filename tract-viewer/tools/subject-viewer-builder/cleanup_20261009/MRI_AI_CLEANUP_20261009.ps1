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
$Partial = Join-Path $Archive 'partial_runpod_archives'
$Conflict = Join-Path $Archive 'conflicts_nonidentical'
$OldTools = Join-Path $Archive 'old_inventory_tools'
$Log = Join-Path $Docs '98_download_cleanup_log_20261009.txt'
$Summary = Join-Path $Docs '98_download_cleanup_summary_20261009.txt'

function Ensure-Dir([string]$p) {
  if (-not (Test-Path -LiteralPath $p)) { New-Item -ItemType Directory -Path $p -Force | Out-Null }
}
function Log([string]$s) {
  $line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')  $s"
  $line | Tee-Object -FilePath $Log -Append
}
function SHA([string]$p) {
  (Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash
}
function Conflict-Path([string]$name) {
  $p = Join-Path $Conflict $name
  if (-not (Test-Path -LiteralPath $p)) { return $p }
  $stem=[IO.Path]::GetFileNameWithoutExtension($name)
  $ext=[IO.Path]::GetExtension($name)
  Join-Path $Conflict ("{0}_{1}{2}" -f $stem,(Get-Date -Format 'yyyyMMdd_HHmmssfff'),$ext)
}
function Move-Safe([string]$src,[string]$dst) {
  if (-not (Test-Path -LiteralPath $src)) { Log "SKIP_MISSING $src"; return }
  Ensure-Dir (Split-Path -Parent $dst)
  if (Test-Path -LiteralPath $dst) {
    $a=SHA $src; $b=SHA $dst
    if ($a -eq $b) {
      Remove-Item -LiteralPath $src -Force
      Log "DELETE_EXACT_DUPLICATE $src == $dst SHA256=$a"
    } else {
      $c=Conflict-Path ([IO.Path]::GetFileName($src))
      Move-Item -LiteralPath $src -Destination $c
      Log "MOVE_CONFLICT_PRESERVED $src -> $c"
    }
  } else {
    Move-Item -LiteralPath $src -Destination $dst
    Log "MOVE $src -> $dst"
  }
}

foreach($d in @(
  $Docs,$Exp,$Pre,$Viewer,$Tools,$Archive,$Partial,$Conflict,$OldTools,
  (Join-Path $Exp 'final_outputs'),
  (Join-Path $Exp 'qc'),
  (Join-Path $Exp 'scripts'),
  (Join-Path $Exp 'failed_attempts\legacy_synthseg_registration'),
  (Join-Path $Viewer 'release'),
  (Join-Path $Tools 'rebuild'),
  (Join-Path $Tools 'inventory')
)){ Ensure-Dir $d }

if (-not (Test-Path -LiteralPath $Src)) { throw "Not found: $Src" }

"=== MRI-AI-study 98_download cleanup 2026-10-09 ===" | Set-Content -LiteralPath $Log -Encoding UTF8
Log "START"

# Subject/source archive
Move-Safe (Join-Path $Src 'DTI261009.zip') (Join-Path $Root '01_SUBJECT_DATA\book_sample_001\diffusion\source_archive\DTI261009.zip')

# Final SynthSeg assets
$canonT1 = Join-Path $Pre 'subject_T1_synthseg_1mm.nii.gz'
Move-Safe (Join-Path $Src 'subject_T1_synthseg_1mm.nii.gz') $canonT1
Move-Safe (Join-Path $Src 'subject_T1_synthseg_1mm (1).nii.gz') $canonT1
Move-Safe (Join-Path $Src 'subject_seg_parc_1mm.nii.gz') (Join-Path $Pre 'subject_seg_parc_1mm.nii.gz')

# A2a final/QC/scripts
Move-Safe (Join-Path $Src 'results_T1_final.nii.gz') (Join-Path $Exp 'final_outputs\results_T1_final.nii.gz')
Move-Safe (Join-Path $Src 'CST_bilat_prob_T1_final.nii.gz') (Join-Path $Exp 'final_outputs\CST_bilat_prob_T1_final.nii.gz')
Move-Safe (Join-Path $Src 'CST_core_bilat.nii.gz') (Join-Path $Exp 'qc\CST_core_bilat.nii.gz')
Move-Safe (Join-Path $Src 'A2a_QC_representative_20261009.zip') (Join-Path $Exp 'qc\A2a_QC_representative_20261009.zip')
Move-Safe (Join-Path $Src 'legacySynthT1_in_finalT1.nii.gz') (Join-Path $Exp 'failed_attempts\legacy_synthseg_registration\legacySynthT1_in_finalT1.nii.gz')
Move-Safe (Join-Path $Src 'run_all_tracts_A2a.zip') (Join-Path $Exp 'scripts\run_all_tracts_A2a.zip')
Move-Safe (Join-Path $Src 'ARCHIVE_A2a_ALL.sh') (Join-Path $Exp 'scripts\ARCHIVE_A2a_ALL.sh')

# Viewer release
Move-Safe (Join-Path $Src 'nougazounoatarashiibennkyoubonnver.zip') (Join-Path $Viewer 'release\nougazounoatarashiibennkyoubonnver_READY_20261009.zip')

# Maintenance tools
Move-Safe (Join-Path $Src 'MRI_AI_STUDY_REBUILD_20261009.zip') (Join-Path $Tools 'rebuild\MRI_AI_STUDY_REBUILD_20261009.zip')
Move-Safe (Join-Path $Src 'check_synthseg_inventory_v2.bat') (Join-Path $Tools 'inventory\check_synthseg_inventory_v2.bat')
Move-Safe (Join-Path $Src 'check_synthseg_inventory.zip') (Join-Path $OldTools 'check_synthseg_inventory.zip')

# Intermediate RunPod snapshots: preserve, but remove from download staging.
foreach($name in @('out (2).zip','out (1).zip','work (1).zip','A2a.zip','workspace.zip','out.zip','work.zip','logs.zip')){
  Move-Safe (Join-Path $Src $name) (Join-Path $Partial $name)
}

# Record current published state (local viewer ZIP may predate the noindex commit).
@'
Published subject viewer, 2026-10-09
URL:
https://umri-web.github.io/tract-viewer/nougazounoatarashiibennkyoubonnver/

GitHub Pages status:
- Research demo is publicly reachable by URL.
- URL is not intended to be distributed.
- noindex/nofollow/noarchive/nosnippet was added to the published index.html.
- noindex commit: 69669a34352d374cbd7d0026dad3346fbc424dd7

Important:
noindex is not authentication/access control.
'@ | Set-Content -LiteralPath (Join-Path $Docs 'PUBLISHED_VIEWER_STATE_20261009.txt') -Encoding UTF8
Log "WRITE PUBLISHED_VIEWER_STATE_20261009.txt"

$remain=@(Get-ChildItem -LiteralPath $Src -Force -File -ErrorAction SilentlyContinue)
$lines=@(
  'MRI-AI-study 98_download cleanup summary - 2026-10-09',
  '',
  "Final SynthSeg: $Pre",
  "A2a experiment: $Exp",
  "Viewer release: $Viewer\release",
  "Tools: $Tools",
  "Historical/intermediate archives: $Archive",
  '',
  "Remaining files in 98_download: $($remain.Count)"
)
if($remain.Count -gt 0){ $lines += ($remain | ForEach-Object { '  '+$_.Name }) }
$lines | Set-Content -LiteralPath $Summary -Encoding UTF8
Log "END remaining=$($remain.Count)"

Write-Host ''
Write-Host '============================================================'
Write-Host 'CLEANUP COMPLETE'
Write-Host "Remaining files in 98_download: $($remain.Count)"
Write-Host "Log: $Log"
Write-Host "Summary: $Summary"
Write-Host '============================================================'
if($remain.Count -gt 0){
  Write-Host 'These remaining files were NOT deleted automatically:'
  $remain | ForEach-Object { Write-Host ('  '+$_.Name) }
}