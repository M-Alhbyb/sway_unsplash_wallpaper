#!/usr/bin/env bash
set -euo pipefail

# Sway Validation Script
# Run on Sway desktop to validate wallpaper changes
# Usage: ./scripts/sway_validation.sh

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PASS=0
FAIL=0

echo "========================================"
echo "  Unsplash Wallpaper - Sway Validation"
echo "========================================"
echo ""

check_sway_running() {
    if [ -z "${WAYLAND_DISPLAY:-}" ]; then
        echo "  [SKIP] Not running on Wayland/Sway"
        return 1
    fi
    if ! command -v swaybg &> /dev/null; then
        echo "  [FAIL] swaybg not installed"
        return 1
    fi
    return 0
}

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

# 1. Environment check
echo "--- Environment ---"
check_sway_running || echo "  [SKIP] Sway environment not detected, skipping Sway-specific tests"
check "swaybg in PATH" command -v swaybg
check "notify-send in PATH" command -v notify-send

# 2. Basic wallpaper update test
echo ""
echo "--- Single Wallpaper Update ---"
TEST_IMAGE="/tmp/sway_test_wallpaper.jpg"
convert -size 1920x1080 xc:blue "$TEST_IMAGE" 2>/dev/null || \
    python3 -c "with open('$TEST_IMAGE', 'wb') as f: f.write(b'\xff\xd8' + b'x' * 1000)"

# Run diagnostics
check "diagnostics runs" python3 -m unsplash_wallpaper --diagnostics

# 3. No orphan swaybg processes
echo ""
echo "--- No Orphan Processes ---"
SWAYBG_BEFORE=$(pgrep -c swaybg 2>/dev/null || echo 0)
echo "  swaybg processes before: $SWAYBG_BEFORE"

# 4. Consecutive wallpaper updates
echo ""
echo "--- 100 Consecutive Updates ---"
for i in $(seq 1 100); do
    TEST_IMG="/tmp/sway_stress_${i}.jpg"
    python3 -c "with open('$TEST_IMG', 'wb') as f: f.write(b'\xff\xd8' + b'x' * 1000)"
    
    swaybg -i "$TEST_IMG" -m fill &>/dev/null &
    PID=$!
    sleep 0.1
    kill "$PID" 2>/dev/null || true
    rm -f "$TEST_IMG"
done

SWAYBG_AFTER=$(pgrep -c swaybg 2>/dev/null || echo 0)
echo "  swaybg processes after stress: $SWAYBG_AFTER"

if [ "$SWAYBG_AFTER" -le "$SWAYBG_BEFORE" ]; then
    echo "  [PASS] No orphan swaybg processes"
    PASS=$((PASS + 1))
else
    echo "  [FAIL] Orphan swaybg processes detected"
    killall swaybg 2>/dev/null || true
    FAIL=$((FAIL + 1))
fi

# 5. Rapid updates
echo ""
echo "--- Rapid Updates (5 second intervals) ---"
for i in $(seq 1 12); do
    TEST_IMG="/tmp/sway_rapid_${i}.jpg"
    python3 -c "with open('$TEST_IMG', 'wb') as f: f.write(b'\xff\xd8' + b'x' * 1000)"
    
    swaybg -i "$TEST_IMG" -m fill &>/dev/null &
    PREV_PID=$!
    sleep 5
    kill "$PREV_PID" 2>/dev/null || true
    rm -f "$TEST_IMG"
done

FINAL_SWAYBG=$(pgrep -c swaybg 2>/dev/null || echo 0)
echo "  Final swaybg count: $FINAL_SWAYBG"

if [ "$FINAL_SWAYBG" -le 1 ]; then
    echo "  [PASS] No duplicate swaybg processes"
    PASS=$((PASS + 1))
else
    echo "  [FAIL] Multiple swaybg processes running"
    FAIL=$((FAIL + 1))
fi

# 6. Memory check
echo ""
echo "--- Memory Usage ---"
if command -v ps &> /dev/null; then
    ps -o pid,rss,comm -p $$ 2>/dev/null || true
fi

# Cleanup
killall swaybg 2>/dev/null || true
rm -f /tmp/sway_test_wallpaper.jpg /tmp/sway_stress_*.jpg /tmp/sway_rapid_*.jpg

echo ""
echo "========================================"
echo "  Results: $PASS passed, $FAIL failed"
echo "========================================"

if [ "$FAIL" -gt 0 ]; then
    echo "  WARNING: Some validation checks failed"
fi

exit $FAIL
