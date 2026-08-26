param(
    [Parameter(Mandatory = $true)]
    [string[]]$Files,
    [string]$Selector = 'input.semi-upload-hidden-input',
    [string]$TabId = 'FB1A22E56892F039D170BDF6C7E9CFE4',
    [int]$Port = 9223
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$tabs = Invoke-RestMethod -NoProxy ("http://127.0.0.1:{0}/json" -f $Port)
$tab = $tabs | Where-Object { $_.id -eq $TabId } | Select-Object -First 1
if (-not $tab) { throw "CDP tab not found: $TabId" }

$socket = [Net.WebSockets.ClientWebSocket]::new()
$socket.Options.Proxy = $null
$cancel = [Threading.CancellationToken]::None
$null = $socket.ConnectAsync([Uri]::new([string]$tab.webSocketDebuggerUrl), $cancel).GetAwaiter().GetResult()
$nextId = 900
function Invoke-Cdp {
    param([string]$Method, [hashtable]$Params)
    $script:nextId += 1
    $requestId = $script:nextId
    $request = @{ id = $requestId; method = $Method; params = $Params } |
        ConvertTo-Json -Depth 30 -Compress
    $bytes = [Text.Encoding]::UTF8.GetBytes($request)
    $null = $socket.SendAsync(
        [ArraySegment[byte]]::new($bytes),
        [Net.WebSockets.WebSocketMessageType]::Text,
        $true,
        $cancel
    ).GetAwaiter().GetResult()
    while ($true) {
        $buffer = New-Object byte[] 1048576
        $stream = [IO.MemoryStream]::new()
        do {
            $message = $socket.ReceiveAsync([ArraySegment[byte]]::new($buffer), $cancel).GetAwaiter().GetResult()
            if ($message.MessageType -eq [Net.WebSockets.WebSocketMessageType]::Close) {
                throw 'CDP socket closed before the requested response arrived.'
            }
            $stream.Write($buffer, 0, $message.Count)
        } while (-not $message.EndOfMessage)
        $response = [Text.Encoding]::UTF8.GetString($stream.ToArray()) | ConvertFrom-Json
        if ($response.id -eq $requestId) {
            if ($response.error) { throw ($response.error | ConvertTo-Json -Compress) }
            return $response.result
        }
    }
}

try {
    $document = Invoke-Cdp 'DOM.getDocument' @{ depth = 1 }
    $match = Invoke-Cdp 'DOM.querySelector' @{
        nodeId = $document.root.nodeId
        selector = $Selector
    }
    if (-not $match.nodeId) { throw "File input not found: $Selector" }
    $resolved = @($Files | ForEach-Object { (Resolve-Path -LiteralPath $_).Path })
    $null = Invoke-Cdp 'DOM.setFileInputFiles' @{
        nodeId = $match.nodeId
        files = $resolved
    }
    @{ selector = $Selector; files = $resolved } | ConvertTo-Json -Depth 5
}
finally {
    $socket.Dispose()
}
