param([string]$RuntimeRoot=(Join-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) 'riff-generator-runtime'))
$ErrorActionPreference='Stop'
$RuntimeRoot=[IO.Path]::GetFullPath($RuntimeRoot)
if([IO.Path]::GetPathRoot($RuntimeRoot) -eq 'C:\'){throw 'Project runtime must not be on C.'}
foreach($name in @('temp','logs','cache')){New-Item -ItemType Directory -Force -Path (Join-Path $RuntimeRoot $name)|Out-Null}
$env:TEMP=Join-Path $RuntimeRoot 'temp';$env:TMP=$env:TEMP;$env:TMPDIR=$env:TEMP
$env:PYTHONDONTWRITEBYTECODE='1';$env:PYTHONPYCACHEPREFIX=Join-Path $RuntimeRoot 'cache\python'
$env:PIP_CACHE_DIR=Join-Path $RuntimeRoot 'cache\pip';$env:XDG_CACHE_HOME=Join-Path $RuntimeRoot 'cache';$env:MPLCONFIGDIR=Join-Path $RuntimeRoot 'cache\matplotlib';$env:NUMBA_CACHE_DIR=Join-Path $RuntimeRoot 'cache\numba'
$env:RIFF_SESSION_COOKIE='riff_weights_session'
$env:RIFF_CSV=Join-Path $RuntimeRoot 'data\all_riffs_phrase_composition.csv'
$env:RIFF_TIMING=Join-Path $RuntimeRoot 'data\pitch_free_all_lengths_phrase_rhythms.json'
$env:RIFF_KONTAKT_PRESET_DIR=Join-Path $RuntimeRoot 'renderer'
$env:RIFF_KONTAKT_MANIFEST=Join-Path $RuntimeRoot 'renderer\hydra-verified-manifest.json'
$env:RIFF_RENDER_WORKER=Join-Path $RuntimeRoot 'renderer\kontakt_isolated_worker.py'
$env:RIFF_RENDER_PYTHON=Join-Path $env:USERPROFILE 'kontakt-render-test\venv312\Scripts\python.exe'
$env:RIFF_KONTAKT_PRESETS='modern-metal-1,ready-to-djent'
$python=Join-Path $env:LOCALAPPDATA 'Programs\Python\Python310\python.exe'
foreach($path in @($python,$env:RIFF_RENDER_PYTHON,$env:RIFF_CSV,$env:RIFF_TIMING,$env:RIFF_KONTAKT_MANIFEST,$env:RIFF_RENDER_WORKER,(Join-Path $RuntimeRoot 'app\server.py'),(Join-Path $RuntimeRoot 'app\save_service.py'))){if(!(Test-Path -LiteralPath $path -PathType Leaf)){throw "Missing runtime asset: $path"}}
$expected=@{csv='b03b60a56ef9b7f774c5a5b8ec1a571a44bb8132534f50484bd401d43e4c849e';timing='d9a651448fea4ce9a5e8005d584ff4ea68a23e31ba207107567a419448cb18c2'}
if((Get-FileHash -LiteralPath $env:RIFF_CSV).Hash -ne $expected.csv -or (Get-FileHash -LiteralPath $env:RIFF_TIMING).Hash -ne $expected.timing){throw 'Dataset hash mismatch'}
$manifest=Get-Content -LiteralPath $env:RIFF_KONTAKT_MANIFEST -Raw|ConvertFrom-Json
foreach($preset in $manifest.presets){if($preset.verified){$path=Join-Path $env:RIFF_KONTAKT_PRESET_DIR $preset.state_file;if((Get-FileHash -LiteralPath $path).Hash -ne $preset.state_sha256){throw "Preset hash mismatch: $($preset.id)"}}}
$record=@{runtime_root=$RuntimeRoot;environment=@{};installed_read_only=@($python,$env:RIFF_RENDER_PYTHON);started_utc=[DateTime]::UtcNow.ToString('o')}
foreach($key in @('TEMP','TMP','TMPDIR','PYTHONDONTWRITEBYTECODE','PYTHONPYCACHEPREFIX','PIP_CACHE_DIR','XDG_CACHE_HOME','MPLCONFIGDIR','NUMBA_CACHE_DIR','RIFF_SESSION_COOKIE','RIFF_CSV','RIFF_TIMING','RIFF_KONTAKT_PRESET_DIR','RIFF_KONTAKT_MANIFEST','RIFF_RENDER_WORKER','RIFF_RENDER_PYTHON')){$record.environment[$key]=[Environment]::GetEnvironmentVariable($key)}
$server=Start-Process -FilePath $python -ArgumentList @('-B',('"'+(Join-Path $RuntimeRoot 'app\server.py')+'"'),'--host','0.0.0.0','--port','8878') -WorkingDirectory $RuntimeRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $RuntimeRoot 'logs\server.stdout.log') -RedirectStandardError (Join-Path $RuntimeRoot 'logs\server.stderr.log') -PassThru
$record.server_pid=$server.Id
$ready=$false
for($i=0;$i -lt 180;$i++){try{$config=Invoke-RestMethod 'http://127.0.0.1:8878/api/config' -TimeoutSec 2;if($config.dataset.csv_sha256 -eq $expected.csv -and $config.dataset.timing_sha256 -eq $expected.timing){$ready=$true;break}}catch{};Start-Sleep -Seconds 1}
if(!$ready){$record|ConvertTo-Json -Depth 6|Set-Content (Join-Path $RuntimeRoot 'logs\launch.json');throw 'Generator failed readiness; inspect F logs'}
$companion=Start-Process -FilePath $python -ArgumentList @('-B',('"'+(Join-Path $RuntimeRoot 'app\save_service.py')+'"'),'--repo',('"'+(Join-Path $RuntimeRoot 'midi-saves')+'"'),'--host','0.0.0.0','--port','8879','--source-port','8878','--origin','http://127.0.0.1:8878','--origin','http://192.168.0.12:8878') -WorkingDirectory $RuntimeRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $RuntimeRoot 'logs\companion.stdout.log') -RedirectStandardError (Join-Path $RuntimeRoot 'logs\companion.stderr.log') -PassThru
$record.companion_pid=$companion.Id;$record|ConvertTo-Json -Depth 6|Set-Content (Join-Path $RuntimeRoot 'logs\launch.json')
$record
