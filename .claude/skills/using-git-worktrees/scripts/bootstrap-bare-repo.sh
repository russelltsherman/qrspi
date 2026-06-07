#!/usr/bin/env bash
set -euo pipefail

# bootstrap-bare-repo.sh — set up a bare-repo-primary checkout for parallel Git
# worktrees: bare clone into .bare/, a top-level .git pointer, the fetch refspec
# a bare clone omits, and a first worktree for the remote's default branch.
#
# Usage: bootstrap-bare-repo.sh <repo-url> [target-dir]
#   <repo-url>    clone URL (https or ssh) of the remote to bootstrap
#   [target-dir]  directory to create (default: repo basename, sans .git)

die() { printf 'error: %s\n' "$*" >&2; exit 1; }

repo_url="${1:?Usage: bootstrap-bare-repo.sh <repo-url> [target-dir]}"
target_dir="${2:-$(basename "${repo_url%.git}")}"

command -v git >/dev/null 2>&1 || die "git is not installed or not on PATH"
[ -e "$target_dir" ] && die "target directory already exists: $target_dir"

mkdir -p "$target_dir" || die "could not create target directory: $target_dir"

# 1. Bare clone into .bare/ so the top level stays free to hold worktrees.
git clone --bare "$repo_url" "$target_dir/.bare" \
  || die "bare clone failed for: $repo_url"

# 2. .git pointer so plain `git` invocations in $target_dir resolve to .bare/.
printf 'gitdir: ./.bare\n' > "$target_dir/.git" \
  || die "could not write .git pointer in: $target_dir"

# 3. A bare clone omits the fetch refspec; set it so origin/* tracking refs
#    populate on fetch (and stay updated thereafter).
git -C "$target_dir" config remote.origin.fetch \
  '+refs/heads/*:refs/remotes/origin/*' \
  || die "could not configure remote.origin.fetch refspec"

# 4. Populate the remote-tracking refs the refspec now describes.
git -C "$target_dir" fetch origin || die "git fetch failed for origin"

# 5. Resolve the remote's default branch (fall back to main) and create the
#    first worktree for it as a sibling directory named after the branch.
default_branch="$(git -C "$target_dir" symbolic-ref --short \
  refs/remotes/origin/HEAD 2>/dev/null | sed 's@^origin/@@' || true)"
[ -n "$default_branch" ] || default_branch="main"

git -C "$target_dir" worktree add "$default_branch" "$default_branch" \
  || die "could not create first worktree for branch: $default_branch"

printf 'Bootstrapped bare repo at %s (first worktree: %s/%s)\n' \
  "$target_dir" "$target_dir" "$default_branch" >&2
