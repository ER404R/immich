# Personal Android builds

This fork installs as **Immich-E**, with Android application ID
`app.alextran.immich.er404r`. It can coexist with the official app. Each app has
its own login, database, permissions and backup settings.

Use `personal` for the customized app and releases. Keep `main` available to track
upstream, and start any upstream contribution on a separate branch from `main`.
Merge upstream updates into `personal` deliberately, especially when the mobile
app requires a newer server version. Keep this guide and `AGENTS.md` current.

## One-time GitHub setup

1. Push the fork changes to `personal`, set the fork's default branch to
   `personal` under repository settings, and enable GitHub Actions in the fork.
   This makes the manual workflow trigger available while `main` remains your
   upstream tracking branch.
2. In the Actions tab, disable inherited upstream workflows for this personal
   fork. Leave **Fork Android** enabled. Upstream workflows depend on Immich's
   private GitHub App credentials, custom runners and publishing infrastructure.
   Their files remain available for reference and upstream merges.
3. Generate a dedicated permanent signing key on your own computer with a JDK:

   ```sh
   keytool -genkeypair -v -keystore immich-er404r.jks -alias immich-er404r \
     -keyalg RSA -keysize 4096 -validity 10000
   ```

   Keep the key and passwords backed up privately. Android updates must use the
   same signing key. Do not commit it or use a temporary/debug key.
   Automated setup stores local signing material in the git-ignored
   `.fork-private/` directory with access restricted to your user. Back up that
   directory securely outside this checkout; GitHub secrets cannot be downloaded
   later to recover the key.

4. Add these repository secrets under **Settings → Secrets and variables →
   Actions**:

   | Secret | Value |
   | --- | --- |
   | `KEY_JKS` | Base64 encoding of the keystore file |
   | `ALIAS` | `immich-er404r` |
   | `ANDROID_STORE_PASSWORD` | The keystore password |
   | `ANDROID_KEY_PASSWORD` | The key password (often the same as the store password) |

   With GitHub CLI authenticated to your account, upload the keystore without
   printing it to the terminal:

   ```sh
   base64 < immich-er404r.jks | gh secret set KEY_JKS --repo ER404R/immich
   gh secret set ALIAS --body immich-er404r --repo ER404R/immich
   gh secret set ANDROID_STORE_PASSWORD --repo ER404R/immich
   gh secret set ANDROID_KEY_PASSWORD --repo ER404R/immich
   ```

5. Run **Fork Android** manually against `personal`, or push another commit to
   that branch. No personal access token or Play Store account is needed by the
   workflow; its release job uses GitHub's automatic token with `contents: write`.

## Checks and releases

Pushes to `personal` and pull requests targeting it run the existing Flutter
tests, Dart analyzer, Dart formatting check and Rust native tests. Code generation
and builds use the repository's pinned tools through mise. The paid DCM analyzer
is not part of this fork workflow. These checks cover the mobile app and native
core; they do not replace server/web tests or testing on a real phone.

After checks pass on `personal`, CI builds one universal release APK, signs it
with your key and publishes `immich-er404r.apk` to a GitHub release. Pull requests
run checks without signing secrets or publishing releases. Other branches can
run the checks through the manual workflow trigger.

The release tag matches the APK's version name, for example
`3.4.0-rc.0-fork.12.1`. The upstream prefix is preserved for the app's server
compatibility checks. The Android version code is `run_number * 100 + run_attempt`
and increases with successive workflow runs. Reruns have distinct versions;
attempts of 100 or greater are rejected. Do not rerun an old workflow after a
newer version has been published, rename/delete this workflow to reset its run
counter, or change the application ID or signing key after installation.

An active build on `personal` finishes when another commit arrives. GitHub may
replace older pending runs with the newest pending run. Failed checks/builds do
not publish a release. Missing signing secrets fail the build explicitly.

Require the **check-and-build** status check in a GitHub ruleset for `personal`
if you want failures to block merges as well as releases. Direct pushes still
run checks, but GitHub cannot undo a pushed commit when tests fail.

## Obtainium

After the first release is published, add `https://github.com/ER404R/immich` as a
GitHub source in Obtainium. Set the release-title filter to `-fork\.` so imported
upstream releases are excluded. If using an APK filename filter, use
`^immich-er404r\.apk$`. Leave prerelease inclusion off; the workflow publishes
ordinary releases even when the upstream version contains `rc`.

The release tag and installed version name match, so keep normal version-name
tracking enabled. Allow Android to install apps from Obtainium when prompted.
Future successful releases on `personal` appear as updates for the fork.

Log in to your existing Immich server separately in the fork and configure photo
permissions and backup settings. Test login, browsing, upload, background backup
and widgets on your phone before relying on it. Shared OAuth callback and Immich
link schemes may show an Android app chooser when both apps are installed.
Passkeys and verified links may require server/domain configuration for the new
package and signing certificate; password login is useful for the first test.
