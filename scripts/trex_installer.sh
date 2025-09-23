#!/usr/bin/env bash
set -euo pipefail

VER="${1:-3.06}"
BASE_URL="https://trex-tgn.cisco.com/trex/release"
PKG="v${VER}.tar.gz"
DEST="/opt/v${VER}"
TARBALL="/opt/${PKG}"
SYMLINK_CURRENT="/opt/current"

log() { printf "\033[1;32m[+] %s\033[0m\n" "$*"; }
err() { printf "\033[1;31m[!] %s\033[0m\n" "$*" >&2; }
die() { err "$*"; exit 1; }

need_root() { [ "$(id -u)" -eq 0 ] || die "Run as root: sudo $0 [VERSION]"; }

ensure_tools() {
  local missing=()
  for t in wget tar; do command -v "$t" >/dev/null 2>&1 || missing+=("$t"); done
  if [ ${#missing[@]} -gt 0 ]; then
    log "Installing: ${missing[*]}"
    if command -v apt-get >/dev/null 2>&1; then
      apt-get update -y && apt-get install -y "${missing[@]}" ca-certificates
    elif command -v dnf >/dev/null 2>&1; then
      dnf install -y "${missing[@]}" ca-certificates
    elif command -v yum >/dev/null 2>&1; then
      yum install -y "${missing[@]}" ca-certificates
    else
      die "Package manager not found; install ${missing[*]} manually."
    fi
  fi
}

download_trex() {
  if [ -d "$DEST" ] && [ -x "$DEST/t-rex-64" ]; then
    log "TRex ${VER} already present at ${DEST}."
    return 0
  fi
  mkdir -p /opt

  if [ ! -f "$TARBALL" ]; then
    log "Downloading ${BASE_URL}/${PKG} -> ${TARBALL}"
    wget --no-check-certificate --tries=3 --timeout=30 -O "$TARBALL" "${BASE_URL}/${PKG}" \
      || die "Download failed."
  else
    log "Using existing tarball: ${TARBALL}"
  fi

  log "Verifying archive..."
  tar -tzf "$TARBALL" >/dev/null 2>&1 || die "Corrupt/invalid tar.gz."

  log "Extracting to /opt ..."
  tar -xzf "$TARBALL" -C /opt

  if [ ! -d "$DEST" ]; then
    CAND="$(find /opt -maxdepth 1 -type d -name "v${VER}" -print -quit || true)"
    if [ -z "$CAND" ]; then
      CAND="$(find /opt -maxdepth 1 -type d -exec test -f '{}/t-rex-64' \; -print -quit || true)"
    fi
    [ -n "$CAND" ] || die "Could not find extracted TRex directory."
    [ "$CAND" = "$DEST" ] || mv "$CAND" "$DEST"
  fi

  [ -x "$DEST/t-rex-64" ] || die "t-rex-64 binary not found in ${DEST}."
  log "Cleaning tarball ..."
  rm -f "$TARBALL"
}

post_install() {
  log "Creating convenience symlinks ..."
  ln -sfn "$DEST" "$SYMLINK_CURRENT" || true
  [ -f "$DEST/t-rex-64" ] && ln -sfn "$DEST/t-rex-64" /usr/local/bin/t-rex-64 || true
  [ -f "$DEST/scripts/trex-console/trex-console" ] && \
    ln -sfn "$DEST/scripts/trex-console/trex-console" /usr/local/bin/trex-console || true

  if [ -f "./trex_cfg.yaml" ] && [ ! -f "/etc/trex_cfg.yaml" ]; then
    log "Installing trex_cfg.yaml to /etc/trex_cfg.yaml"
    cp ./trex_cfg.yaml /etc/trex_cfg.yaml
  fi
}

main() {
  need_root
  ensure_tools
  download_trex
  post_install
  log "TRex ${VER} installed at ${DEST}"
  echo -e "\nQuick start:\n  cd ${DEST}\n  sudo ./t-rex-64 -i"
}

main "$@"
