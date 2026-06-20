# ======================================================================
#  OptiBoard - Montee de version (SemVer)
#
#  Met a jour le numero de version dans TOUS les fichiers concernes :
#    - reporting-commercial/frontend/package.json   ("version": "x.y.z")
#    - reporting-commercial/backend/run.py          (FastAPI version="x.y.z")
#    - installer/OptiBoard.iss                      (#define AppVersion + OutputBaseFilename)
#    - CHANGELOG.md                                 ([Non publié] -> [x.y.z] — date)
#
#  Usage (depuis la racine du repo) :
#    .\scripts\release\bump_version.ps1 -Version 1.1.0
#
#  Puis :
#    git add -A ; git commit -m "release: v1.1.0" ; git tag v1.1.0
# ======================================================================
param(
    [Parameter(Mandatory = $true)][string]$Version
)

$ErrorActionPreference = "Stop"

if ($Version -notmatch '^\d+\.\d+\.\d+$') {
    Write-Host "[ERREUR] Version invalide '$Version' (attendu : MAJEUR.MINEUR.CORRECTIF, ex: 1.1.0)" -ForegroundColor Red
    exit 1
}

$root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$files = @{
    PackageJson = Join-Path $root "reporting-commercial\frontend\package.json"
    RunPy       = Join-Path $root "reporting-commercial\backend\run.py"
    Iss         = Join-Path $root "installer\OptiBoard.iss"
    Changelog   = Join-Path $root "CHANGELOG.md"
}

foreach ($f in $files.Values) {
    if (-not (Test-Path $f)) {
        Write-Host "[ERREUR] Fichier introuvable : $f (lancer depuis la racine du repo)" -ForegroundColor Red
        exit 1
    }
}

function Update-File([string]$path, [string]$pattern, [string]$replacement, [string]$label) {
    $content = [System.IO.File]::ReadAllText($path)
    $new = [regex]::Replace($content, $pattern, $replacement)
    if ($new -eq $content) {
        Write-Host "[ATTENTION] Aucun changement dans $label (motif non trouve ou version identique)" -ForegroundColor Yellow
    } else {
        [System.IO.File]::WriteAllText($path, $new)
        Write-Host "[OK] $label -> $Version" -ForegroundColor Green
    }
}

# 1. package.json
Update-File $files.PackageJson '("version"\s*:\s*")\d+\.\d+\.\d+(")' "`${1}$Version`${2}" "package.json"

# 2. run.py (FastAPI version=)
Update-File $files.RunPy '(version\s*=\s*")\d+\.\d+\.\d+(")' "`${1}$Version`${2}" "run.py"

# 3. OptiBoard.iss (AppVersion + nom du setup genere)
Update-File $files.Iss '(#define\s+AppVersion\s+")\d+\.\d+\.\d+(")' "`${1}$Version`${2}" "OptiBoard.iss (AppVersion)"
Update-File $files.Iss '(OutputBaseFilename=OptiBoard-Setup-)\d+\.\d+\.\d+' "`${1}$Version" "OptiBoard.iss (OutputBaseFilename)"

# 4. CHANGELOG.md : [Non publié] -> [x.y.z] — date, et nouvelle section vide au-dessus
$today = Get-Date -Format "yyyy-MM-dd"
$chg = [System.IO.File]::ReadAllText($files.Changelog)
if ($chg -match '## \[Non publié\]') {
    $chg = $chg -replace '## \[Non publié\]', "## [Non publié]`r`n`r`n## [$Version] — $today"
    [System.IO.File]::WriteAllText($files.Changelog, $chg)
    Write-Host "[OK] CHANGELOG.md : section [$Version] — $today creee" -ForegroundColor Green
} else {
    Write-Host "[ATTENTION] Section [Non publié] introuvable dans CHANGELOG.md" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Version $Version appliquee. Etapes suivantes :" -ForegroundColor Cyan
Write-Host "  1. Verifier :   git diff"
Write-Host "  2. Committer :  git add -A ; git commit -m `"release: v$Version`""
Write-Host "  3. Tagger :     git tag v$Version"
Write-Host "  4. Rebuilder :  REBUILD_ALL.bat (Cython + Vite + installeur)"
exit 0
