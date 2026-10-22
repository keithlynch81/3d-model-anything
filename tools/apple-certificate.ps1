param(
    [ValidateSet('Request', 'Package')][string]$Step = 'Request',
    [string]$CertificatePath,
    [string]$OpenSSL = 'C:\Program Files\Git\usr\bin\openssl.exe'
)
$ErrorActionPreference = 'Stop'
if (-not (Test-Path -LiteralPath $OpenSSL)) { throw 'OpenSSL was not found. Install Git for Windows or supply -OpenSSL with its path.' }
$signingDirectory = Join-Path (Split-Path $PSScriptRoot -Parent) 'signing'
New-Item -ItemType Directory -Force -Path $signingDirectory | Out-Null
$keyPath = Join-Path $signingDirectory 'distribution.key'
$requestPath = Join-Path $signingDirectory 'distribution.certSigningRequest'
if ($Step -eq 'Request') {
    if ((Test-Path $keyPath) -or (Test-Path $requestPath)) { throw 'A key or request already exists. Keep it; do not overwrite the key associated with your certificate.' }
    Write-Host 'Choose a password to encrypt your private key. OpenSSL will then ask for certificate request details.'
    & $OpenSSL genrsa -aes256 -out $keyPath 2048
    if ($LASTEXITCODE -ne 0) { throw 'Key generation failed.' }
    & $OpenSSL req -new -sha256 -key $keyPath -out $requestPath
    if ($LASTEXITCODE -ne 0) { throw 'Certificate request failed.' }
    Write-Host "Upload this request to Apple: $requestPath"
} else {
    if (-not $CertificatePath) { throw 'Supply -CertificatePath with the downloaded Apple .cer file.' }
    $pemPath = Join-Path $signingDirectory 'distribution.pem'
    $p12Path = Join-Path $signingDirectory 'distribution.p12'
    if (Test-Path $p12Path) { throw 'The P12 already exists. Keep it or move it before packaging another certificate.' }
    & $OpenSSL x509 -inform DER -in $CertificatePath -out $pemPath
    if ($LASTEXITCODE -ne 0) { throw 'Certificate conversion failed.' }
    Write-Host 'Enter the private-key password, then choose a nonempty export password for the P12.'
    & $OpenSSL pkcs12 -export -inkey $keyPath -in $pemPath -out $p12Path -name 'Room Scanner Distribution' -keypbe PBE-SHA1-3DES -certpbe PBE-SHA1-3DES -macalg sha1
    if ($LASTEXITCODE -ne 0) { throw 'Packaging failed. Check that the certificate matches this private key.' }
    Write-Host "Created: $p12Path"
    Write-Host 'The export password is the APPLE_CERTIFICATE_PASSWORD GitHub secret.'
}
