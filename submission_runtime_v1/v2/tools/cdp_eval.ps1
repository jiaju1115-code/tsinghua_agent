param(
    [Parameter(Mandatory = $true)]
    [string]$Expression,
    [string]$TabId = '4DEBD8157D6CF144CD5ECA46103A2949',
    [int]$Port = 9222
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$tabs = Invoke-RestMethod -NoProxy ("http://127.0.0.1:{0}/json" -f $Port)
$tab = $tabs | Where-Object { $_.id -eq $TabId } | Select-Object -First 1
if (-not $tab) {
    throw "CDP tab not found: $TabId"
}

$socket = [Net.WebSockets.ClientWebSocket]::new()
$socket.Options.Proxy = $null
$cancel = [Threading.CancellationToken]::None
$debugUrl = [string]$tab.webSocketDebuggerUrl
$null = $socket.ConnectAsync([Uri]::new($debugUrl), $cancel).GetAwaiter().GetResult()
try {
    $requestId = 777
    $request = @{
        id = $requestId
        method = 'Runtime.evaluate'
        params = @{
            expression = $Expression
            awaitPromise = $true
            returnByValue = $true
        }
    } | ConvertTo-Json -Depth 20 -Compress
    $requestBytes = [Text.Encoding]::UTF8.GetBytes($request)
    $null = $socket.SendAsync(
        [ArraySegment[byte]]::new($requestBytes),
        [Net.WebSockets.WebSocketMessageType]::Text,
        $true,
        $cancel
    ).GetAwaiter().GetResult()

    while ($true) {
        $buffer = New-Object byte[] 1048576
        $stream = [IO.MemoryStream]::new()
        do {
            $message = $socket.ReceiveAsync(
                [ArraySegment[byte]]::new($buffer),
                $cancel
            ).GetAwaiter().GetResult()
            if ($message.MessageType -eq [Net.WebSockets.WebSocketMessageType]::Close) {
                throw 'CDP socket closed before the requested response arrived.'
            }
            $stream.Write($buffer, 0, $message.Count)
        } while (-not $message.EndOfMessage)
        $response = [Text.Encoding]::UTF8.GetString($stream.ToArray()) | ConvertFrom-Json
        if ($response.id -eq $requestId) {
            if ($response.error) {
                throw ($response.error | ConvertTo-Json -Compress)
            }
            $response.result.result.value | ConvertTo-Json -Depth 30
            break
        }
    }
}
finally {
    $socket.Dispose()
}
