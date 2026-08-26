param(
    [string]$TabId = 'FB1A22E56892F039D170BDF6C7E9CFE4',
    [int]$Port = 9223,
    [int]$TimeoutSeconds = 20
)

$ErrorActionPreference = 'Stop'
$tabs = Invoke-RestMethod -NoProxy ("http://127.0.0.1:{0}/json" -f $Port)
$tab = $tabs | Where-Object { $_.id -eq $TabId } | Select-Object -First 1
if (-not $tab) { throw "CDP tab not found: $TabId" }

$socket = [Net.WebSockets.ClientWebSocket]::new()
$socket.Options.Proxy = $null
$cancel = [Threading.CancellationToken]::None
$null = $socket.ConnectAsync([Uri]::new([string]$tab.webSocketDebuggerUrl), $cancel).GetAwaiter().GetResult()

function Send-Cdp([int]$Id, [string]$Method, [hashtable]$Params) {
    $request = @{ id = $Id; method = $Method; params = $Params } | ConvertTo-Json -Depth 30 -Compress
    $bytes = [Text.Encoding]::UTF8.GetBytes($request)
    $null = $socket.SendAsync([ArraySegment[byte]]::new($bytes), [Net.WebSockets.WebSocketMessageType]::Text, $true, $cancel).GetAwaiter().GetResult()
}

try {
    Send-Cdp 1 'Network.enable' @{}
    Send-Cdp 2 'Page.reload' @{ ignoreCache = $false }
    $deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
    $bodyRequestId = $null
    while ([DateTime]::UtcNow -lt $deadline) {
        $buffer = New-Object byte[] 1048576
        $stream = [IO.MemoryStream]::new()
        do {
            $message = $socket.ReceiveAsync([ArraySegment[byte]]::new($buffer), $cancel).GetAwaiter().GetResult()
            if ($message.MessageType -eq [Net.WebSockets.WebSocketMessageType]::Close) { throw 'CDP socket closed.' }
            $stream.Write($buffer, 0, $message.Count)
        } while (-not $message.EndOfMessage)
        $event = [Text.Encoding]::UTF8.GetString($stream.ToArray()) | ConvertFrom-Json
        if ($event.method -eq 'Network.responseReceived' -and [string]$event.params.response.url -match '/studio/api/workflow_api/canvas') {
            $bodyRequestId = [string]$event.params.requestId
            break
        }
    }
    if (-not $bodyRequestId) { throw 'Canvas response was not observed before timeout.' }
    Send-Cdp 3 'Network.getResponseBody' @{ requestId = $bodyRequestId }
    while ([DateTime]::UtcNow -lt $deadline.AddSeconds(5)) {
        $buffer = New-Object byte[] 1048576
        $stream = [IO.MemoryStream]::new()
        do {
            $message = $socket.ReceiveAsync([ArraySegment[byte]]::new($buffer), $cancel).GetAwaiter().GetResult()
            if ($message.MessageType -eq [Net.WebSockets.WebSocketMessageType]::Close) { throw 'CDP socket closed.' }
            $stream.Write($buffer, 0, $message.Count)
        } while (-not $message.EndOfMessage)
        $event = [Text.Encoding]::UTF8.GetString($stream.ToArray()) | ConvertFrom-Json
        if ($event.id -eq 3) {
            $event.result | ConvertTo-Json -Depth 50
            break
        }
    }
}
finally { $socket.Dispose() }
