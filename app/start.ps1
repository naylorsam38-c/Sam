# Starts the app on http://127.0.0.1:8787
#
#   1. Set your two secrets once (per PowerShell window):
#        $env:ANTHROPIC_API_KEY = "sk-ant-..."
#        $env:APP_PASSWORD      = "pick-a-password"
#   2. Run this script:
#        .\start.ps1
#
# A password shorter than 8 characters is refused by server.js. To keep a short
# password, set its SHA-256 instead of the plaintext - the length check does not
# apply to a hash:
#        $env:APP_PASSWORD_HASH = "<sha256 hex of your password>"
#
# To make the key and password stick across reboots instead, run once:
#   [Environment]::SetEnvironmentVariable("ANTHROPIC_API_KEY","sk-ant-...","User")
#   [Environment]::SetEnvironmentVariable("APP_PASSWORD","pick-a-password","User")
# then open a new PowerShell window.

$ErrorActionPreference = "Stop"

if (-not $env:ANTHROPIC_API_KEY) {
  $env:ANTHROPIC_API_KEY = [Environment]::GetEnvironmentVariable("ANTHROPIC_API_KEY", "User")
}
if (-not $env:APP_PASSWORD) {
  $env:APP_PASSWORD = [Environment]::GetEnvironmentVariable("APP_PASSWORD", "User")
}
if (-not $env:APP_PASSWORD_HASH) {
  $env:APP_PASSWORD_HASH = [Environment]::GetEnvironmentVariable("APP_PASSWORD_HASH", "User")
}

if (-not $env:ANTHROPIC_API_KEY) { Write-Host "ANTHROPIC_API_KEY is not set - chat and the planner will return an error." -ForegroundColor Yellow }
if (-not $env:APP_PASSWORD -and -not $env:APP_PASSWORD_HASH) { Write-Error "Neither APP_PASSWORD nor APP_PASSWORD_HASH is set. Set one, then run this again." }

# Keeps sessions valid across restarts. Generated once, stored for this user.
if (-not $env:SESSION_SECRET) {
  $secret = [Environment]::GetEnvironmentVariable("SAM_SESSION_SECRET", "User")
  if (-not $secret) {
    $bytes = New-Object byte[] 32
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
    $secret = [System.BitConverter]::ToString($bytes).Replace("-", "").ToLower()
    [Environment]::SetEnvironmentVariable("SAM_SESSION_SECRET", $secret, "User")
  }
  $env:SESSION_SECRET = $secret
}

# Loopback only. Nothing outside this machine can reach it.
$env:HOST = "127.0.0.1"
$env:PORT = "8787"

Set-Location $PSScriptRoot
Write-Host "Open http://127.0.0.1:8787 in your browser." -ForegroundColor Green
node server.js
