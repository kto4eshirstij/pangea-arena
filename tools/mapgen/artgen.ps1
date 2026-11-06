# Generate skin art with the Higgsfield CLI from a job list, then build the texture set via art2skin.py.
# Usage: tools\mapgen\artgen.ps1 -Jobs tools\mapgen\art-jobs-siberian_core.json [-Pick wall_a,floor_a] [-SkipExisting]
param([Parameter(Mandatory=$true)][string]$Jobs, [string]$Pick = "", [switch]$SkipExisting)
$ErrorActionPreference = "Continue"
$repo = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $repo
$hf = "$env:APPDATA\npm\higgsfield.cmd"
$spec = Get-Content -LiteralPath (Join-Path $repo $Jobs) -Raw -Encoding UTF8 | ConvertFrom-Json
$skinName = $spec.skin
$rawDir = Join-Path $repo "content\pangea\art\$skinName"
New-Item -ItemType Directory -Force -Path $rawDir | Out-Null
$pickList = @(); if ($Pick -ne "") { $pickList = $Pick.Split(",") }
"artgen: skin=$skinName model=$($spec.model) jobs=$($spec.jobs.Count) pick=[$Pick] skipExisting=$SkipExisting"
$refs = @{}
foreach ($job in $spec.jobs) {
  $name = [string]$job.name
  if ($pickList.Count -gt 0 -and ($pickList -notcontains $name)) { continue }
  $existing = Get-ChildItem -LiteralPath $rawDir -File -ErrorAction SilentlyContinue | Where-Object { $_.BaseName -eq $name -and $_.Extension -in ".png",".jpg",".jpeg",".webp" } | Select-Object -First 1
  if ($existing -and $SkipExisting) { "skip $name (have $($existing.Name))"; $refs[$name] = $existing.FullName; continue }
  $cli = @("generate", "create", [string]$spec.model, "--prompt", [string]$job.prompt, "--aspect_ratio", [string]$job.aspect, "--resolution", [string]$spec.resolution, "--seed", [string]$spec.seed, "--thinking_level", "medium", "--wait", "--wait-timeout", "8m", "--json")
  if ($job.ref -and $refs.ContainsKey([string]$job.ref)) { $cli += @("--image-references", $refs[[string]$job.ref]) }
  "== $name [$($job.aspect)] =="
  $t0 = Get-Date
  $out = (& $hf @cli 2>&1) | Out-String
  [IO.File]::WriteAllText((Join-Path $rawDir "$name.json"), $out)
  $m = [regex]::Match($out, '"result_url":\s*"([^"]+)"')
  if (-not $m.Success) { "  no result_url; tail: " + (($out -split "`n" | Select-Object -Last 4) -join " | "); continue }
  $url = $m.Groups[1].Value
  $ext = ([uri]$url).AbsolutePath.Split(".")[-1]
  $file = Join-Path $rawDir "$name.$ext"
  try {
    Invoke-WebRequest -Uri $url -OutFile $file -UseBasicParsing
    "  saved $name.$ext ($([math]::Round((Get-Item $file).Length/1KB)) KB) in $([math]::Round(((Get-Date)-$t0).TotalSeconds)) s"
    $refs[$name] = $file
  } catch { "  download failed: $_" }
}
"== art2skin =="
& py -3.11 tools\mapgen\art2skin.py $skinName 2>&1 | Out-String
