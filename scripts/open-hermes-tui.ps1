$ErrorActionPreference = "Stop"

$KeyPath = "C:\Users\itayc\.ssh\id_ed25519"
$HostName = "root@31.97.36.182"
$TmuxSession = "hermes-chat"

$command = "ssh -tt -i `"$KeyPath`" $HostName `"sudo -H -u aria bash -lc 'exec tmux attach-session -t $TmuxSession'`""

Start-Process -FilePath "powershell.exe" -ArgumentList @(
  "-NoExit",
  "-Command",
  $command
)
