# tools/shots.ps1 - render the game's own screens to PNG on eagle1.
#
# The game saves its runtime viewport with --screenshot=<png> (Main.cs ShotPoll) and quits.
# This is the same recipe release.yml runs under xvfb; here it runs on the real GPU.
# Output goes to remake/build/shots/ (build/ is never committed).
#
# eagle1 has Windows PowerShell 5.1 only -- there is no pwsh on the box, so invoke it as:
#
#   powershell -NoProfile -ExecutionPolicy Bypass -File tools\shots.ps1                    # all screens, original files
#   powershell -NoProfile -ExecutionPolicy Bypass -File tools\shots.ps1 -Clean             # all screens, the clean pack
#   powershell -NoProfile -ExecutionPolicy Bypass -File tools\shots.ps1 -Only game,yard    # just those
#
# Exits non-zero if a screen produced no PNG, or its log shows an exception / missing resource.

[CmdletBinding()]
param(
  [switch]$Clean,
  [string[]]$Only,
  [string]$Out,
  [string]$Repo
)

$ErrorActionPreference = 'Stop'
$repo = if ($Repo) { $Repo } else { Split-Path -Parent $PSScriptRoot }
$game = Join-Path $repo 'remake\game'
if (-not $Out) { $Out = Join-Path $repo ($(if ($Clean) { 'remake\build\shots-clean' } else { 'remake\build\shots' })) }
New-Item -ItemType Directory -Force -Path $Out | Out-Null

# name -> the user args that select the screen. Same set and same seeds as release.yml,
# so a local frame and a CI frame are comparable.
$screens = [ordered]@{
  title     = @('--title', '--frames=120')
  game      = @('--seed=1234', '--ticks=600')
  yard      = @('--seed=1234', '--ticks=300', '--yard')
  history   = @('--seed=1234', '--ticks=600', '--history')
  antipedia = @('--antipedia')
  tutorial  = @('--tutorial=5')
}
# -File passes "a,b" as one string; accept both that and a real array.
$names = if ($Only) { @($Only) -split ',' | ForEach-Object { $_.Trim() } | Where-Object { $_ } } else { @($screens.Keys) }
foreach ($n in $names) { if (-not $screens.Contains($n)) { throw "unknown screen '$n' (have: $($screens.Keys -join ', '))" } }

$failed = @()
foreach ($name in $names) {
  $sel = $screens[$name]
  $png = Join-Path $Out "$name.png"
  $log = Join-Path $Out "$name.log"
  Remove-Item $png -ErrorAction SilentlyContinue

  $userArgs = @()
  if ($Clean) { $userArgs += '--clean' }
  $userArgs += $sel + @("--screenshot=$png")
  $argv = @('--path', $game, '--audio-driver', 'Dummy', '--') + $userArgs

  Write-Host "shot $name ..." -NoNewline
  $p = Start-Process -FilePath godot -ArgumentList $argv -PassThru -NoNewWindow `
         -RedirectStandardOutput $log -RedirectStandardError "$log.err"
  if (-not $p.WaitForExit(240000)) { $p.Kill(); Write-Host " TIMEOUT"; $failed += "$name (timeout)"; continue }

  $text = (Get-Content $log, "$log.err" -Raw -ErrorAction SilentlyContinue) -join "`n"
  if (-not (Test-Path $png) -or (Get-Item $png).Length -eq 0) { Write-Host " NO PNG"; $failed += "$name (no png)"; continue }
  if ($text -match 'Unhandled exception|[A-Za-z.]+Exception:| is missing') { Write-Host " FAILED"; $failed += "$name (see $log)"; continue }
  Write-Host (" {0} ({1:n0} bytes)" -f $png, (Get-Item $png).Length)
}

if ($failed) { Write-Host "`nfailed: $($failed -join ', ')"; exit 1 }
Write-Host "`nok - $Out"
