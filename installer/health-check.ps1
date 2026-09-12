param(
    [int]$Port = 8080,
    [int]$TimeoutSeconds = 60
)

$ErrorActionPreference = "Stop"
$deadline = (Get-Date).AddSeconds($TimeoutSeconds)
$uri = "http://127.0.0.1:$Port/"

while ((Get-Date) -lt $deadline) {
    try {
        $response = Invoke-WebRequest -Uri $uri -UseBasicParsing -TimeoutSec 5
        if ($response.StatusCode -eq 200) {
            Write-Host "Garage LPR is ready: $uri"
            exit 0
        }
    }
    catch {
        Start-Sleep -Seconds 2
    }
}

Write-Error "Garage LPR did not become ready within $TimeoutSeconds seconds."
exit 1
