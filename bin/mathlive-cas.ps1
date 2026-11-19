# Start Flask
$flask = Start-Process pythonw -ArgumentList "$code/GitHub/mathlive-cas/app.py"

Start-Sleep -Seconds 1
Start-Process chrome -app="http://127.0.0.1:5000" -Wait

