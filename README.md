# podfind-ios
PodFind - iOS app for tracking AirPods using Apple APIs (Find My, CoreLocation, Nearby Interaction)

## TestFlight deployment

The [TestFlight workflow](.github/workflows/testflight-deploy.yml) archives, signs,
exports and uploads the app on pushes to `main` or when run manually from
**Actions → Deploy to TestFlight → Run workflow**. The first upload must finish
processing in App Store Connect before it appears in TestFlight; add testers there.
This repository currently has **no Xcode project**, so the workflow cannot
successfully deploy until the project and the configuration below are added.
The deployment job is skipped until the `XCODE_PROJECT` repository variable is
set; after it is set, any other missing configuration is reported as an error.

### Prepare the app and Apple credentials

1. Enroll in the [Apple Developer Program](https://developer.apple.com/programs/)
   and create an App Store Connect app record with the app's bundle ID. Accept
   any outstanding agreements in App Store Connect.
2. Commit an iOS `.xcodeproj` and a shared scheme with a Release archive action.
   The workflow supports one app target and one App Store distribution profile;
   apps with extensions or a workspace need corresponding workflow changes.
   Configure the app's bundle ID and team to match the Apple records. Set
   `CFBundleVersion` to `$(CURRENT_PROJECT_VERSION)` (or use Xcode's generated
   Info.plist) so the workflow can assign a build number.
3. In Certificates, Identifiers & Profiles, register the bundle ID and create
   an **Apple Distribution** certificate. Export the certificate **with its
   private key** from Keychain Access as a password-protected `.p12`. Create
   and download an **App Store Connect** provisioning profile for that app ID
   and certificate. Renew and replace both secrets before they expire.
4. In App Store Connect → Users and Access → Integrations → App Store Connect
   API, create a team API key with access to upload builds (for example, the
   Developer role). Record its Key ID and Issuer ID and download its `.p8`
   private key; Apple allows the key to be downloaded only once.

### Configure GitHub Actions

In the repository's **Settings → Secrets and variables → Actions**, add these
repository variables (not secrets):

| Variable | Value |
| --- | --- |
| `XCODE_PROJECT` | Repository-relative path to the `.xcodeproj`, e.g. `PodFind.xcodeproj` |
| `XCODE_SCHEME` | Name of the shared scheme to archive |
| `APP_BUNDLE_ID` | App bundle ID, matching the App Store Connect record and profile |
| `APPLE_TEAM_ID` | Apple Developer team ID |
| `BUILD_NUMBER_OFFSET` | Optional non-negative integer, at most six digits; defaults to `0` |

Add these repository **secrets**:

| Secret | Value |
| --- | --- |
| `APPLE_DISTRIBUTION_CERTIFICATE_BASE64` | Base64-encoded `.p12` including the private key |
| `APPLE_DISTRIBUTION_CERTIFICATE_PASSWORD` | Password used to export the `.p12` |
| `APPLE_PROVISIONING_PROFILE_BASE64` | Base64-encoded App Store Connect `.mobileprovision` |
| `APP_STORE_CONNECT_API_KEY_BASE64` | Base64-encoded downloaded `.p8` key |
| `APP_STORE_CONNECT_KEY_ID` | App Store Connect API Key ID |
| `APP_STORE_CONNECT_ISSUER_ID` | App Store Connect API Issuer ID |

On a Mac, encode each file with `base64 -i /path/to/file | pbcopy` and paste
the clipboard contents into the matching secret. Do not commit the files,
their encoded contents, or passwords. Restrict repository access and rotate
credentials if exposed. GitHub secrets must be configured by a repository
administrator; the workflow cannot create them.

The build number is the workflow run number plus `BUILD_NUMBER_OFFSET`. Set the
offset high enough that the first generated number exceeds any existing build
number for the same marketing version in App Store Connect; do not lower it
later. A GitHub rerun reuses the same run number, so start a new workflow run
instead if that build number was already uploaded. Check the run's build logs
for signing or upload errors. A successful upload still requires Apple's
processing and, for external testers, beta review.
If the default branch is not `main`, adjust the workflow's push trigger.
