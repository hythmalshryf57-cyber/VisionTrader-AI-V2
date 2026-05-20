Write-Output '=== ROOT PAGE ==='
try{
  $r = Invoke-WebRequest -Uri 'http://127.0.0.1:8000/' -UseBasicParsing -TimeoutSec 20
  Write-Output "StatusCode: $($r.StatusCode)"
  Write-Output "Length: $($r.RawContent.Length)"
}catch{
  Write-Output "ERROR: $($_.Exception.Message)"
}

Write-Output ''
Write-Output '=== CALENDAR PAGE ==='
try{
  $r = Invoke-WebRequest -Uri 'http://127.0.0.1:8000/calendar.html' -UseBasicParsing -TimeoutSec 20
  Write-Output "StatusCode: $($r.StatusCode)"
  Write-Output "Length: $($r.RawContent.Length)"
}catch{
  Write-Output "ERROR: $($_.Exception.Message)"
}

Write-Output ''
Write-Output '=== BACKTEST PAGE ==='
try{
  $r = Invoke-WebRequest -Uri 'http://127.0.0.1:8000/backtest.html' -UseBasicParsing -TimeoutSec 20
  Write-Output "StatusCode: $($r.StatusCode)"
  Write-Output "Length: $($r.RawContent.Length)"
}catch{
  Write-Output "ERROR: $($_.Exception.Message)"
}

Write-Output ''
Write-Output '=== HEALTH ==='
try{
  $r = Invoke-RestMethod -Uri 'http://127.0.0.1:8000/api/health' -Method GET -TimeoutSec 20
  Write-Output (ConvertTo-Json $r -Depth 2)
}catch{
  Write-Output "ERROR: $($_.Exception.Message)"
}

Write-Output ''
Write-Output '=== GET /api/calendar/events ==='
try{
  $r = Invoke-RestMethod -Uri 'http://127.0.0.1:8000/api/calendar/events' -Method GET -TimeoutSec 20
  if($r -is [System.Array]){
    Write-Output "Count: $($r.Count)"
  } else {
    Write-Output "Result:"
    Write-Output (ConvertTo-Json $r -Depth 3)
  }
}catch{
  Write-Output "ERROR: $($_.Exception.Message)"
}

Write-Output ''
Write-Output '=== POST /api/backtest/run ==='
try{
  $body = @{market='BTC/USDT'; timeframe='1h'; start_date='2023-01-01'; end_date='2023-02-01'} | ConvertTo-Json
  $r = Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8000/api/backtest/run' -ContentType 'application/json' -Body $body -TimeoutSec 60
  Write-Output 'Response:'
  Write-Output (ConvertTo-Json $r -Depth 4)
}catch{
  Write-Output "ERROR: $($_.Exception.Message)"
}
