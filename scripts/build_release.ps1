param(
    [string]$Version = "",
    [switch]$SkipTests,
    [switch]$SkipSanityCheck,
    [switch]$Clean,
    [switch]$SmokeTest,
    [switch]$StopRunningApp,
    [int]$SmokeTestSeconds = 5,
    [string]$PythonExe = $env:PYTHON
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
$distOneFileExe = Join-Path $distRoot "$appName.exe"
$stageRoot = Join-Path $releaseRoot "$appName-stage"

function Assert-PathInsideProject {
    param([string]$PathToCheck)

    $separator = [System.IO.Path]::DirectorySeparatorChar
    $projectFull = [System.IO.Path]::GetFullPath($projectRoot)
    if (-not $projectFull.EndsWith([string]$separator)) {
        $projectFull += $separator
    }

    $targetFull = [System.IO.Path]::GetFullPath($PathToCheck)
    if (-not $targetFull.StartsWith($projectFull, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to modify path outside project root: $targetFull"
    }
}

function Get-BuildOutputProcesses {
    $distAppFull = [System.IO.Path]::GetFullPath($distAppRoot)
    $processes = @()
    foreach ($process in Get-Process -Name $appName -ErrorAction SilentlyContinue) {
        try {
            $processPath = $process.Path
            if (-not $processPath) {
                continue
            }
            $processFull = [System.IO.Path]::GetFullPath($processPath)
            if ($processFull.StartsWith($distAppFull, [System.StringComparison]::OrdinalIgnoreCase)) {
                $processes += $process
            }
        } catch {
            continue
        }
    }
    return $processes
}

function Assert-BuildOutputNotRunning {
    $processes = @(Get-BuildOutputProcesses)
    if ($processes.Count -eq 0) {
        return
    }

    if (-not $StopRunningApp) {
        $processList = ($processes | ForEach-Object { "$($_.ProcessName) pid=$($_.Id)" }) -join ", "
        throw "Packaged app is still running from dist and blocks rebuild: $processList. Close it first or rerun with -StopRunningApp."
    }

    Write-Host "Stopping running packaged app before build..."
    foreach ($process in $processes) {
        Stop-Process -Id $process.Id -Force
    }
    Start-Sleep -Milliseconds 500
}

function Remove-PathIfExistsInsideProject {
    param([string]$PathToRemove)

    if (-not (Test-Path -LiteralPath $PathToRemove)) {
        return
    }

    Assert-PathInsideProject $PathToRemove
    Remove-Item -LiteralPath $PathToRemove -Recurse -Force
}

function Format-PythonCandidate {
    param([object[]]$Candidate)

    $parts = @($Candidate)
    if ($parts.Count -le 1) {
        return [string]$parts[0]
    }

    return "$($parts[0]) $($parts[1..($parts.Count - 1)] -join ' ')"
}

function Test-PythonCandidate {
    param([object[]]$Candidate)

    $parts = @($Candidate)
    $exe = [string]$parts[0]
    $prefixArgs = @()
    if ($parts.Count -gt 1) {
        $prefixArgs = @($parts[1..($parts.Count - 1)])
    }

    try {
        & $exe @prefixArgs --version *> $null
        if ($LASTEXITCODE -ne 0) {
            return [pscustomobject]@{
                Usable = $false
                Exe    = $exe
                Args   = $prefixArgs
                Reason = "python --version failed"
            }
        }
    } catch {
        return [pscustomobject]@{
            Usable = $false
            Exe    = $exe
            Args   = $prefixArgs
            Reason = "cannot execute: $($_.Exception.Message)"
        }
    }

    try {
        & $exe @prefixArgs -c "import PyInstaller" *> $null
        if ($LASTEXITCODE -ne 0) {
            return [pscustomobject]@{
                Usable = $false
                Exe    = $exe
                Args   = $prefixArgs
                Reason = "PyInstaller is not installed"
            }
        }
    } catch {
        return [pscustomobject]@{
            Usable = $false
            Exe    = $exe
            Args   = $prefixArgs
            Reason = "PyInstaller check failed: $($_.Exception.Message)"
        }
    }

    $identity = & $exe @prefixArgs -c "import sys; print(sys.executable); print(sys.version.split()[0])"
    return [pscustomobject]@{
        Usable     = $true
        Exe        = $exe
        Args       = $prefixArgs
        PythonPath = [string]$identity[0]
        Version    = [string]$identity[1]
        Reason     = ""
    }
}

function Resolve-PythonRunner {
    param([string]$RequestedPython)

    $candidates = @()
    if ($RequestedPython) {
        $candidates += ,@($RequestedPython)
    }

    foreach ($relativePath in @(".venv\Scripts\python.exe", "venv\Scripts\python.exe")) {
        $candidatePath = Join-Path $projectRoot $relativePath
        if (Test-Path $candidatePath) {
            $candidates += ,@($candidatePath)
        }
    }

    $candidates += ,@("python")
    $candidates += ,@("python3")

    if (Get-Command py -ErrorAction SilentlyContinue) {
        $candidates += ,@("py", "-3.12")
        $candidates += ,@("py", "-3")
    }

    $seen = @{}
    $attempts = @()

    foreach ($candidate in $candidates) {
        $label = Format-PythonCandidate $candidate
        $key = $label.ToLowerInvariant()
        if ($seen.ContainsKey($key)) {
            continue
        }
        $seen[$key] = $true

        $result = Test-PythonCandidate $candidate
        if ($result.Usable) {
            return $result
        }

        $attempts += "$label -> $($result.Reason)"
    }

    throw "No usable Python interpreter with PyInstaller found. Pass -PythonExe <path-to-python.exe> or install PyInstaller in one of these candidates:`n- $($attempts -join "`n- ")"
}

$pythonRunner = Resolve-PythonRunner -RequestedPython $PythonExe
if ($pythonRunner.Args.Count -gt 0) {
    Write-Host "Using Python: $($pythonRunner.Exe) $($pythonRunner.Args -join ' ') ($($pythonRunner.Version), $($pythonRunner.PythonPath))"
} else {
    Write-Host "Using Python: $($pythonRunner.Exe) ($($pythonRunner.Version), $($pythonRunner.PythonPath))"
}

function Invoke-ProjectPython {
    param([string[]]$Arguments)

    $exe = $script:pythonRunner.Exe
    $prefixArgs = @($script:pythonRunner.Args)
    & $exe @prefixArgs @Arguments | Out-Host
    if ($null -eq $LASTEXITCODE) {
        if ($?) {
            return 0
        }
        return 1
    }
    return [int]$LASTEXITCODE
}

function Assert-RequiredPath {
    param(
        [string]$PathToCheck,
        [string]$Description
    )

    if (-not (Test-Path -LiteralPath $PathToCheck)) {
        throw "Missing $Description`: $PathToCheck"
    }
}

function Get-BundleContentRoot {
    param([string]$AppRoot)

    $internalRoot = Join-Path $AppRoot "_internal"
    if (Test-Path -LiteralPath $internalRoot) {
        return $internalRoot
    }

    return $AppRoot
}

function Assert-BuildOutput {
    Assert-RequiredPath $distAppRoot "PyInstaller output directory"

    $exePath = Join-Path $distAppRoot "$appName.exe"
    Assert-RequiredPath $exePath "application executable"

    $contentRoot = Get-BundleContentRoot $distAppRoot
    foreach ($relativePath in @("data", "docs", "images\background", "resources", "settings.example.ini", "image.ico", "favicon.ico")) {
        Assert-RequiredPath (Join-Path $contentRoot $relativePath) "bundled $relativePath"
    }

    foreach ($relativePath in @("resources\icons\tool_favorite.svg", "resources\icons\tool_notes.svg")) {
        Assert-RequiredPath (Join-Path $contentRoot $relativePath) "bundled action icon $relativePath"
    }

    $backgroundDir = Join-Path $contentRoot "images\background"
    $backgroundCount = @(Get-ChildItem -LiteralPath $backgroundDir -Filter "*.png" -File).Count
    if ($backgroundCount -lt 5) {
        throw "Expected bundled background PNG files, found only $backgroundCount in $backgroundDir"
    }

    return [pscustomobject]@{
        ExePath     = $exePath
        ContentRoot = $contentRoot
    }
}

function Invoke-BuildSmokeTest {
    param([string]$ExePath)

    Write-Host "Running packaged executable smoke test..."
    $process = Start-Process -FilePath $ExePath -WorkingDirectory (Split-Path -Parent $ExePath) -WindowStyle Hidden -PassThru
    Start-Sleep -Seconds ([Math]::Max(1, $SmokeTestSeconds))
    if ($process.HasExited) {
        throw "Packaged executable exited during smoke test with code $($process.ExitCode)."
    }

    Stop-Process -Id $process.Id -Force
}

function Remove-PackagedRuntimeState {
    $runtimePath = Join-Path $distAppRoot ".runtime"
    if (Test-Path -LiteralPath $runtimePath) {
        Remove-PathIfExistsInsideProject $runtimePath
    }
}

function Assert-ReleaseArchive {
    param(
        [string]$ZipPath,
        [string]$ContentRoot
    )

    Assert-RequiredPath $ZipPath "release archive"

    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $zip = [System.IO.Compression.ZipFile]::OpenRead($ZipPath)
    try {
        $entryNames = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
        foreach ($entry in $zip.Entries) {
            [void]$entryNames.Add($entry.FullName.Replace("\", "/"))
        }

        $contentPrefix = "$appName"
        if ((Split-Path -Leaf $ContentRoot) -eq "_internal") {
            $contentPrefix = "$appName/_internal"
        }

        foreach ($entryName in @(
            "$appName/$appName.exe",
            "$contentPrefix/settings.example.ini",
            "$contentPrefix/images/background/blue_white.png",
            "$contentPrefix/resources/icons/tool_favorite.svg",
            "$contentPrefix/resources/icons/tool_notes.svg"
        )) {
            if (-not $entryNames.Contains($entryName)) {
                throw "Release archive is missing: $entryName"
            }
        }
    } finally {
        $zip.Dispose()
    }
}

if (-not $Version) {
    $Version = Get-Date -Format "yyyy.MM.dd-HHmm"
}

$archiveName = "$appName-win64-v$Version.zip"
$archivePath = Join-Path $releaseRoot $archiveName

if ($Clean) {
    foreach ($path in @($distRoot, $buildRoot, $stageRoot)) {
        if (Test-Path $path) {
            Remove-PathIfExistsInsideProject $path
        }
    }
}

if (-not $SkipTests) {
    Write-Host "Running unit tests..."
    $exitCode = Invoke-ProjectPython @("-m", "unittest", "discover", "-s", "tests", "-v")
    if ($exitCode -ne 0) {
        throw "Unit tests failed."
    }
}

if (-not $SkipSanityCheck) {
    Write-Host "Running repository sanity check..."
    $exitCode = Invoke-ProjectPython @("scripts/repo_sanity_check.py")
    if ($exitCode -ne 0) {
        throw "Repository sanity check failed."
    }
}

Assert-BuildOutputNotRunning
Remove-PathIfExistsInsideProject $distAppRoot
Remove-PathIfExistsInsideProject $distOneFileExe

Write-Host "Building PyInstaller package..."
$exitCode = Invoke-ProjectPython @("-m", "PyInstaller", "--noconfirm", "ZifeiyuSec.spec")
if ($exitCode -ne 0) {
    throw "PyInstaller build failed."
}

$buildOutput = Assert-BuildOutput
if ($SmokeTest) {
    Invoke-BuildSmokeTest -ExePath $buildOutput.ExePath
    Remove-PackagedRuntimeState
}

New-Item -ItemType Directory -Force -Path $releaseRoot | Out-Null
if (Test-Path $archivePath) {
    Assert-PathInsideProject $archivePath
    Remove-Item -LiteralPath $archivePath -Force
}
if (Test-Path $stageRoot) {
    Assert-PathInsideProject $stageRoot
    Remove-Item -LiteralPath $stageRoot -Recurse -Force
}

Write-Host "Staging release files..."
New-Item -ItemType Directory -Force -Path $stageRoot | Out-Null
Copy-Item -LiteralPath $distAppRoot -Destination $stageRoot -Recurse -Force

Write-Host "Creating release archive..."
$zipCode = "import pathlib, zipfile; root=pathlib.Path(r'$stageRoot'); archive=pathlib.Path(r'$archivePath'); archive.parent.mkdir(parents=True, exist_ok=True); zf=zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9); [zf.write(path, path.relative_to(root)) for path in root.rglob('*') if path.is_file()]; zf.close()"
$exitCode = Invoke-ProjectPython @("-c", $zipCode)
if ($exitCode -ne 0) {
    throw "Release archive creation failed."
}

Assert-ReleaseArchive -ZipPath $archivePath -ContentRoot $buildOutput.ContentRoot

Write-Host "Cleaning release staging directory..."
Assert-PathInsideProject $stageRoot
Remove-Item -LiteralPath $stageRoot -Recurse -Force

Write-Host ""
Write-Host "Release archive created:"
Write-Host $archivePath
Write-Host "Archive size: $([Math]::Round((Get-Item -LiteralPath $archivePath).Length / 1MB, 2)) MB"
