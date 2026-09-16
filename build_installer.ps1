$ErrorActionPreference = "Stop"

$projectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvDir = Join-Path $projectDir (".venv-" + $env:COMPUTERNAME)
$pythonExe = Join-Path $venvDir "Scripts\python.exe"
$temporaryRoot = Join-Path ([IO.Path]::GetTempPath()) ("K40Whisperer-build-" + [guid]::NewGuid().ToString("N"))
$workDir = Join-Path $temporaryRoot "work"
$releaseDir = Join-Path $temporaryRoot "release"
$installerDir = Join-Path $temporaryRoot "installer"
$finalOutputDir = Join-Path (Split-Path -Parent $projectDir) "Output"

if (-not (Test-Path -LiteralPath $pythonExe)) {
    & (Join-Path $projectDir "Preparar_Ambiente.bat")
    if ($LASTEXITCODE -ne 0) {
        throw "Não foi possível preparar o ambiente Python."
    }
}

Push-Location $projectDir
try {
    New-Item -ItemType Directory -Path $workDir, $releaseDir, $installerDir -Force | Out-Null

    & $pythonExe -m pip install -r "requirements-build.txt"
    if ($LASTEXITCODE -ne 0) { throw "Falha ao instalar as dependências de build." }

    & $pythonExe -m unittest discover -s tests
    if ($LASTEXITCODE -ne 0) { throw "Os testes falharam; o instalador não foi gerado." }

    & $pythonExe -m PyInstaller --noconfirm --clean `
        --workpath $workDir --distpath $releaseDir "K40Whisperer.spec"
    if ($LASTEXITCODE -ne 0) { throw "Falha ao gerar o aplicativo com PyInstaller." }

    $isccCandidates = @(
        (Join-Path ${env:ProgramFiles(x86)} "Inno Setup 6\ISCC.exe"),
        (Join-Path $env:ProgramFiles "Inno Setup 6\ISCC.exe"),
        (Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe")
    )
    $iscc = $isccCandidates | Where-Object { $_ -and (Test-Path -LiteralPath $_) } | Select-Object -First 1
    if (-not $iscc) {
        throw "Inno Setup 6 não encontrado. Instale com: winget install --id JRSoftware.InnoSetup -e"
    }

    $appSource = Join-Path $releaseDir "K40 Whisperer"
    & $iscc "/DAppSource=$appSource" "/DInstallerOutputDir=$installerDir" `
        (Join-Path $projectDir "installer\K40Whisperer.iss")
    if ($LASTEXITCODE -ne 0) { throw "Falha ao compilar o instalador Inno Setup." }

    New-Item -ItemType Directory -Path $finalOutputDir -Force | Out-Null
    Get-ChildItem -LiteralPath $installerDir -Filter "*.exe" | ForEach-Object {
        Copy-Item -LiteralPath $_.FullName -Destination (Join-Path $finalOutputDir $_.Name) -Force
    }
    Write-Host "Instalador criado em $finalOutputDir." -ForegroundColor Green
}
finally {
    Pop-Location
    $resolvedTemp = [IO.Path]::GetFullPath($temporaryRoot)
    $systemTemp = [IO.Path]::GetFullPath([IO.Path]::GetTempPath())
    if ($resolvedTemp.StartsWith($systemTemp, [StringComparison]::OrdinalIgnoreCase) -and
        (Split-Path -Leaf $resolvedTemp).StartsWith("K40Whisperer-build-")) {
        Remove-Item -LiteralPath $resolvedTemp -Recurse -Force -ErrorAction SilentlyContinue
    }
}
