$ErrorActionPreference = "Stop"

$revision = "2cfc18c9415c912f9d8155881c133215df768a70"
$totalBytes = 1112206140
$expectedSha256 = "ced967c45fd1902eb92716c9ceeca7c95a936770ea9db611f5a841b926e33fbd"
$url = "https://huggingface.co/BAAI/bge-reranker-base/resolve/$revision/model.safetensors?download=true"
$modelDir = "D:\python_projects\tsinghua_ai\data_second\rag_v1\indexes\reranker\model"
$partsDir = "D:\python_projects\tsinghua_ai\data_second\rag_v1\indexes\reranker\_download_parts"
$assembled = Join-Path $modelDir "model.download.safetensors"
$final = Join-Path $modelDir "model.safetensors"
$partCount = 8
$resolvedParts = [System.IO.Path]::GetFullPath($partsDir)
$allowedPrefix = [System.IO.Path]::GetFullPath("D:\python_projects\tsinghua_ai\data_second\rag_v1\indexes\reranker\")
if (-not $resolvedParts.StartsWith($allowedPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Temporary parts directory escaped the permitted RAG V1 reranker directory."
}

New-Item -ItemType Directory -Force $modelDir | Out-Null
New-Item -ItemType Directory -Force $partsDir | Out-Null
$partSize = [math]::Ceiling($totalBytes / $partCount)
$processes = @()
$parts = @()

for ($i = 0; $i -lt $partCount; $i++) {
    $start = [int64]($i * $partSize)
    $end = [int64][math]::Min($totalBytes - 1, (($i + 1) * $partSize) - 1)
    $partPath = Join-Path $partsDir ("part-{0:D2}.bin" -f $i)
    $expectedPartBytes = $end - $start + 1
    if ((Test-Path $partPath) -and ((Get-Item $partPath).Length -eq $expectedPartBytes)) {
        $parts += [pscustomobject]@{ Path = $partPath; Expected = $expectedPartBytes }
        continue
    }
    $args = @("-L", "--fail", "--retry", "3", "--range", "$start-$end", "--output", $partPath, $url)
    $proc = Start-Process -FilePath "curl.exe" -ArgumentList $args -WindowStyle Hidden -PassThru
    $processes += $proc
    $parts += [pscustomobject]@{ Path = $partPath; Expected = $expectedPartBytes }
}

foreach ($proc in $processes) {
    $proc.WaitForExit()
    if ($proc.ExitCode -ne 0) { throw "curl range worker $($proc.Id) failed with exit code $($proc.ExitCode)" }
}
foreach ($part in $parts) {
    if (-not (Test-Path $part.Path)) { throw "Missing range part: $($part.Path)" }
    if ((Get-Item $part.Path).Length -ne $part.Expected) {
        throw "Range part length mismatch: $($part.Path) actual=$((Get-Item $part.Path).Length) expected=$($part.Expected)"
    }
}

$outputStream = [System.IO.File]::Open($assembled, [System.IO.FileMode]::Create, [System.IO.FileAccess]::Write)
try {
    foreach ($part in $parts) {
        $inputStream = [System.IO.File]::OpenRead($part.Path)
        try { $inputStream.CopyTo($outputStream) } finally { $inputStream.Dispose() }
    }
} finally {
    $outputStream.Dispose()
}

if ((Get-Item $assembled).Length -ne $totalBytes) { throw "Assembled length mismatch" }
$actualSha256 = (Get-FileHash -Algorithm SHA256 $assembled).Hash.ToLowerInvariant()
if ($actualSha256 -ne $expectedSha256) { throw "SHA-256 mismatch: $actualSha256" }
Move-Item -Force -LiteralPath $assembled -Destination $final
Remove-Item -LiteralPath $partsDir -Recurse -Force
Write-Output "RERANKER_DOWNLOAD_PASS bytes=$totalBytes sha256=$actualSha256 revision=$revision"
