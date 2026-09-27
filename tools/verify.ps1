$ErrorActionPreference = 'Stop'

$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location $root

# ---------------------------------------------------------------------------
# 1) Java backend: build all modules and run the integration test suite
# ---------------------------------------------------------------------------
$mvn = 'D:\apache-maven-3.9.16\bin\mvn.cmd'
if (-not (Test-Path $mvn)) {
    $cmd = Get-Command mvn -ErrorAction SilentlyContinue
    if ($cmd) { $mvn = $cmd.Source } else { throw 'Maven not found (set MAVEN_HOME or install Maven 3.9+).' }
}

Write-Output '[verify] building Java backend (pestkg-api + dependencies) and running tests...'
& $mvn -f apps/java/pom.xml -pl pestkg-api -am clean package -q
if ($LASTEXITCODE -ne 0) { throw 'Java build or tests failed.' }
Write-Output '[verify] Java build + tests OK.'

# ---------------------------------------------------------------------------
# 2) API smoke test against the real v1.0 release
# ---------------------------------------------------------------------------
$jar = Get-ChildItem apps\java\pestkg-api\target\pestkg-api-*.jar |
    Where-Object { $_.Name -notmatch 'sources|javadoc' } | Select-Object -First 1
if (-not $jar) { throw 'pestkg-api jar not found after build.' }

$env:PESTKG_DATA_DIR = Join-Path $root 'data\releases'
$env:PESTKG_STATE_DIR = Join-Path $root 'data\state'
$env:PESTKG_RELEASE_ID = 'PestKG_A_Data_Release_v1.0'
$port = 18088

$proc = Start-Process java -ArgumentList @('-jar', $jar.FullName, "--server.port=$port") -PassThru -WindowStyle Hidden
try {
    $deadline = (Get-Date).AddSeconds(60)
    $health = $null
    while ((Get-Date) -lt $deadline) {
        try { $health = Invoke-RestMethod "http://127.0.0.1:$port/health" -TimeoutSec 3; break }
        catch { Start-Sleep -Seconds 2 }
    }
    if (-not $health) { throw 'API health check timed out.' }

    $base = "http://127.0.0.1:$port/api/v1"
    $overview = (Invoke-RestMethod "$base/datasets/overview" -TimeoutSec 90).data
    if ($overview.mode -ne 'full') { throw "expected data_mode 'full', got '$($overview.mode)'." }
    if ([int]$overview.inventory.kg_nodes -lt 1000000) {
        throw "full release inventory below expectation: kg_nodes=$($overview.inventory.kg_nodes)"
    }
    if (($overview.node_types.PSObject.Properties | Measure-Object).Count -lt 5) { throw 'overview node_types look empty.' }

    $null = Invoke-RestMethod "$base/entities/search?q=&limit=3" -TimeoutSec 30
    Write-Output '[verify] empty search OK (no crash).'

    $body = @{ filters = @{ product = 'Frutor Fungicide' }; page_size = 2 } | ConvertTo-Json -Depth 4
    $uses = Invoke-RestMethod "$base/registration-uses/query" -Method Post -ContentType 'application/json' -Body $body -TimeoutSec 180
    if ([int]$uses.meta.total -le 0) { throw 'registration-uses product filter returned no rows.' }
    $first = $uses.data | Select-Object -First 1
    if (-not $first.product_label_original) { throw 'enriched registration uses missing product label.' }

    $countries = (Invoke-RestMethod "$base/datasets/coverage" -TimeoutSec 30).data
    if ($countries.Count -lt 1) { throw 'coverage/countries returned no entries.' }

    Write-Output "[verify] API smoke OK: mode=$($overview.mode) kg_nodes=$($overview.inventory.kg_nodes) " +
        "kg_edges=$($overview.inventory.kg_edges) uses_total=$($uses.meta.total)"
}
finally {
    if ($proc) { Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue }
    # Belt-and-braces: kill whatever still listens on the smoke-test port.
    $listeners = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    foreach ($l in $listeners) { Stop-Process -Id $l.OwningProcess -Force -ErrorAction SilentlyContinue }
}

# ---------------------------------------------------------------------------
# 3) Web checks (only when dependencies are installed)
# ---------------------------------------------------------------------------
if (Get-Command npm -ErrorAction SilentlyContinue) {
    if (Test-Path 'apps\web\node_modules') {
        $generatedPaths = @(
            'apps/web/src/shared/api/generated/types.gen.ts',
            'apps/web/src/shared/api/generated/index.ts',
            'apps/web/src/shared/api/browser-generated/types.gen.ts',
            'apps/web/src/shared/api/browser-generated/index.ts'
        )
        $hashes = @{}
        foreach ($path in $generatedPaths) { $hashes[$path] = (Get-FileHash -LiteralPath $path).Hash }
        foreach ($script in @('api:generate', 'api:generate:browser')) {
            npm --prefix apps/web run $script
            if ($LASTEXITCODE -ne 0) { throw "API generation failed: $script" }
        }
        foreach ($path in $generatedPaths) {
            if ((Get-FileHash -LiteralPath $path).Hash -ne $hashes[$path]) { throw "Generated contract drift: $path" }
        }
        if (Test-Path 'apps\web\node_modules\.bin\oxlint.cmd') {
            Write-Output '[verify] running web lint...'
            npm --prefix apps/web run lint
            if ($LASTEXITCODE -ne 0) { throw 'web lint failed.' }
        }
        else {
            Write-Output '[verify] oxlint not installed; skipping web lint (run npm --prefix apps/web install).'
        }
        Write-Output '[verify] running web build...'
        npm --prefix apps/web run build
        if ($LASTEXITCODE -ne 0) { throw 'web build failed.' }
        Write-Output '[verify] web build OK.'
    }
    else {
        Write-Output '[verify] apps/web/node_modules missing; skipping web checks (run npm --prefix apps/web install).'
    }
}
else {
    Write-Output '[verify] npm not found; skipping web checks.'
}

Write-Output '[verify] all checks passed.'
