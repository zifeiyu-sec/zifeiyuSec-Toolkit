param(
    [string]$Version = "",
    [switch]$SkipTests,
    [switch]$SkipSanityCheck,
    [switch]$Clean
)

$ErrorActionPreference = "Stop"

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptRoot
Set-Location $projectRoot

$distRoot = Join-Path $projectRoot "dist"
$buildRoot = Join-Path $projectRoot "build"
$releaseRoot = Join-Path $projectRoot "release"
$appName = "ZifeiyuSec"
$distAppRoot = Join-Path $distRoot $appName
$stageRoot = Join-Path $releaseRoot "$appName-stage"

if (-not $Version) {
    $Version = Get-Date -Format "yyyy.MM.dd-HHmm"
}

$archiveName = "$appName-win64-v$Version.zip"
$archivePath = Join-Path $releaseRoot $archiveName

if ($Clean) {
    foreach ($path in @($distRoot, $buildRoot, $stageRoot)) {
        if (Test-Path $path) {
            Remove-Item -LiteralPath $path -Recurse -Force
        }
    }
}

if (-not $SkipTests) {
    Write-Host "Running unit tests..."
    python -m unittest discover -s tests -v
    if ($LASTEXITCODE -ne 0) {
        throw "Unit tests failed."
    }
}

if (-not $SkipSanityCheck) {
    Write-Host "Running repository sanity check..."
    python scripts/repo_sanity_check.py
    if ($LASTEXITCODE -ne 0) {
        throw "Repository sanity check failed."
    }
}

Write-Host "Building PyInstaller package..."
python -m PyInstaller --noconfirm ZifeiyuSec.spec
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller build failed."
}

if (-not (Test-Path $distAppRoot)) {
    throw "Build output not found: $distAppRoot"
}

New-Item -ItemType Directory -Force -Path $releaseRoot | Out-Null
if (Test-Path $archivePath) {
    Remove-Item -LiteralPath $archivePath -Force
}
if (Test-Path $stageRoot) {
    Remove-Item -LiteralPath $stageRoot -Recurse -Force
}

Write-Host "Staging release files..."
New-Item -ItemType Directory -Force -Path $stageRoot | Out-Null
Copy-Item -LiteralPath $distAppRoot -Destination $stageRoot -Recurse -Force

Write-Host "Creating release archive..."
python -c "import pathlib, zipfile; root=pathlib.Path(r'$stageRoot'); archive=pathlib.Path(r'$archivePath'); archive.parent.mkdir(parents=True, exist_ok=True); zf=zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9); [zf.write(path, path.relative_to(root)) for path in root.rglob('*') if path.is_file()]; zf.close()"
if ($LASTEXITCODE -ne 0) {
    throw "Release archive creation failed."
}

Write-Host "Cleaning release staging directory..."
Remove-Item -LiteralPath $stageRoot -Recurse -Force

Write-Host ""
Write-Host "Release archive created:"
Write-Host $archivePath
