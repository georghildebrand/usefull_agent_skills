#!/usr/bin/env bash
# List every file in a repository that can run code during clone, open, build, test or
# install. Read-only: it runs find and grep, never a build tool.
#
# Usage: bash inventory.sh [repo-dir]
#
# The output is the reading list for the review. Every path it prints must be read in full.
# An empty section means "none found", not "not checked".
set -u
ROOT="${1:-.}"
cd "$ROOT" || exit 2

PRUNE=(-path ./.git -o -path '*/node_modules' -o -path '*/target' -o -path '*/.venv' -o -path '*/venv' -o -path '*/dist' -o -path '*/__pycache__')
f() { find . \( "${PRUNE[@]}" \) -prune -o "$@" -print 2>/dev/null | sed 's|^\./||' | sort; }
# g PATTERN NAME...: grep files with these names for PATTERN, print path:line:text.
g() { local pat="$1"; shift; local names=(); for n in "$@"; do names+=(-o -name "$n"); done
  find . \( "${PRUNE[@]}" \) -prune -o -type f \( "${names[@]:1}" \) -exec grep -n -H -E "$pat" {} + 2>/dev/null | sed 's|^\./||' | sort; }
section() { printf '\n== %s\n' "$1"; }
show() { local out; out="$(cat)"; if [ -n "$out" ]; then printf '%s\n' "$out"; else echo "(none)"; fi; }

echo "Repo: $(pwd)"
echo "Tracked files: $(git ls-files 2>/dev/null | wc -l | tr -d ' ')"

section "Runs when an agent or editor opens the folder"
f \( -path '*/.claude/settings*.json' -o -name .mcp.json -o -name CLAUDE.md -o -name AGENTS.md \
  -o -name GEMINI.md -o -name .cursorrules -o -path '*/.cursor/*' -o -path '*/.vscode/tasks.json' \
  -o -path '*/.vscode/settings.json' -o -path '*/.vscode/launch.json' -o -path '*/.devcontainer/*' \
  -o -name .envrc -o -name .env.example \) | show

section "Git: submodules, hooks, filters (code not in this checkout, or run on git actions)"
f \( -name .gitmodules -o -path '*/.husky/*' -o -path '*/.githooks/*' -o -name lefthook.yml \
  -o -name .pre-commit-config.yaml \) | show
grep -n 'filter=' .gitattributes 2>/dev/null
git config --local --get core.hooksPath 2>/dev/null | sed 's/^/core.hooksPath = /'

section "Rust: build scripts (run on every cargo build/test/install)"
# A build script is build.rs next to a Cargo.toml, or the file named by `build = "..."`.
# A build.rs inside src/ is an ordinary module and is not listed.
{ f -name build.rs | while read -r p; do [ -f "$(dirname "$p")/Cargo.toml" ] && echo "$p"; done
  g '^[[:space:]]*build[[:space:]]*=[[:space:]]*"' Cargo.toml; } | show
section "Rust: proc-macro crates (the whole crate runs inside the compiler)"
g '^[[:space:]]*proc-macro[[:space:]]*=[[:space:]]*true' Cargo.toml | show
section "Rust: cargo config and toolchain (runner, linker, rustflags, env, aliases)"
f \( -path '*/.cargo/config' -o -path '*/.cargo/config.toml' -o -name 'rust-toolchain*' \) | show
section "Rust: dependencies not from crates.io ([patch], git, path outside repo)"
g '^\[patch|git[[:space:]]*=|path[[:space:]]*=[[:space:]]*"\.\./\.\.' Cargo.toml | show
[ -f Cargo.lock ] && grep '^source = ' Cargo.lock | sort | uniq -c

section "JavaScript: lifecycle scripts (run on npm/yarn/pnpm install)"
g '"(preinstall|install|postinstall|prepare|prepack|prepublish|postpack)"[[:space:]]*:' package.json | show
section "JavaScript: registry overrides and non-registry dependencies"
{ f \( -name .npmrc -o -name '.yarnrc*' -o -name .pnpmfile.cjs \)
  g '"(git\+|git:|github:|https?:|file:)' package.json; } | show

section "Python: code run by pip install or pytest"
{ f \( -name setup.py -o -name conftest.py -o -name '*.pth' -o -name noxfile.py -o -name tox.ini \)
  g 'build-backend|backend-path' pyproject.toml
  g 'git\+|https?://|--(extra-)?index-url|--trusted-host' 'requirements*.txt'; } | show

section "Build and install entry points (read the install path in full)"
f \( -name Makefile -o -name GNUmakefile -o -name justfile -o -name Justfile -o -name Taskfile.yml \
  -o -path '*/xtask/*' -o -name 'install*.sh' -o -name 'setup*.sh' -o -name Dockerfile \
  -o -name '*.ps1' -o -name CMakeLists.txt -o -name Rakefile -o -name 'gradlew*' -o -name 'mvnw*' \) | show
grep -rn --include='*.go' '//go:generate' . 2>/dev/null | head -20

section "Download-and-run in docs and scripts"
grep -rn -E '(curl|wget)[^|]*\|[[:space:]]*(sudo[[:space:]]+)?(ba|z)?sh|iwr[^|]*\|[[:space:]]*iex' \
  --exclude-dir=.git --exclude-dir=node_modules --exclude-dir=target . 2>/dev/null | head -20 | show

section "Obfuscation hints (read every hit; names can also be split to beat grep)"
grep -rn -E 'base64|atob\(|fromCharCode|\beval\(|exec\(|\]\.concat\(\)|\.join\(""\)' \
  --include='*.rs' --include='*.js' --include='*.mjs' --include='*.cjs' --include='*.ts' \
  --include='*.py' --include='*.sh' --exclude-dir=.git --exclude-dir=node_modules --exclude-dir=target \
  . 2>/dev/null | head -30 | show
