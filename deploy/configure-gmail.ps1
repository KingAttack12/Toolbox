$ErrorActionPreference = 'Stop'
$key = Join-Path $env:USERPROFILE 'OneDrive\Documents\ssh-key-2026-09-22.key'
Write-Host "Configuration Gmail de Toolbox. Le secret sera saisi directement sur le serveur et restera invisible."
& ssh -t -i $key ubuntu@141.253.106.219 '/home/ubuntu/toolbox/.venv/bin/python /home/ubuntu/toolbox/deploy/configure-mail.py'
if ($LASTEXITCODE -ne 0) { Write-Host 'Configuration non terminee.' }
Read-Host 'Appuyez sur Entree pour fermer'
