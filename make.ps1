param(
    [Parameter(Position=0)]
    [string]$Command = "help"
)

$envFile = Join-Path $PSScriptRoot ".env"
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^\s*([^#][^=]+)=(.*)$') {
            $key = $matches[1].Trim()
            $val = $matches[2].Trim()
            [Environment]::SetEnvironmentVariable($key, $val, "Process")
        }
    }
}

$DEV = "docker compose --env-file .env"
$PROD = "docker compose --env-file .env.prod"

function Invoke-Dev { param([string]$cmd) Invoke-Expression "$DEV $cmd" }
function Invoke-Prod { param([string]$cmd) Invoke-Expression "$PROD $cmd" }

switch ($Command) {
    "help" {
        $fe = $env:FRONTEND_EXTERNAL_PORT; if (!$fe) { $fe = "3071" }
        $be = $env:BACKEND_EXTERNAL_PORT;  if (!$be) { $be = "8037" }
        $db = $env:POSTGRES_EXTERNAL_PORT; if (!$db) { $db = "5491" }
        Write-Host @"
WPP
===

Dev:
  .\make.ps1 dev-up        Start all services
  .\make.ps1 dev-down      Stop all services
  .\make.ps1 dev-restart   Restart all services

Prod:
  .\make.ps1 prod-up       Start all services
  .\make.ps1 prod-down     Stop all services
  .\make.ps1 prod-restart  Restart all services

Other:
  .\make.ps1 clean         Nuke containers, volumes, caches

Ports:
  Frontend:  http://localhost:$fe
  Backend:   http://localhost:${be}/docs
  Database:  localhost:$db
"@
    }

    "dev-up"       { Invoke-Dev "up -d" }
    "dev-down"     { Invoke-Dev "down" }
    "dev-restart"  { Invoke-Dev "down"; Invoke-Dev "up -d" }
    "prod-up"      { Invoke-Prod "up -d" }
    "prod-down"    { Invoke-Prod "down" }
    "prod-restart" { Invoke-Prod "down"; Invoke-Prod "up -d" }

    "clean" {
        Invoke-Dev "down -v --remove-orphans"
        if (Test-Path "frontend/node_modules") { Remove-Item -Recurse -Force "frontend/node_modules" }
        if (Test-Path "frontend/.next") { Remove-Item -Recurse -Force "frontend/.next" }
        Get-ChildItem -Path "backend" -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force
        if (Test-Path "backend/.pytest_cache") { Remove-Item -Recurse -Force "backend/.pytest_cache" }
        Write-Host "Cleaned."
    }

    default {
        Write-Host "Unknown command: $Command"
        Write-Host "Run '.\make.ps1 help' for available commands."
    }
}
