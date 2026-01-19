$targetPrice = 95000
$checkInterval = 30  # seconds

Write-Host "🚀 Bitcoin Price Monitor Started" -ForegroundColor Cyan
Write-Host "Alert threshold: $targetPrice" -ForegroundColor Yellow
Write-Host ""

while ($true) {
    try {
        $response = Invoke-RestMethod "http://localhost:8000/api/v1/market"
        $currentPrice = $response.last_price

        Write-Host "Current price: $currentPrice"

        if ($currentPrice -ge $targetPrice) {
            Write-Host "🚨 Target price reached!" -ForegroundColor Green
            break
        }
    }
    catch {
        Write-Host "Error fetching data: $_" -ForegroundColor Red
    }

    Start-Sleep -Seconds $checkInterval
}