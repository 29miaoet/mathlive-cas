# Start Flask
$flask = Start-Process pythonw -ArgumentList "$code/GitHub/mathlive-cas/app.py"

# Wait a second for it to spin up, then open Chrome and WAIT for Chrome to close
Start-Sleep -Seconds 1
Start-Process chrome -app="http://127.0.0.1:5000" -Wait

