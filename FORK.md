# Personal Android builds

This fork installs as **Immich-E**, with Android application ID
`app.alextran.immich.er404r`. It can coexist with the official app. Each app has
its own login, database, permissions and backup settings.

Use `main` for the customized app and releases. Automatic updates merge only
official stable release tags, never upstream development-branch updates.
Official stable releases can be merged automatically using the workflow below.
Keep the server compatible with the updated mobile app. Keep this guide and
`AGENTS.md` current.

## One-time GitHub setup

1. Push the fork changes to `main`, set the fork's default branch to
   `main` under repository settings, and enable GitHub Actions in the fork.
   This makes scheduled and manual workflows available on the release branch.
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

5. Run **Fork Android** manually against `main`, or push another commit to
   that branch. No personal access token or Play Store account is needed by the
   workflow; its release job uses GitHub's automatic token with `contents: write`.

## Automatic upstream updates

**Sync Official Releases** checks `immich-app/immich` every 30 minutes and can
also be run manually on `main`. Scheduled runs require `main` to be the
fork's default branch and this workflow to have been merged and pushed there.
GitHub can delay scheduled runs or disable schedules after prolonged repository
inactivity; check the Actions tab if updates stop arriving.

It selects official `vMAJOR.MINOR.PATCH` releases, excluding drafts and
prereleases. It merges the release tag into `main`, preserving custom changes,
and pushes without force. Diverging history is handled by a normal merge.
Conflicts, branch protection failures or concurrent incompatible pushes stop
the sync without updating the remote branch. Resolve the failure manually
before rerunning it. Checks without a new release do not push or build an APK.

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
Versions older than the mobile version on main are skipped to avoid
downgrades. This checkout began at `3.4.0-rc.0`, so it waits for stable `3.4.0`
or later rather than merging the older `3.3.x` line.

Each successful sync starts the existing APK pipeline. The next sync waits for
that pipeline to finish successfully on the current `main` commit before
merging another release, so queued updates cannot replace one another's builds.
Failed tests or builds
leave the synced source branch in place and do not publish a release. After
fixing a build failure, push the fix to `main` to retry. A successful APK
release appears in Obtainium as usual; server upgrades remain your responsibility.

Keep inherited upstream workflows disabled. Review new workflow files introduced
by future upstream releases, since those may require disabling as well.

Validate changes to this automation with:

```sh
mise //.github:test:release-sync
mise //.github:lint:fork-workflow
```

## Checks and releases

Pushes to `main` and pull requests targeting it run the existing Flutter
tests, Dart analyzer, Dart formatting check and Rust native tests. Code generation
and builds use the repository's pinned tools through mise. The paid DCM analyzer
is not part of this fork workflow. These checks cover the mobile app and native
core; they do not replace server/web tests or testing on a real phone.

After checks pass on `main`, CI builds one ARM64-only release APK for the
Nothing Phone (3a) Pro, signs it with your key and publishes `immich-er404r.apk`
to a GitHub release. It verifies that the APK contains only `arm64-v8a` native
libraries before uploading. Pull requests
run checks without signing secrets or publishing releases. Other branches can
run the checks through the manual workflow trigger.

The Nothing Phone (3a) Pro uses the Snapdragon 7s Gen 3, a 64-bit ARM processor.
Building only for `arm64-v8a` removes the unused 32-bit ARM and x86-64 code from
the old universal APK. This reduces the download size without removing features.
Other ARM64 phones can use the same APK; 32-bit devices and x86-64 emulators need
a separate build. The normal local debug workflow still supports emulators.

The package ID, signing key and release asset filename are unchanged. Existing
Obtainium installations can update directly from the universal APK to the ARM64
APK without uninstalling the app. The exact size is reported by each CI build.

The release tag matches the APK's version name, for example
`3.4.0-rc.0-fork.12.1`. The upstream prefix is preserved for the app's server
compatibility checks. The Android version code is `run_number * 100 + run_attempt`
and increases with successive workflow runs. The ARM64 build disables Flutter's
per-ABI version-code offset to preserve this counter when moving from universal
APKs. Reruns have distinct versions; attempts of 100 or greater are rejected.
Do not rerun an old workflow after a
newer version has been published, rename/delete this workflow to reset its run
counter, or change the application ID or signing key after installation.

An active build on `main` finishes when another commit arrives. GitHub may
replace older pending runs with the newest pending run. Failed checks/builds do
not publish a release. Missing signing secrets fail the build explicitly.

Require the **check-and-build** status check in a GitHub ruleset for `main`
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
Future successful releases on `main` appear as updates for the fork.

Log in to your existing Immich server separately in the fork and configure photo
permissions and backup settings. Test login, browsing, upload, background backup
and widgets on your phone before relying on it. Shared OAuth callback and Immich
link schemes may show an Android app chooser when both apps are installed.
Passkeys and verified links may require server/domain configuration for the new
package and signing certificate; password login is useful for the first test.

## Migration from personal to main

The local main branch contains the existing fork history and updated workflows.
This migration preserves existing development commits; merging a stable tag
does not remove code already present in the fork.

After committing the migration, publish and change the default branch:

```sh
git push origin main
gh repo edit ER404R/immich --default-branch main
```

Wait for Fork Android on main to succeed before removing the old remote branch:

```sh
git push origin --delete personal
```

The existing signing secrets, deploy key, workflow filename/version counter and
Obtainium configuration remain valid. No new credentials are required.
