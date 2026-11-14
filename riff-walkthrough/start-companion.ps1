param(
  [string]$AppDirectory = (Join-Path $PSScriptRoot 'app'),
  [string]$MidiRepository = (Join-Path $PSScriptRoot 'midi-saves'),
  [string]$RenderDirectory = (Join-Path $env:USERPROFILE 'kontakt-render-test'),
  [string]$ServicePython = (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python310\python.exe'),
  [string]$CsvPath = (Join-Path $env:USERPROFILE 'riff-csv-engine\full-export\all_riffs_phrase_composition.csv'),
  [string]$TimingPath = (Join-Path $env:USERPROFILE 'riff-csv-engine\pitch-free-all-lengths\pitch_free_all_lengths_phrase_rhythms.json'),
  [int]$Port = 8879,
  [int]$SourcePort = 8878,
  [string]$SessionCookie = 'riff_weights_session',
  [string[]]$Origins = @('http://127.0.0.1:8878','http://192.168.0.12:8878')
)
$ErrorActionPreference = 'Stop'
$env:RIFF_SESSION_COOKIE = $SessionCookie
$env:RIFF_CSV = $CsvPath
$env:RIFF_TIMING = $TimingPath
$env:RIFF_KONTAKT_PRESET_DIR = $RenderDirectory
$env:RIFF_RENDER_PYTHON = Join-Path $RenderDirectory 'venv312\Scripts\python.exe'
$env:RIFF_RENDER_WORKER = Join-Path $RenderDirectory 'kontakt_isolated_worker.py'
$env:RIFF_KONTAKT_PRESETS = 'modern-metal-1,ready-to-djent'
foreach($path in @($CsvPath,$TimingPath,$ServicePython,$env:RIFF_RENDER_PYTHON,$env:RIFF_RENDER_WORKER,(Join-Path $RenderDirectory 'verify-console-live.state'),(Join-Path $RenderDirectory 'verify-console-djent.state'),(Join-Path $AppDirectory 'save_service.py'))) {
  if(!(Test-Path -LiteralPath $path -PathType Leaf)){throw "Required companion asset missing: $path"}
}
# Refuse mismatched datasets instead of starting a partially functional companion.
$dataset = (Invoke-RestMethod -Uri "http://127.0.0.1:$SourcePort/api/config" -TimeoutSec 30).dataset
if((Get-FileHash -LiteralPath $CsvPath -Algorithm SHA256).Hash -ne $dataset.csv_sha256 -or (Get-FileHash -LiteralPath $TimingPath -Algorithm SHA256).Hash -ne $dataset.timing_sha256){throw 'Companion datasets do not match the running generator.'}
$arguments = @('-B',('"'+(Join-Path $AppDirectory 'save_service.py')+'"'),'--repo',('"'+$MidiRepository+'"'),'--host','0.0.0.0','--port',"$Port",'--source-port',"$SourcePort")
foreach($origin in $Origins){$arguments += @('--origin',$origin)}
Start-Process -FilePath $ServicePython -ArgumentList $arguments -WindowStyle Hidden -PassThru
