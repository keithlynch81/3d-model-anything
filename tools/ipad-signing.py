"""Install CI-only signing assets and validate an explicit ad hoc profile."""
import base64
import datetime
import hashlib
import os
from pathlib import Path
import plistlib
import re
import secrets
import shutil
import subprocess


def run(*args):
    return subprocess.check_output(args, stderr=subprocess.PIPE)


def main():
    temp = Path(os.environ['RUNNER_TEMP'])
    bundle = os.environ['APP_BUNDLE_ID']
    team = os.environ['APPLE_TEAM_ID']
    if not re.fullmatch(r'[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+', bundle):
        raise ValueError('APP_BUNDLE_ID must be an explicit reverse-domain identifier')
    if not re.fullmatch(r'[A-Z0-9]{10}', team):
        raise ValueError('APPLE_TEAM_ID must contain 10 uppercase letters/digits')
    p12 = temp / 'signing.p12'
    profile_file = temp / 'profile.mobileprovision'
    p12.write_bytes(base64.b64decode(os.environ['CERTIFICATE'], validate=True))
    profile_file.write_bytes(base64.b64decode(os.environ['PROFILE'], validate=True))
    profile = plistlib.loads(run('security', 'cms', '-D', '-i', str(profile_file)))
    entitlements = profile['Entitlements']
    if profile['TeamIdentifier'] != [team]:
        raise ValueError('Provisioning profile does not match APPLE_TEAM_ID')
    prefix = profile['ApplicationIdentifierPrefix'][0]
    if entitlements['application-identifier'] != f'{prefix}.{bundle}':
        raise ValueError('Provisioning profile does not match APP_BUNDLE_ID')
    if not profile.get('ProvisionedDevices') or entitlements.get('get-task-allow') or profile.get('ProvisionsAllDevices'):
        raise ValueError('Select an Ad Hoc profile, not Development, Enterprise or App Store')
    if profile['ExpirationDate'] <= datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None):
        raise ValueError('Provisioning profile has expired')
    uuid = profile['UUID']
    if not re.fullmatch(r'[A-Fa-f0-9-]{36}', uuid):
        raise ValueError('Invalid profile UUID')
    keychain = str(temp / 'ipad-signing.keychain-db')
    password = secrets.token_urlsafe(32)
    run('security', 'create-keychain', '-p', password, keychain)
    run('security', 'set-keychain-settings', '-lut', '21600', keychain)
    run('security', 'unlock-keychain', '-p', password, keychain)
    run('security', 'import', str(p12), '-P', os.environ['CERTIFICATE_PASSWORD'], '-A', '-t', 'cert', '-f', 'pkcs12', '-k', keychain)
    run('security', 'set-key-partition-list', '-S', 'apple-tool:,apple:', '-k', password, keychain)
    run('security', 'list-keychains', '-d', 'user', '-s', keychain, str(Path.home() / 'Library/Keychains/login.keychain-db'))
    identities = run('security', 'find-identity', '-v', '-p', 'codesigning', keychain).decode()
    candidates = [hashlib.sha1(cert).hexdigest().upper() for cert in profile['DeveloperCertificates']]
    identity = next((sha for sha in candidates if sha in identities), None)
    if not identity:
        raise ValueError('P12 has no valid signing identity matching the profile; check certificate and private key')
    for directory in ('Library/MobileDevice/Provisioning Profiles', 'Library/Developer/Xcode/UserData/Provisioning Profiles'):
        destination = Path.home() / directory
        destination.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(profile_file, destination / f'{uuid}.mobileprovision')
    options = dict(method='release-testing', teamID=team, signingStyle='manual',
                   signingCertificate=identity, provisioningProfiles={bundle: uuid},
                   stripSwiftSymbols=True, manageAppVersionAndBuildNumber=False)
    (temp / 'ExportOptions.plist').write_bytes(plistlib.dumps(options))
    with open(os.environ['GITHUB_ENV'], 'a') as output:
        output.write(f'PROFILE_UUID={uuid}\nSIGNING_IDENTITY={identity}\n')
    print('Validated ad hoc profile, matching signing identity, and export configuration.')


if __name__ == '__main__':
    try:
        main()
    except subprocess.CalledProcessError:
        # Do not print command arguments: security commands contain passwords.
        raise SystemExit('Apple signing command failed. Check the P12 password, certificate and profile.')
