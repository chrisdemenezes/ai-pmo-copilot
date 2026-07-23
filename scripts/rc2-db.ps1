# STRATECH RC-2 -- PowerShell equivalent of rc2-db.sh (idempotent PostgreSQL
# app role/database management). See rc2-db.sh for the full rationale;
# kept as a thin parallel script rather than a shared implementation since
# bash and PowerShell can't share a script body.
#
# Usage: rc2-db.ps1 {create|reset|drop}
param(
    [ValidateSet("create", "reset", "drop")]
    [string]$Action = "create"
)
$ErrorActionPreference = "Stop"

$AppDb = if ($env:POSTGRES_DB) { $env:POSTGRES_DB } else { "aipmo" }
$AppUser = if ($env:POSTGRES_USER) { $env:POSTGRES_USER } else { "aipmo" }
$AppPassword = if ($env:POSTGRES_PASSWORD) { $env:POSTGRES_PASSWORD } else { "aipmo" }

$env:PGUSER = if ($env:PG_ADMIN_USER) { $env:PG_ADMIN_USER } else { "postgres" }
$env:PGDATABASE = if ($env:PG_ADMIN_DATABASE) { $env:PG_ADMIN_DATABASE } else { "postgres" }

if (-not (Get-Command psql -ErrorAction SilentlyContinue)) {
    Write-Error "psql not found. Install the PostgreSQL client tools before continuing."
    exit 1
}

function Invoke-AdminPsql([string]$Sql) {
    $result = psql -v ON_ERROR_STOP=1 -tAc $Sql
    return $result
}

function Stop-AppConnections {
    # backend_type = 'client backend' excludes autovacuum/background workers,
    # which a non-superuser admin role cannot terminate even on a database it owns.
    Invoke-AdminPsql "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$AppDb' AND pid <> pg_backend_pid() AND backend_type = 'client backend'" | Out-Null
}

switch ($Action) {
    "create" {
        Write-Host "Ensuring role '$AppUser' exists ..."
        Invoke-AdminPsql "DO `$`$ BEGIN IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '$AppUser') THEN CREATE ROLE $AppUser LOGIN PASSWORD '$AppPassword' CREATEDB; END IF; END `$`$;" | Out-Null
        Write-Host "Ensuring database '$AppDb' exists ..."
        $exists = Invoke-AdminPsql "SELECT 1 FROM pg_database WHERE datname='$AppDb'"
        if ($exists -ne "1") {
            Invoke-AdminPsql "CREATE DATABASE $AppDb OWNER $AppUser" | Out-Null
        }
        Write-Host "Database '$AppDb' ready (role '$AppUser')."
    }
    "reset" {
        Write-Host "Dropping and recreating '$AppDb' (all data will be lost) ..."
        Stop-AppConnections
        Invoke-AdminPsql "DROP DATABASE IF EXISTS $AppDb" | Out-Null
        Invoke-AdminPsql "CREATE DATABASE $AppDb OWNER $AppUser" | Out-Null
        Write-Host "Database '$AppDb' reset."
    }
    "drop" {
        Stop-AppConnections
        Invoke-AdminPsql "DROP DATABASE IF EXISTS $AppDb" | Out-Null
        Write-Host "Database '$AppDb' dropped."
    }
}
