$ErrorActionPreference = "Stop"
$revision = "7999e1d3359715c523056ef9478215996d62a620"
$expectedBytes = 95827648
$expectedSha256 = "354763b9b1357bc9c44f62c6be2276321081ed2567773608c0d0785b61d5a026"
$modelDir = "D:\python_projects\tsinghua_ai\data_second\rag_v1\indexes\dense\model"
$files = @("config.json", "special_tokens_map.json", "tokenizer.json", "tokenizer_config.json", "vocab.txt")
New-Item -ItemType Directory -Force $modelDir | Out-Null
foreach ($name in $files) {
    $target = Join-Path $modelDir $name
    if ((Test-Path $target) -and ((Get-Item $target).Length -gt 0)) { continue }
    $url = "https://huggingface.co/BAAI/bge-small-zh-v1.5/resolve/$revision/$name?download=true"
    & curl.exe --silent --show-error -L --fail --retry 5 --output $target $url
    if ($LASTEXITCODE -ne 0) { throw "Failed to download $name" }
}
$weights = Join-Path $modelDir "model.safetensors"
$valid = (Test-Path $weights) -and ((Get-Item $weights).Length -eq $expectedBytes)
if ($valid) { $valid = ((Get-FileHash -Algorithm SHA256 $weights).Hash.ToLowerInvariant() -eq $expectedSha256) }
if (-not $valid) {
    $download = Join-Path $modelDir "model.download.safetensors"
    $url = "https://huggingface.co/BAAI/bge-small-zh-v1.5/resolve/$revision/model.safetensors?download=true"
    & curl.exe --silent --show-error -L --fail --retry 5 --output $download $url
    if ($LASTEXITCODE -ne 0) { throw "Failed to download Dense weights" }
    if ((Get-Item $download).Length -ne $expectedBytes) { throw "Dense weight byte length mismatch" }
    $actual = (Get-FileHash -Algorithm SHA256 $download).Hash.ToLowerInvariant()
    if ($actual -ne $expectedSha256) { throw "Dense weight SHA-256 mismatch: $actual" }
    Move-Item -Force -LiteralPath $download -Destination $weights
}
Write-Output "DENSE_DOWNLOAD_PASS bytes=$expectedBytes sha256=$expectedSha256 revision=$revision"
