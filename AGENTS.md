# AGENTS.md

Immich monorepo: `server/` (NestJS API + job workers), `web/` (SvelteKit SPA), `mobile/` (Flutter), `native/` (Rust core for mobile), `machine-learning/` (FastAPI + ONNX), `e2e/` (API + Playwright tests), `packages/` (`@immich/sdk`, `@immich/cli`, plugin SDK/core, release scripts), `open-api/`, `i18n/`, `docs/`. Before changing code in `server/`, `web/`, `mobile/`, `native/`, `machine-learning/` or `e2e/`, read that folder's `AGENTS.md`.

## Rules

- No PRs of LLM-generated code; the human contributor must understand and be able to explain every change (see `CONTRIBUTING.md`).
- Do not generate PR titles, descriptions, issue text, review comments or discussion answers. Translating human-written text is fine.
- Never work on issues labelled `good first issue`; those PRs are closed automatically.
- Run every build, lint, test and codegen task through mise: `mise //<dir>:<task>`, root tasks as `mise //:<task>`. `mise tasks ls --all` lists them.
- Never hand-edit generated files: `open-api/immich-openapi-specs.json`, `packages/sdk/src/fetch-client.ts`, `mobile/generated/openapi/`, `server/src/queries/*.sql`, and Dart codegen (`*.g.dart`, `*.drift.dart`, `*.freezed.dart`, `router.gr.dart`, `lib/generated/`, `lib/platform/*.g.dart`).
- Only edit `i18n/en.json`; the other locale files come from Weblate.
- Do not add code comments. Make the code self-explanatory through naming and structure instead.
- PR titles are conventional commits. Keep a PR to one focused change.
- Sharing/asset ownership and external libraries are feature-frozen: bug fixes only.
- Renaming or removing a docs page requires an entry in `docs/static/_redirects`.

## Personal Android fork

- This fork targets `ER404R/immich`; `personal` is the Android release branch; keep `main` available for upstream tracking. Setup and update instructions live in `FORK.md`.
- `.github/workflows/fork-android.yml` runs the existing mobile tests, Dart analysis, formatting and native tests on pushes to and pull requests targeting `personal`; only successful builds on `personal` publish APK releases for Obtainium.
- Preserve Android application ID `app.alextran.immich.er404r` and launcher name `Immich-E`. Keep the Kotlin namespace `app.alextran.immich` so existing platform classes and bindings continue to resolve.
- Release APKs must use the permanent signing key in repository secrets. Never publish debug-signed releases, commit signing material or reset the fork workflow's version counter.
- Local signing backups belong in `.fork-private/`, which is git-ignored. Keep that directory private and back it up outside this checkout; never print its credentials.
- Keep the upstream version prefix for server compatibility; CI adds the fork version suffix and an increasing Android version code. Do not hand-edit `mobile/pubspec.yaml` for each fork build.
- Keep fork setup instructions and these conventions current as the release process changes. Upstream contribution restrictions above still apply to contributions sent upstream.

## Skills

- **Regenerate the API clients**: after any change to a server controller or DTO, run `mise //:open-api`. It rebuilds the server, rewrites the OpenAPI spec, regenerates the TypeScript SDK and the Dart client. The CI job "OpenAPI Clients" fails if this is stale. If a response field became required, the Dart client also needs a backward-compatibility patch in `open-api/patch`, checked by `flutter test test/openapi_patches_coverage.dart` (job "check-mobile-patches").
- **Add a translation string**: add the key to `i18n/en.json`, then run `mise //:i18n:format-fix` so the file stays key-sorted (CI job "Test i18n" fails otherwise). For the mobile app also run `mise //mobile:translation`. Web keys are typed against `en.json`, so the key must exist before `tsc` passes.
