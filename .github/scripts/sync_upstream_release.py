import json
import os
import re
import subprocess
from pathlib import Path


UPSTREAM_REPOSITORY = "immich-app/immich"
UPSTREAM_URL = f"https://github.com/{UPSTREAM_REPOSITORY}.git"


def git(*args, check=True):
    return subprocess.run(["git", *args], check=check, text=True, capture_output=True)


def stable_releases(releases):
    versions = {}
    for release in releases:
        match = re.fullmatch(r"v(\d+)\.(\d+)\.(\d+)", release["tag_name"])
        if match and not release["draft"] and not release["prerelease"]:
            versions[tuple(map(int, match.groups()))] = release["tag_name"]
    return sorted(versions.items())


def branch_version(ref):
    pubspec = git("show", f"{ref}:mobile/pubspec.yaml").stdout
    match = re.search(r"^version:\s*(\d+)\.(\d+)\.(\d+)", pubspec, re.MULTILINE)
    if not match:
        raise ValueError(f"Cannot determine mobile version at {ref}")
    return tuple(map(int, match.groups()))


def contains(ref, commit):
    result = git("merge-base", "--is-ancestor", commit, ref, check=False)
    if result.returncode not in (0, 1):
        raise subprocess.CalledProcessError(result.returncode, result.args, stderr=result.stderr)
    return result.returncode == 0


def build_passed(runs, head):
    return bool(runs) and (
        runs[0]["head_sha"] == head
        and runs[0]["status"] == "completed"
        and runs[0]["conclusion"] == "success"
    )


def synchronize(releases, upstream_url=UPSTREAM_URL, build_runs=None):
    git(
        "fetch", "--no-tags", "origin",
        "+refs/heads/main:refs/remotes/origin/main",
        "+refs/heads/personal:refs/remotes/origin/personal",
    )
    personal_head = git("rev-parse", "origin/personal").stdout.strip()
    if build_runs is not None and not build_passed(build_runs, personal_head):
        return "Waiting for Fork Android to finish successfully on the current personal commit before syncing another release."
    minimum_version = max(branch_version("origin/main"), branch_version("origin/personal"))
    for version, tag in stable_releases(releases):
        if version < minimum_version:
            continue

        release_ref = f"refs/upstream-releases/{tag}"
        git("fetch", "--no-tags", upstream_url, f"refs/tags/{tag}:{release_ref}")
        commit = git("rev-parse", f"{release_ref}^{{commit}}").stdout.strip()
        if contains("origin/main", commit) and contains("origin/personal", commit):
            continue

        git("switch", "--create", "release-sync-main", "origin/main")
        if not contains("origin/main", commit):
            git("merge", "--ff-only", commit)
        git("switch", "--create", "release-sync-personal", "origin/personal")
        git(
            "-c", "user.name=github-actions[bot]",
            "-c", "user.email=41898282+github-actions[bot]@users.noreply.github.com",
            "merge", "--no-edit", commit,
        )
        git(
            "push", "--atomic", "origin",
            "release-sync-main:refs/heads/main",
            "release-sync-personal:refs/heads/personal",
        )
        return f"Merged official release {tag} into main and personal. Fork Android will build the update."

    return "No newer compatible stable release needs merging. Both branches were left unchanged."


def main():
    response = subprocess.run(
        ["gh", "api", "--paginate", "--slurp", f"repos/{UPSTREAM_REPOSITORY}/releases?per_page=100"],
        check=True, text=True, capture_output=True,
    )
    releases = [release for page in json.loads(response.stdout) for release in page]
    repository = os.environ["GITHUB_REPOSITORY"]
    builds = subprocess.run(
        ["gh", "api", f"repos/{repository}/actions/workflows/fork-android.yml/runs?branch=personal&per_page=1"],
        check=True, text=True, capture_output=True,
    )
    try:
        message = synchronize(releases, build_runs=json.loads(builds.stdout)["workflow_runs"])
    except subprocess.CalledProcessError as error:
        print(error.stderr or str(error), flush=True)
        raise SystemExit("Release sync stopped. Resolve the Git failure before retrying; no force-push is used.")
    print(message)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with Path(summary).open("a") as file:
            file.write(message + "\n")


if __name__ == "__main__":
    main()
