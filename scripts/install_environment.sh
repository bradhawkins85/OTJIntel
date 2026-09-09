#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
PROJECT_ROOT=$(cd "${SCRIPT_DIR}/.." && pwd)
ENV_FILE="${PROJECT_ROOT}/.env"
ENV_TEMPLATE="${PROJECT_ROOT}/.env.example"
VENV_DIR="${PROJECT_ROOT}/.venv"
ENV_FILE_CREATED=0

usage() {
  cat <<'USAGE'
Usage: install_environment.sh <environment>

Prepare a MyPortal installation for the specified environment. Supported
environments are:
  production   Installs dependencies in a dedicated virtual environment using
               regular (non-editable) mode.
  development  Installs dependencies in editable mode to support local
               iteration alongside production deployments.
USAGE
}

if [[ $# -lt 1 ]]; then
  usage >&2
  exit 1
fi

ENVIRONMENT="$1"
case "$ENVIRONMENT" in
  production|development)
    ;;
  *)
    echo "Error: Unsupported environment '${ENVIRONMENT}'." >&2
    usage >&2
    exit 1
    ;;
esac

select_system_python() {
  if command -v python3 >/dev/null 2>&1; then
    printf '%s' "$(command -v python3)"
    return
  fi
  if command -v python >/dev/null 2>&1; then
    printf '%s' "$(command -v python)"
    return
  fi
  printf ''
}

SYSTEM_PYTHON=$(select_system_python)

if [[ -z "$SYSTEM_PYTHON" ]]; then
  echo "Error: Python 3 is required to run the installer." >&2
  exit 1
fi

ensure_env_file() {
  if [[ -f "$ENV_FILE" ]]; then
    return
  fi

  if [[ ! -f "$ENV_TEMPLATE" ]]; then
    echo "Error: ${ENV_TEMPLATE} template not found." >&2
    exit 1
  fi

  cp "$ENV_TEMPLATE" "$ENV_FILE"
  ENV_FILE_CREATED=1
  echo "Created ${ENV_FILE} from template." >&2
}

read_env_value() {
  local key="$1"
  local default_value="${2:-}"

  if [[ ! -f "$ENV_FILE" ]]; then
    printf '%s' "$default_value"
    return
  fi

  ENV_LOOKUP_KEY="$key" \
    ENV_LOOKUP_DEFAULT="$default_value" \
    ENV_LOOKUP_FILE="$ENV_FILE" \
    "$SYSTEM_PYTHON" - <<'PY'
from __future__ import annotations

import os
from pathlib import Path

env_path = Path(os.environ["ENV_LOOKUP_FILE"])
key = os.environ["ENV_LOOKUP_KEY"]
default = os.environ.get("ENV_LOOKUP_DEFAULT", "")

if not env_path.exists():
    print(default)
    raise SystemExit

for raw_line in env_path.read_text(encoding="utf-8").splitlines():
    stripped = raw_line.strip()
    if not stripped or stripped.startswith("#") or "=" not in raw_line:
        continue
    name, value = raw_line.split("=", 1)
    if name.strip() != key:
        continue
    value = value.strip()
    if value and len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        value = value[1:-1]
    print(value)
    break
else:
    print(default)
PY
}

set_env_value() {
  local key="$1"
  local value="$2"

  if [[ ! -f "$ENV_FILE" ]]; then
    return
  fi

  ENV_SET_KEY="$key" \
    ENV_SET_VALUE="$value" \
    ENV_SET_FILE="$ENV_FILE" \
    "$SYSTEM_PYTHON" - <<'PY'
from __future__ import annotations

import os
from pathlib import Path

env_path = Path(os.environ["ENV_SET_FILE"])
key = os.environ["ENV_SET_KEY"]
value = os.environ["ENV_SET_VALUE"]

content = env_path.read_text(encoding="utf-8") if env_path.exists() else ""
lines = content.splitlines()

for index, raw_line in enumerate(lines):
    stripped = raw_line.strip()
    if not stripped or stripped.startswith("#") or "=" not in raw_line:
        continue
    name, _ = raw_line.split("=", 1)
    if name.strip() != key:
        continue
    lines[index] = f"{key}={value}"
    break
else:
    lines.append(f"{key}={value}")

updated = "\n".join(lines)
if updated:
    updated += "\n"
env_path.write_text(updated, encoding="utf-8")
PY
}

default_service_name() {
  if [[ "$ENVIRONMENT" == "development" ]]; then
    printf '%s' "myportal-development"
    return
  fi
  printf '%s' "myportal"
}

sync_environment_metadata() {
  set_env_value "ENVIRONMENT" "$ENVIRONMENT"
  if [[ "$ENV_FILE_CREATED" == "1" ]]; then
    set_env_value "SYSTEMD_SERVICE_NAME" "$(default_service_name)"
  fi
}

ensure_env_default() {
  local key="$1"
  local default_value="$2"

  if [[ ! -f "$ENV_FILE" ]]; then
    return
  fi

  ENV_DEFAULT_KEY="$key" \
    ENV_DEFAULT_VALUE="$default_value" \
    ENV_DEFAULT_FILE="$ENV_FILE" \
    "$SYSTEM_PYTHON" - <<'PY'
from __future__ import annotations

import os
from pathlib import Path

env_path = Path(os.environ["ENV_DEFAULT_FILE"])
key = os.environ["ENV_DEFAULT_KEY"]
default = os.environ["ENV_DEFAULT_VALUE"]

existing = env_path.read_text(encoding="utf-8") if env_path.exists() else ""
for raw_line in existing.splitlines():
    stripped = raw_line.strip()
    if not stripped or stripped.startswith("#") or "=" not in raw_line:
        continue
    name, _ = raw_line.split("=", 1)
    if name.strip() == key:
        break
else:
    suffix = "" if not existing or existing.endswith("\n") else "\n"
    env_path.write_text(existing + f"{suffix}{key}={default}\n", encoding="utf-8")
PY
}

ensure_env_secret() {
  # Replace weak or placeholder values for the given key with a freshly
  # generated cryptographically-random string. Existing non-placeholder
  # values are left untouched so redeploying never rotates live secrets.
  local key="$1"
  local byte_length="${2:-48}"

  if [[ ! -f "$ENV_FILE" ]]; then
    return
  fi

  ENV_SECRET_KEY="$key" \
    ENV_SECRET_BYTES="$byte_length" \
    ENV_SECRET_FILE="$ENV_FILE" \
    "$SYSTEM_PYTHON" - <<'PY'
from __future__ import annotations

import os
import secrets
from pathlib import Path

env_path = Path(os.environ["ENV_SECRET_FILE"])
key = os.environ["ENV_SECRET_KEY"]
byte_length = int(os.environ.get("ENV_SECRET_BYTES", "48"))

PLACEHOLDER = {
    "",
    "change-me",
    "changeme",
    "change_me",
    "please-change",
    "replace-me",
    "secret",
    "password",
}


def looks_weak(value: str) -> bool:
    stripped = value.strip().strip('"').strip("'")
    if stripped.lower() in PLACEHOLDER:
        return True
    if len(stripped) < 24:
        return True
    return False


content = env_path.read_text(encoding="utf-8") if env_path.exists() else ""
lines = content.splitlines()
updated = False
found = False
for index, raw_line in enumerate(lines):
    stripped = raw_line.strip()
    if not stripped or stripped.startswith("#") or "=" not in raw_line:
        continue
    name, value = raw_line.split("=", 1)
    if name.strip() != key:
        continue
    found = True
    if looks_weak(value):
        new_value = secrets.token_urlsafe(byte_length)
        lines[index] = f"{key}={new_value}"
        updated = True
        print(f"Generated new value for {key}.")
    break

if not found:
    new_value = secrets.token_urlsafe(byte_length)
    suffix = "" if not content or content.endswith("\n") else "\n"
    env_path.write_text(content + f"{suffix}{key}={new_value}\n", encoding="utf-8")
    print(f"Appended new value for {key}.")
elif updated:
    trailing = "\n" if content.endswith("\n") else ""
    env_path.write_text("\n".join(lines) + trailing, encoding="utf-8")
PY
}

secure_env_file_permissions() {
  if [[ -f "$ENV_FILE" ]]; then
    chmod 600 "$ENV_FILE" 2>/dev/null || true
  fi
}

ensure_python_venv_available() {
  # On Debian/Ubuntu the venv module ships in a separate package that is
  # often absent on minimal images. Install it (plus python3-pip so that
  # pip is available inside the new venv) when apt-get is present.
  #
  # Note: on Debian/Ubuntu, `import ensurepip` may succeed even when the
  # bundled pip wheels have been stripped out (python3-pip is a separate
  # package). We therefore also check that ensurepip actually has wheels.
  local needs_venv=false
  local needs_pip=false

  if ! "$SYSTEM_PYTHON" -c "import ensurepip" >/dev/null 2>&1; then
    needs_venv=true
    needs_pip=true
  elif ! "$SYSTEM_PYTHON" -c "import ensurepip; ensurepip._get_packages_info()" >/dev/null 2>&1; then
    # ensurepip is present but has no bundled pip wheels (stripped Debian/Ubuntu install)
    needs_pip=true
  fi

  if $needs_venv || $needs_pip; then
    if command -v apt-get >/dev/null 2>&1; then
      echo "Installing missing Python packaging tools (python3-venv and/or python3-pip)…" >&2
      apt-get update -qq
      # Determine the exact python version (e.g. 3.12) for the versioned package name.
      local py_ver
      py_ver=$("$SYSTEM_PYTHON" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
      if $needs_venv; then
        apt-get install -y -qq "python${py_ver}-venv" python3-pip
      else
        apt-get install -y -qq python3-pip
      fi
    else
      echo "Error: python3-venv (ensurepip) is not available and apt-get was not found." >&2
      echo "Install the python3-venv package for your distribution and rerun this installer." >&2
      exit 1
    fi
  fi
}

_bootstrap_pip_in_venv() {
  # Ensure pip is available inside the venv whose Python interpreter is $1.
  local venv_py="$1"

  if "$venv_py" -m pip --version >/dev/null 2>&1; then
    return 0
  fi

  # Try the stdlib ensurepip module first.
  "$venv_py" -m ensurepip --upgrade 2>/dev/null || true

  if "$venv_py" -m pip --version >/dev/null 2>&1; then
    "$venv_py" -m pip install --quiet --upgrade pip setuptools wheel
    return 0
  fi

  # ensurepip either failed or left no pip wheel (stripped Debian/Ubuntu).
  # Fall back to get-pip.py.
  echo "ensurepip did not install pip; falling back to get-pip.py…" >&2
  local get_pip_url="https://bootstrap.pypa.io/get-pip.py"
  local get_pip_tmp
  get_pip_tmp=$(mktemp /tmp/get-pip-XXXXXX.py)
  if command -v curl >/dev/null 2>&1; then
    curl -fsSL "$get_pip_url" -o "$get_pip_tmp"
  elif command -v wget >/dev/null 2>&1; then
    wget -q "$get_pip_url" -O "$get_pip_tmp"
  else
    echo "Error: pip could not be bootstrapped and neither curl nor wget is available." >&2
    echo "Install python3-pip and rerun the installer." >&2
    rm -f "$get_pip_tmp"
    exit 1
  fi
  "$venv_py" "$get_pip_tmp" --quiet
  rm -f "$get_pip_tmp"

  "$venv_py" -m pip install --quiet --upgrade pip setuptools wheel
}

ensure_virtualenv() {
  local venv_py

  if [[ -d "$VENV_DIR" ]]; then
    venv_py=$(venv_python)
    # Re-bootstrap pip if the venv exists but pip is missing (e.g. the venv
    # was created with --without-pip on a previous run that failed mid-way).
    if [[ -n "$venv_py" ]] && ! "$venv_py" -m pip --version >/dev/null 2>&1; then
      echo "Existing venv is missing pip; re-bootstrapping…" >&2
      _bootstrap_pip_in_venv "$venv_py"
      echo "pip bootstrapped in ${VENV_DIR}." >&2
    fi
    return
  fi

  ensure_python_venv_available

  # Create the venv without pip first; we bootstrap pip below via ensurepip
  # so the venv works correctly even on distros that ship a stripped venv.
  "$SYSTEM_PYTHON" -m venv --without-pip "$VENV_DIR"
  echo "Created virtual environment at ${VENV_DIR}." >&2

  venv_py=$(venv_python)
  if [[ -z "$venv_py" ]]; then
    echo "Error: Unable to locate virtualenv python interpreter after creation." >&2
    exit 1
  fi

  _bootstrap_pip_in_venv "$venv_py"
  echo "pip bootstrapped in ${VENV_DIR}." >&2
}

venv_python() {
  if [[ -x "${VENV_DIR}/bin/python" ]]; then
    printf '%s' "${VENV_DIR}/bin/python"
    return
  fi
  if [[ -x "${VENV_DIR}/Scripts/python.exe" ]]; then
    printf '%s' "${VENV_DIR}/Scripts/python.exe"
    return
  fi
  printf ''
}

install_dependencies() {
  local python_bin
  python_bin=$(venv_python)

  if [[ -z "$python_bin" ]]; then
    echo "Error: Unable to locate virtualenv python interpreter." >&2
    exit 1
  fi

  if [[ "$ENVIRONMENT" == "development" ]]; then
    "$python_bin" -m pip install --upgrade -e "$PROJECT_ROOT"
  else
    "$python_bin" -m pip install --upgrade "$PROJECT_ROOT"
  fi
}

install_sip_client() {
  if command -v baresip >/dev/null 2>&1; then
    echo "SIP client (baresip) is already installed." >&2
    return
  fi
  if ! command -v apt-get >/dev/null 2>&1; then
    echo "Error: baresip is required; install it and rerun this installer." >&2
    exit 1
  fi
  echo "Installing server SIP client (baresip)…" >&2
  apt-get update -qq
  apt-get install -y -qq baresip
  command -v baresip >/dev/null 2>&1 || { echo "Error: baresip installation failed." >&2; exit 1; }
}

# ---------------------------------------------------------------------------
# Go toolchain – required for building the tray app binaries
# ---------------------------------------------------------------------------

GO_MIN_MAJOR=1
GO_MIN_MINOR=22

_go_satisfies_version() {
  local go_bin="$1"
  local version_output
  version_output=$("$go_bin" version 2>/dev/null) || return 1
  local major minor
  if [[ "$version_output" =~ go([0-9]+)\.([0-9]+) ]]; then
    major="${BASH_REMATCH[1]}"
    minor="${BASH_REMATCH[2]}"
    if [[ "$major" -gt "$GO_MIN_MAJOR" ]] || \
       [[ "$major" -eq "$GO_MIN_MAJOR" && "$minor" -ge "$GO_MIN_MINOR" ]]; then
      return 0
    fi
  fi
  return 1
}

_detect_go() {
  local -a candidates=("${GOROOT:-/usr/local/go}/bin/go" "go")
  local candidate resolved
  for candidate in "${candidates[@]}"; do
    if [[ "$candidate" == /* ]]; then
      [[ -x "$candidate" ]] && resolved="$candidate" || continue
    else
      command -v "$candidate" >/dev/null 2>&1 && resolved=$(command -v "$candidate") || continue
    fi
    if _go_satisfies_version "$resolved"; then
      printf '%s' "$resolved"
      return 0
    fi
  done
  return 1
}

install_go() {
  if _detect_go >/dev/null 2>&1; then
    local go_bin
    go_bin=$(_detect_go)
    echo "Go toolchain found: $("$go_bin" version)." >&2
    return
  fi

  if ! command -v apt-get >/dev/null 2>&1; then
    echo "Warning: apt-get not found – skipping Go installation." >&2
    echo "Install Go ${GO_MIN_MAJOR}.${GO_MIN_MINOR}+ manually to enable tray app builds: https://go.dev/dl/" >&2
    return
  fi

  echo "Go ${GO_MIN_MAJOR}.${GO_MIN_MINOR}+ not found; installing via apt-get…" >&2
  if ! apt-get update -qq; then
    echo "Warning: apt-get update failed – skipping Go installation." >&2
    return
  fi
  if ! apt-get install -y -qq golang-go; then
    echo "Warning: Failed to install golang-go package." >&2
    return
  fi

  if _detect_go >/dev/null 2>&1; then
    local go_bin
    go_bin=$(_detect_go)
    echo "Go toolchain installed: $("$go_bin" version)." >&2
  else
    echo "Warning: golang-go installed but Go ${GO_MIN_MAJOR}.${GO_MIN_MINOR}+ was not detected." >&2
    echo "Install Go ${GO_MIN_MAJOR}.${GO_MIN_MINOR}+ manually: https://go.dev/dl/" >&2
  fi
}

build_tray_installers() {
  local tray_dir="${PROJECT_ROOT}/tray"
  local static_tray_dir="${PROJECT_ROOT}/app/static/tray"

  if [[ ! -f "${tray_dir}/Makefile" ]]; then
    echo "Tray app Makefile not found; skipping tray build." >&2
    return
  fi

  local go_bin
  if ! go_bin=$(_detect_go 2>/dev/null); then
    echo "Go ${GO_MIN_MAJOR}.${GO_MIN_MINOR}+ not available; skipping tray build." >&2
    return
  fi

  if ! command -v make >/dev/null 2>&1; then
    echo "make not available; skipping tray build." >&2
    return
  fi

  echo "Attempting to build tray installers…" >&2
  local go_dir
  go_dir=$(dirname "$go_bin")
  if (cd "$tray_dir" && PATH="${go_dir}:${PATH}" make build-msi); then
    mkdir -p "$static_tray_dir"
    if [[ -f "${tray_dir}/dist/windows/myportal-tray.msi" ]]; then
      cp "${tray_dir}/dist/windows/myportal-tray.msi" "${static_tray_dir}/myportal-tray.msi"
      echo "MSI installer built and copied → app/static/tray/" >&2
    fi
    if [[ -f "${tray_dir}/dist/darwin/myportal-tray.pkg" ]]; then
      cp "${tray_dir}/dist/darwin/myportal-tray.pkg" "${static_tray_dir}/myportal-tray.pkg"
      echo "PKG installer copied → app/static/tray/" >&2
    fi
    if [[ -f "${tray_dir}/dist/darwin/myportal-tray.dmg" ]]; then
      cp "${tray_dir}/dist/darwin/myportal-tray.dmg" "${static_tray_dir}/myportal-tray.dmg"
      echo "DMG installer copied → app/static/tray/" >&2
    fi
    if [[ ! -f "${tray_dir}/dist/windows/myportal-tray.msi" ]]; then
      echo "Warning: MSI build reported success but myportal-tray.msi was not found at expected path." >&2
    fi
  else
    echo "Warning: MSI build failed." >&2
  fi
}

resolve_service_name() {
  local configured
  configured=$(read_env_value "SYSTEMD_SERVICE_NAME" "$(default_service_name)")
  if [[ -n "$configured" ]]; then
    printf '%s' "$configured"
    return
  fi
  default_service_name
}

resolve_service_unit_name() {
  local unit_name
  unit_name=$(resolve_service_name)
  if [[ "$unit_name" != *.service ]]; then
    unit_name="${unit_name}.service"
  fi
  printf '%s' "$unit_name"
}

resolve_service_user() {
  local configured
  configured=$(read_env_value "SERVICE_USER" "")
  if [[ -n "$configured" ]]; then
    printf '%s' "$configured"
    return
  fi
  if [[ -n "${SUDO_USER:-}" && "${SUDO_USER}" != "root" ]]; then
    printf '%s' "$SUDO_USER"
    return
  fi
  id -un
}

resolve_service_group() {
  local service_user="$1"
  local service_group
  service_group=$(id -gn "$service_user" 2>/dev/null || true)
  if [[ -n "$service_group" ]]; then
    printf '%s' "$service_group"
    return
  fi
  printf '%s' "$service_user"
}

run_privileged() {
  if [[ "${EUID:-$(id -u)}" == "0" ]]; then
    "$@"
    return
  fi
  if command -v sudo >/dev/null 2>&1; then
    sudo "$@"
    return
  fi
  return 127
}

reset_project_permissions() {
  local service_user="$1"
  if [[ "${EUID:-$(id -u)}" != "0" ]]; then
    return
  fi
  if [[ -z "$service_user" ]] || ! id "$service_user" >/dev/null 2>&1; then
    echo "Warning: Service user '${service_user}' is invalid; skipping ownership reset." >&2
    return
  fi

  local service_group
  service_group=$(resolve_service_group "$service_user")
  chown -R "$service_user:$service_group" "$PROJECT_ROOT"
}

install_systemd_service() {
  if [[ "$(uname -s)" != "Linux" ]]; then
    echo "Skipping systemd service installation on non-Linux host." >&2
    return 0
  fi
  if ! command -v systemctl >/dev/null 2>&1; then
    echo "systemctl not found; skipping automatic service installation." >&2
    return 0
  fi
  if ! run_privileged systemctl list-unit-files >/dev/null 2>&1; then
    echo "systemd is not available on this host; skipping automatic service installation." >&2
    return 0
  fi

  local service_user
  service_user=$(resolve_service_user)
  if ! id "$service_user" >/dev/null 2>&1; then
    echo "Error: Service user '${service_user}' does not exist." >&2
    return 1
  fi

  local service_group
  service_group=$(resolve_service_group "$service_user")
  local unit_name
  unit_name=$(resolve_service_unit_name)

  local service_port service_workers
  if [[ "$ENVIRONMENT" == "development" ]]; then
    service_port=8001
    service_workers=2
  else
    service_port=8000
    service_workers=4
  fi

  local tmp_unit
  tmp_unit=$(mktemp /tmp/myportal-systemd-XXXXXX.service)
  cat >"$tmp_unit" <<EOF
# Managed by scripts/install_environment.sh
[Unit]
Description=MyPortal customer portal (${ENVIRONMENT})
After=network-online.target mysql.service redis.service
Wants=network-online.target

[Service]
Type=notify
User=${service_user}
Group=${service_group}
WorkingDirectory=${PROJECT_ROOT}
EnvironmentFile=${ENV_FILE}
ExecStart=${PROJECT_ROOT}/scripts/start_with_auto_update.sh ${VENV_DIR}/bin/uvicorn app.main:app --host 0.0.0.0 --port ${service_port} --workers ${service_workers}
ExecReload=/bin/kill -s HUP \$MAINPID
Restart=always
RestartSec=5
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=full
ProtectHome=true
ReadWritePaths=${PROJECT_ROOT}

[Install]
WantedBy=multi-user.target
EOF

  local unit_path="/etc/systemd/system/${unit_name}"
  if ! run_privileged install -D -m 0644 "$tmp_unit" "$unit_path"; then
    rm -f "$tmp_unit"
    echo "Error: Failed to install systemd unit at ${unit_path}." >&2
    return 1
  fi
  rm -f "$tmp_unit"

  if ! run_privileged systemctl daemon-reload; then
    echo "Error: systemctl daemon-reload failed." >&2
    return 1
  fi
  if ! run_privileged systemctl enable --now "$unit_name"; then
    echo "Error: Failed to enable or start ${unit_name}." >&2
    return 1
  fi

  echo "Installed and started ${unit_name}." >&2
}

ensure_env_file
sync_environment_metadata
ensure_env_default "ENABLE_AUTO_REFRESH" "false"
ensure_env_default "UVICORN_AUTO_UPDATE_ENABLED" "true"
ensure_env_default "UVICORN_AUTO_UPDATE_ATTEMPTS" "2"
ensure_env_default "UVICORN_AUTO_UPDATE_RETRY_DELAY" "5"

# Security: replace placeholder secrets with cryptographically random values.
# Existing non-placeholder values are preserved, so running the installer on an
# already-provisioned host never rotates live keys.
ensure_env_secret "SESSION_SECRET" 48
ensure_env_secret "TOTP_ENCRYPTION_KEY" 48
ensure_env_secret "SMTP2GO_WEBHOOK_SECRET" 32
ensure_env_secret "PLAUSIBLE_PEPPER" 32
ensure_env_secret "MCP_TOKEN" 32
secure_env_file_permissions

cat <<'REMINDER'

SECURITY REMINDER:
  - Your .env file has been set to mode 0600 (owner-only).
  - If fresh secrets were generated above, store a secure backup. Losing
    TOTP_ENCRYPTION_KEY will make stored TOTP secrets and encrypted
    integration credentials unrecoverable.
  - Rotate SESSION_SECRET and TOTP_ENCRYPTION_KEY at least annually and
    whenever an operator with access to the server leaves.

REMINDER

install_go
install_sip_client
ensure_virtualenv
install_dependencies
build_tray_installers
reset_project_permissions "$(resolve_service_user)"
install_systemd_service

cat <<MESSAGE
MyPortal ${ENVIRONMENT} environment is ready.
- Environment file: ${ENV_FILE}
- Virtualenv: ${VENV_DIR}
- Service: $(resolve_service_unit_name)

Database migrations run automatically during application startup.
MESSAGE
