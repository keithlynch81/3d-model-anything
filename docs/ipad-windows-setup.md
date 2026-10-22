# Build and install from Windows

This workflow builds the native HouseCapture app on GitHub's macOS runner and signs a Release IPA for your registered iPad. It needs an active paid Apple Developer membership. No Expo, Mac purchase, App Store listing or Apple account password in GitHub is required. Device scanning remains unverified until the first physical-device test.

## 1. Your GitHub fork

Fork https://github.com/wesbos/3d-model-anything into your own account, keeping the default main branch. Put the added workflow, helper scripts and this guide into that fork. Standard GitHub-hosted runners are free for public repositories; private repositories use an allowance. Retained artifacts also have storage allowances; this workflow keeps only the IPA for three days. Scan data stays off GitHub.

## 2. Generate the certificate request on Windows

Open PowerShell in the project folder and run:

```powershell
.\tools\apple-certificate.ps1 -Step Request
```

The helper uses the OpenSSL shipped with Git for Windows. It creates an encrypted private key in the ignored `signing` folder and prompts for a password. Keep that password and key. When asked for certificate request details, use your country, name and Apple account email; optional fields can be left blank. Leave the challenge password blank.

Only upload `signing/distribution.certSigningRequest` to Apple. Do not upload the private key or paste credentials into chat. If you already have a suitable Apple Distribution P12 and its password (for example from a previous project), you may reuse those and skip creating a certificate. A downloaded .cer alone does not contain its private key.

## 3. Apple Developer account

Open https://developer.apple.com/account/resources/ and use Certificates, Identifiers & Profiles.

1. **Certificates → + → Apple Distribution.** Upload the CSR from step 2 and download the `.cer`. Do not choose Developer ID, Apple Development or enterprise distribution. If your team is at its certificate limit, reuse an existing exportable identity rather than revoking a certificate another app relies on.
2. Package the downloaded certificate on Windows:

   ```powershell
   .\tools\apple-certificate.ps1 -Step Package -CertificatePath "$env:USERPROFILE\Downloads\distribution.cer"
   ```

   Use the actual downloaded filename. Enter the private-key password, then choose a nonempty P12 export password. This produces `signing/distribution.p12`.
3. **Identifiers → + → App IDs → App.** Description: `Room Scanner`. Choose an explicit, unique Bundle ID such as `com.YOURUNIQUEHANDLE.roomscanner`. Use your own identifier, not `com.wesbos.housecapture`. This project does not require special capabilities to be enabled for camera, ARKit or RoomPlan access.
4. **Devices → +.** Register your iPad using its UDID (not its serial number or model A2377). See the USB steps below to retrieve it.
5. **Profiles → + → Distribution → Ad Hoc.** Select your new App ID, the exact distribution certificate used for the P12, and your iPad. Name it `Room Scanner iPad Ad Hoc`, generate it and download the `.mobileprovision` into `signing`.
6. Find your 10-character **Team ID** in your account's Membership details.

## 4. USB connection and UDID

Install Apple's **Apple Devices** app from the Microsoft Store for Windows device support. Connect the unlocked iPad by USB, accept **Trust This Computer** on the iPad, and verify it appears in Apple Devices. Close Apple Devices before installing the IPA if it interferes with the connection.

The free, open-source PyMobileDevice3 tool provides device discovery and IPA installation. Install it into a dedicated environment:

```powershell
python -m venv .venv-ipad
.\.venv-ipad\Scripts\python.exe -m pip install --upgrade pymobiledevice3
.\.venv-ipad\Scripts\python.exe -m pymobiledevice3 usbmux list
```

Use your connected iPad's identifier from the list as the UDID for Apple registration. Keep only the intended iPad connected. If Windows cannot detect it, resolve the Apple USB driver/pairing issue before building. We still need to test this tool against your device and iPadOS version.

## 5. GitHub signing environment

In your fork, open **Settings → Environments → New environment**, name it **ipad-signing**, and restrict deployment branches to **main**. Enable a required reviewer if your plan offers it and you want an extra manual gate.

Add these **environment variables**:

| Name | Value |
| --- | --- |
| `APP_BUNDLE_ID` | The explicit identifier registered in Apple |
| `APPLE_TEAM_ID` | Your 10-character Team ID |

Add these **environment secrets**:

| Name | Value |
| --- | --- |
| `APPLE_CERTIFICATE_P12_BASE64` | Base64 of your P12 |
| `APPLE_CERTIFICATE_PASSWORD` | The P12 export password |
| `APPLE_PROFILE_BASE64` | Base64 of your downloaded ad hoc profile |

Copy the encoded values to the clipboard without printing them:

```powershell
[Convert]::ToBase64String([IO.File]::ReadAllBytes((Resolve-Path '.\signing\distribution.p12').Path)) | Set-Clipboard
```

Paste into `APPLE_CERTIFICATE_P12_BASE64`, then repeat for the profile using its actual filename:

```powershell
[Convert]::ToBase64String([IO.File]::ReadAllBytes((Resolve-Path '.\signing\Room_Scanner_iPad_Ad_Hoc.mobileprovision').Path)) | Set-Clipboard
```

Paste into `APPLE_PROFILE_BASE64`. Enter the P12 export password directly into its secret field. Clear the clipboard afterwards with `Set-Clipboard -Value ''`. The private key, certificate package and profile must never be committed. The workflow imports them into a temporary keychain and removes them after the job.

## 6. Build

Open your fork's **Actions** tab and enable workflows if GitHub asks. Select **Build signed iPad app → Run workflow → main**. This workflow runs only when manually requested; it does not sign pull requests. After success, download the `ipad-app-N` artifact at the bottom of the run and extract the IPA from its ZIP.

The workflow checks the profile's team, bundle ID, expiry, ad hoc type and matching signing identity before archiving. It cannot check whether you selected the correct physical iPad; confirm that in Apple's profile page.

If the existing **Deploy viewer** workflow fails because Pages is not configured in your fork, that is separate from the iPad build. You can disable that viewer workflow in Actions until you want to publish a viewer.

## 7. Install and test

With the trusted iPad connected and unlocked, run (replace the path with the extracted IPA):

```powershell
.\.venv-ipad\Scripts\python.exe -m pymobiledevice3 apps install "C:\path\to\HouseCapture.ipa"
```

If requested, enable **Settings → Privacy & Security → Developer Mode**, restart, and confirm. Launch **3D Model Anything**, allow camera access, and scan one small room. Save it, reopen its 3D preview, and export a ZIP to Files. That is the first real end-to-end acceptance check.

An IPA cannot be installed by simply opening it in Files or tapping a GitHub artifact link. The Windows USB installation tool transfers the signed app. Ad hoc profiles expire; rebuild with a renewed profile/certificate before expiry. The free-account seven-day limit does not apply to this paid-team ad hoc build. Keep the same bundle ID for upgrades, and export scans before changing signing or reinstalling.

## References

- [GitHub signing on macOS runners](https://docs.github.com/en/actions/how-tos/deploy/deploy-to-third-party-platforms/sign-xcode-applications)
- [Apple certificate types](https://developer.apple.com/help/account/create-certificates/certificates-overview)
- [Apple ad hoc profile creation](https://developer.apple.com/help/account/provisioning-profiles/create-an-ad-hoc-provisioning-profile/)
- [PyMobileDevice3 installation and commands](https://github.com/doronz88/pymobiledevice3)
- [GitHub Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions)
