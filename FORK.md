# Personal Android builds

This fork installs as **Immich-E**, with Android application ID
`app.alextran.immich.er404r`. It can coexist with the official app. Each app has
its own login, database, permissions and backup settings.

Use `personal` for the customized app and releases. Keep `main` available to track
upstream, and start any upstream contribution on a separate branch from `main`.
Official stable releases can be merged automatically using the workflow below.
Keep the server compatible with the updated mobile app. Keep this guide and
`AGENTS.md` current.

## One-time GitHub setup

1. Push the fork changes to `personal`, set the fork's default branch to
   `personal` under repository settings, and enable GitHub Actions in the fork.
   This makes the manual workflow trigger available while `main` remains your
   upstream tracking branch.
2. In the Actions tab, disable inherited upstream workflows for this personal
   fork. Leave **Fork Android** and **Sync Official Releases** enabled. Upstream workflows depend on Immich's
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

## Automatic upstream updates

**Sync Official Releases** checks `immich-app/immich` every 30 minutes and can
also be run manually on `personal`. Scheduled runs require `personal` to be the
fork's default branch and this workflow to have been merged and pushed there.
GitHub can delay scheduled runs or disable schedules after prolonged repository
inactivity; check the Actions tab if updates stop arriving.

It selects official `vMAJOR.MINOR.PATCH` releases, excluding drafts and
prereleases. It fast-forwards `main` to the release commit and merges that commit
into `personal`, preserving personal changes. Both branches are pushed atomically
without force. Conflicts, divergent history on `main`, branch protection failures
or concurrent incompatible pushes stop the sync without updating either branch.
Resolve the failure manually before rerunning it.

The sync uses the dedicated write-enabled deploy key **Immich-E upstream release
sync**, restricted to `ER404R/immich`. Its private key is the Actions secret
`UPSTREAM_SYNC_SSH_KEY`. This permits upstream workflow-file updates and triggers
the normal Fork Android push workflow, which tests, builds and signs the new APK.
GitHub's automatic token suppresses push-triggered workflows, so it is not used
for the sync push. The deploy key is unrelated to Android signing and your
personal password-protected SSH key.

Automated setup keeps the local deploy-key backup in `.fork-private/`.
For manual setup, generate a dedicated key, add its public half under repository
**Settings → Deploy keys** with write access, and upload its private half as
`UPSTREAM_SYNC_SSH_KEY`. Never add your personal SSH private key to Actions.

Only one outstanding release is merged per run, oldest first, so missed releases
can be processed in order. Already-merged releases produce no push or APK.
Versions older than the mobile version on either branch are skipped to avoid
downgrades. This checkout began at `3.4.0-rc.0`, so it waits for stable `3.4.0`
or later rather than merging the older `3.3.x` line.

Each successful sync starts the existing APK pipeline. The next sync waits for
that pipeline to finish successfully on the current `personal` commit before
merging another release, so queued updates cannot replace one another's builds.
Failed tests or builds
leave the synced source branches in place and do not publish a release. After
fixing a build failure, push the fix to `personal` to retry. A successful APK
release appears in Obtainium as usual; server upgrades remain your responsibility.

Keep inherited upstream workflows disabled. Review new workflow files introduced
by future upstream releases, since those may require disabling as well.

Validate changes to this automation with:

```sh
mise //.github:test:release-sync
mise //.github:lint:fork-workflow
```

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
