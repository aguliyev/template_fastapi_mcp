#!/usr/bin/env bash
set -euo pipefail

source_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
tmpdir="$(mktemp -d)"
trap 'rm -rf -- "$tmpdir"' EXIT

mkdir -p -- "$tmpdir/bin"
project_root="$tmpdir/project"
mkdir -p -- "$project_root/bin"
cp -- "$source_root/bin/graphify-setup" "$project_root/bin/graphify-setup"
log_file="$tmpdir/uv.log"
git_log_file="$tmpdir/git.log"

cat > "$tmpdir/bin/uv" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$*" >> "$UV_LOG"
if [[ "$*" == 'run --group dev graphify hook install' ]]; then
  printf 'graphify-out/graph.json merge=graphify\n' > .gitattributes
fi
EOF
chmod +x "$tmpdir/bin/uv"

cat > "$tmpdir/bin/git" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$*" >> "$GIT_LOG"
if [[ "$*" == *'--get-regexp'* ]]; then
  exit 1
fi
EOF
chmod +x "$tmpdir/bin/git"

PATH="$tmpdir/bin:$PATH" UV_LOG="$log_file" GIT_LOG="$git_log_file" \
  "$project_root/bin/graphify-setup"

expected=$'sync --group dev\nrun --group dev graphify hook install'
actual="$(cat "$log_file")"
if [[ "$actual" != "$expected" ]]; then
  printf 'unexpected uv invocation:\n%s\n' "$actual" >&2
  exit 1
fi

expected_git="config --local --remove-section merge.graphify"
actual_git="$(cat "$git_log_file")"
if [[ "$actual_git" != "$expected_git" ]]; then
  printf 'unexpected git invocation:\n%s\n' "$actual_git" >&2
  exit 1
fi

if [[ -e "$project_root/.gitattributes" ]]; then
  printf 'Graphify merge attribute should not remain after setup\n' >&2
  exit 1
fi
