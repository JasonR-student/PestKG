$ErrorActionPreference = 'Stop'

$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location $root

$contractTemp = Join-Path ([System.IO.Path]::GetTempPath()) ("pestkg-contract-" + [guid]::NewGuid())
New-Item -ItemType Directory -Path $contractTemp | Out-Null
Copy-Item packages\api-contract\openapi-v1.1.json $contractTemp
Copy-Item apps\web\src\shared\api\generated\types.gen.ts $contractTemp
Copy-Item apps\web\src\shared\api\generated\index.ts $contractTemp

try {
    .\.venv\Scripts\python packages\api-contract\export_openapi.py
    npm --prefix apps/web run api:generate
    if ((Get-FileHash packages\api-contract\openapi-v1.1.json).Hash -ne
        (Get-FileHash (Join-Path $contractTemp 'openapi-v1.1.json')).Hash) {
        throw 'OpenAPI snapshot drift detected. Regenerate and review the contract.'
    }
    if ((Get-FileHash apps\web\src\shared\api\generated\types.gen.ts).Hash -ne
        (Get-FileHash (Join-Path $contractTemp 'types.gen.ts')).Hash -or
        (Get-FileHash apps\web\src\shared\api\generated\index.ts).Hash -ne
        (Get-FileHash (Join-Path $contractTemp 'index.ts')).Hash) {
        throw 'Generated TypeScript API types drift detected.'
    }
}
finally {
    Remove-Item -LiteralPath $contractTemp -Recurse -Force
}

.\.venv\Scripts\python -m pytest apps\api\tests tools\release-pipeline\tests
.\.venv\Scripts\python -m unittest discover -s research\figures\tests -v
.\.venv\Scripts\python -m compileall apps\api\src tools\release-pipeline research\figures
npm --prefix apps/web run lint
npm --prefix apps/web run test
npm --prefix apps/web run build
docker compose config --quiet
docker compose -f docker-compose.yml -f infra/docker-compose.prod.yml config --quiet
