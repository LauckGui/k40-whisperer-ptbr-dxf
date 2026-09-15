$ErrorActionPreference = "Stop"

$projectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvDir = Join-Path $projectDir (".venv-" + $env:COMPUTERNAME)
$pythonExe = Join-Path $venvDir "Scripts\python.exe"

if (-not (Test-Path -LiteralPath $pythonExe)) {
    & (Join-Path $projectDir "Preparar_Ambiente.bat")
    if ($LASTEXITCODE -ne 0) {
        throw "Não foi possível preparar o ambiente Python."
    }
}

Push-Location $projectDir
try {
    & $pythonExe -m pip install -r "requirements-build.txt"
    if ($LASTEXITCODE -ne 0) { throw "Falha ao instalar as dependências de build." }

    & $pythonExe -m unittest discover -s tests
    if ($LASTEXITCODE -ne 0) { throw "Os testes falharam; o instalador não foi gerado." }

    & $pythonExe -m PyInstaller --noconfirm --clean "K40Whisperer.spec"
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

    & $iscc (Join-Path $projectDir "installer\K40Whisperer.iss")
    if ($LASTEXITCODE -ne 0) { throw "Falha ao compilar o instalador Inno Setup." }

    Write-Host "Instalador criado em dist\installer." -ForegroundColor Green
}
finally {
    Pop-Location
}
