<#
.SYNOPSIS
    Baixa o .env do repositorio privado cafebugado/backendeventos-env e copia para a raiz do projeto.

.PARAMETER Environment
    Nome do ambiente (corresponde ao arquivo "<Environment>.env" no repo de env). Default: dev.

.PARAMETER Up
    Se informado, roda "docker compose up --build" apos configurar o .env.

.EXAMPLE
    ./scripts/fetch-env.ps1
    ./scripts/fetch-env.ps1 -Environment staging -Up
#>
param(
    [string]$Environment = "dev",
    [switch]$Up
)

$ErrorActionPreference = "Stop"

$EnvRepo = "cafebugado/backendeventos-env"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$TargetEnvFile = Join-Path $ProjectRoot ".env"
$CloneDir = Join-Path $env:TEMP "backendeventos-env"

function Assert-GhAuthenticated {
    try {
        gh auth status *> $null
    } catch {
        Write-Error "Voce nao esta autenticado no GitHub CLI. Rode 'gh auth login' e tente novamente."
        exit 1
    }
}

function Sync-EnvRepo {
    if (Test-Path $CloneDir) {
        Write-Host "Atualizando repositorio de env existente..."
        Push-Location $CloneDir
        try {
            git pull --quiet
        } catch {
            Write-Error "Falha ao atualizar '$EnvRepo'. Verifique se voce ainda tem acesso a ele."
            exit 1
        } finally {
            Pop-Location
        }
    } else {
        Write-Host "Clonando '$EnvRepo'..."
        try {
            gh repo clone $EnvRepo $CloneDir 2>&1 | Out-Null
        } catch {
            Write-Error "Nao foi possivel clonar '$EnvRepo'. Peca acesso a esse repositorio a quem administra o projeto."
            exit 1
        }
        if (-not (Test-Path $CloneDir)) {
            Write-Error "Nao foi possivel clonar '$EnvRepo'. Peca acesso a esse repositorio a quem administra o projeto."
            exit 1
        }
    }
}

Assert-GhAuthenticated
Sync-EnvRepo

$SourceEnvFile = Join-Path $CloneDir "$Environment.env"
if (-not (Test-Path $SourceEnvFile)) {
    Write-Error "Arquivo '$Environment.env' nao encontrado em '$EnvRepo'."
    exit 1
}

if (Test-Path $TargetEnvFile) {
    $existing = Get-Content $TargetEnvFile -Raw
    $incoming = Get-Content $SourceEnvFile -Raw
    if ($existing -ne $incoming) {
        $answer = Read-Host "Já existe um .env local diferente do remoto. Sobrescrever? (s/N)"
        if ($answer -notmatch '^[sS]$') {
            Write-Host "Operacao cancelada. .env local mantido."
            exit 0
        }
    }
}

Copy-Item $SourceEnvFile $TargetEnvFile -Force
Write-Host "'.env' atualizado a partir de '$Environment.env' ($EnvRepo)."

if ($Up) {
    docker compose up --build
}
