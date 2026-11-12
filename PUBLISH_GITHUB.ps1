# Standalone publishing helper. It does NOT create a GitHub repository.
# Run after you create an EMPTY GitHub repository and verify its URL.
param([Parameter(Mandatory=$true)][ValidatePattern('^https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(\.git)?$')][string]$RepoUrl)
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$python = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path $python)) { $python = 'python' }
& $python -m phase6.release_checks
if ($LASTEXITCODE -ne 0) { throw 'Source audit blocked publication.' }
if (-not (Test-Path '.git')) { git init }
git add .
git diff --cached --check
if ($LASTEXITCODE -ne 0) { throw 'Staged whitespace/conflict markers check failed.' }
& $python -m phase6.release_checks --git-only
if ($LASTEXITCODE -ne 0) { throw 'Staged-file audit blocked publication.' }
Write-Host 'Review staged content before publishing:'
git status --short
$choice = Read-Host 'Publish these staged source files? Type PUBLISH to confirm'
if ($choice -cne 'PUBLISH') { throw 'Cancelled without pushing.' }
$changes = git diff --cached --quiet; $hasChanges = $LASTEXITCODE -eq 1
if ($hasChanges) { git commit -m 'Release manufacturing copilot phases 1-6 with reproducible evaluation' }
git branch -M main
$existing = git remote get-url origin 2>$null
if ($LASTEXITCODE -ne 0) { git remote add origin $RepoUrl }
elseif (($existing.TrimEnd('/')) -ne ($RepoUrl.TrimEnd('/'))) { throw "Existing origin $existing differs from requested repo $RepoUrl. Refusing to retarget." }
# No force-push. If remote has pre-existing commits, the user must reconcile them explicitly.
git push -u origin main
if ($LASTEXITCODE -ne 0) { throw 'Push did not complete. Remote may not be empty or GitHub authentication is needed.' }
Write-Host 'GitHub push completed successfully.'
