#!/usr/bin/env bash
set -euo pipefail

# Packaging Validation Script for Unsplash Wallpaper
# Usage: ./scripts/validate_packaging.sh

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
TEMP_DIR=$(mktemp -d)
PASS=0
FAIL=0

cleanup() {
    rm -rf "$TEMP_DIR"
}

trap cleanup EXIT

echo "========================================"
echo "  Unsplash Wallpaper - Packaging Validation"
echo "========================================"
echo ""

check() {
    local desc="$1"
    shift
    if "$@" > /dev/null 2>&1; then
        echo "  [PASS] $desc"
        PASS=$((PASS + 1))
    else
        echo "  [FAIL] $desc"
        FAIL=$((FAIL + 1))
    fi
}

# 1. pip install .
check "pip install from source" \
    pip install "$PROJECT_DIR" --quiet

check "package importable after pip install" \
    python -c "import unsplash_wallpaper; print(unsplash_wallpaper.__name__)"

check "version correct after install" \
    python -c "from unsplash_wallpaper.constants import VERSION; assert VERSION == '1.0.0'"

# 2. pipx install
if command -v pipx &> /dev/null; then
    check "pipx install" \
        pipx install "$PROJECT_DIR" --force --quiet

    check "pipx run --version" \
        pipx run unsplash-wallpaper --version

    pipx uninstall unsplash-wallpaper > /dev/null 2>&1 || true
else
    echo "  [SKIP] pipx install (pipx not available)"
fi

# 3. virtualenv install
check "virtualenv creation" \
    python -m venv "$TEMP_DIR/venv"

check "pip install in virtualenv" \
    "$TEMP_DIR/venv/bin/pip" install "$PROJECT_DIR" --quiet

check "run from virtualenv" \
    "$TEMP_DIR/venv/bin/unsplash-wallpaper" --version

# 4. Build check
check "python -m build" \
    python -m build "$PROJECT_DIR" --outdir "$TEMP_DIR/dist" --quiet

check "wheel exists" \
    test -f "$TEMP_DIR/dist/unsplash_wallpaper-1.0.0-py3-none-any.whl"

# 5. Desktop file validation
check "desktop file exists" \
    test -f "$PROJECT_DIR/data/com.unsplash.wallpaper.desktop"

if command -v desktop-file-validate &> /dev/null; then
    check "desktop file validation" \
        desktop-file-validate "$PROJECT_DIR/data/com.unsplash.wallpaper.desktop"
else
    echo "  [SKIP] desktop-file-validate (not available)"
fi

# 6. Systemd unit validation
if command -v systemd-analyze &> /dev/null; then
    check "systemd service validation" \
        systemd-analyze verify "$PROJECT_DIR/data/com.unsplash.wallpaper.service" 2>/dev/null
else
    echo "  [SKIP] systemd-analyze (not available)"
fi

# 7. RPM spec validation
check "RPM spec file exists" \
    test -f "$PROJECT_DIR/data/unsplash-wallpaper.spec"

# 8. Flatpak manifest
check "Flatpak manifest exists" \
    test -f "$PROJECT_DIR/data/com.unsplash.wallpaper.json"

# 9. Icon check
check "icon referenced in desktop file" \
    grep -q "Icon=" "$PROJECT_DIR/data/com.unsplash.wallpaper.desktop"

# 10. License check
check "LICENSE file exists" \
    test -f "$PROJECT_DIR/LICENSE"

# 11. CHANGELOG check
check "CHANGELOG.md exists" \
    test -f "$PROJECT_DIR/CHANGELOG.md"

# 12. CLEANUP pip uninstall
pip uninstall unsplash-wallpaper --quiet --yes > /dev/null 2>&1 || true

echo ""
echo "========================================"
echo "  Results: $PASS passed, $FAIL failed"
echo "========================================"

exit $FAIL
