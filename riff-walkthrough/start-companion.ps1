param(
  [string]$AppDirectory = (Join-Path $PSScriptRoot 'app'),
  [string]$MidiRepository = (Join-Path $PSScriptRoot 'midi-saves'),
  [string]$RenderDirectory = (Join-Path $env:USERPROFILE 'kontakt-render-test'),
  [string]$ServicePython = (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python310\python.exe'),
  [int]$Port = 8879,
  [int]$SourcePort = 8878,
  [string]$SessionCookie = 'riff_weights_session',
  [string[]]$Origins = @('http://127.0.0.1:8878','http://192.168.0.12:8878')
)
$ErrorActionPreference = 'Stop'
$env:RIFF_SESSION_COOKIE = $SessionCookie
$env:RIFF_KONTAKT_PRESET_DIR = $RenderDirectory
$env:RIFF_RENDER_PYTHON = Join-Path $RenderDirectory 'venv312\Scripts\python.exe'
$env:RIFF_RENDER_WORKER = Join-Path $RenderDirectory 'kontakt_isolated_worker.py'
$env:RIFF_KONTAKT_PRESETS = 'modern-metal-1,ready-to-djent'
foreach($path in @($ServicePython,$env:RIFF_RENDER_PYTHON,$env:RIFF_RENDER_WORKER,(Join-Path $RenderDirectory 'verify-console-live.state'),(Join-Path $RenderDirectory 'verify-console-djent.state'),(Join-Path $AppDirectory 'save_service.py'))) {
  if(!(Test-Path -LiteralPath $path -PathType Leaf)){throw "Required companion asset missing: $path"}
}
$arguments = @('-B',('"'+(Join-Path $AppDirectory 'save_service.py')+'"'),'--repo',('"'+$MidiRepository+'"'),'--host','0.0.0.0','--port',"$Port",'--source-port',"$SourcePort")
foreach($origin in $Origins){$arguments += @('--origin',$origin)}
Start-Process -FilePath $ServicePython -ArgumentList $arguments -WindowStyle Hidden -PassThru
