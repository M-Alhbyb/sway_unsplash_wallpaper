#!/usr/bin/env bash
set -euo pipefail

# Recovery Testing Script
# Validates recovery from corrupted settings, databases, missing files, etc.
# Usage: ./scripts/recovery_test.sh

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
TEMP_DIR=$(mktemp -d)
PASS=0
FAIL=0
SKIP=0

cleanup() {
    rm -rf "$TEMP_DIR"
}

trap cleanup EXIT

echo "========================================"
echo "  Unsplash Wallpaper - Recovery Tests"
echo "========================================"
echo ""

PACKAGE_DIR="$PROJECT_DIR/src"

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

# Mock data directory
export DATA_DIR="$TEMP_DIR/data"
export WALLPAPERS_DIR="$TEMP_DIR/data/wallpapers"
export DATABASE_PATH="$TEMP_DIR/data/database.db"

mkdir -p "$DATA_DIR" "$WALLPAPERS_DIR"

# 1. Test with no existing data
echo "--- Test 1: Fresh Start (no existing data) ---"
check "database initializes on fresh start" \
    python3 -c "
import sys
sys.path.insert(0, '$PACKAGE_DIR')
from pathlib import Path
from unsplash_wallpaper.database import Database
db = Database(Path('$DATABASE_PATH'))
db.initialize()
assert db.count_wallpapers() == 0
print('Fresh database OK')
db.close_all()
"

# 2. Test corrupted settings
echo ""
echo "--- Test 2: Corrupted Database ---"
check "handles corrupted database gracefully" \
    python3 -c "
import sys
sys.path.insert(0, '$PACKAGE_DIR')
from pathlib import Path
import sqlite3
db_path = Path('$TEMP_DIR/corrupted.db')
db_path.write_text('NOT A VALID SQLITE DATABASE')
try:
    from unsplash_wallpaper.database import Database
    db = Database(db_path)
    db.initialize()
    print('ERROR: Should have raised')
    sys.exit(1)
except Exception as e:
    print(f'Correctly rejected corrupted DB: {e}')
"

# 3. Test missing storage directory
echo ""
echo "--- Test 3: Missing Storage Directory ---"
rm -rf "$WALLPAPERS_DIR"
check "recreates missing storage directory" \
    python3 -c "
import sys
sys.path.insert(0, '$PACKAGE_DIR')
from unsplash_wallpaper.services.storage_service import StorageService
from pathlib import Path
storage = StorageService(Path('$WALLPAPERS_DIR'))
assert Path('$WALLPAPERS_DIR').exists()
print('Storage directory recreated')
"

# 4. Test empty API key
echo ""
echo "--- Test 4: Invalid API Key ---"
check "rejects empty API key" \
    python3 -c "
import sys
sys.path.insert(0, '$PACKAGE_DIR')
from unsplash_wallpaper.config import Config
from unsplash_wallpaper.database import Database
from pathlib import Path
db = Database(Path('$DATABASE_PATH'))
db.initialize()
config = Config(db)
assert config.has_valid_api_key() is False
print('Empty API key correctly rejected')
db.close_all()
"

# 5. Test network timeout
echo ""
echo "--- Test 5: Network Failure ---"
check "handles network timeout gracefully" \
    python3 -c "
import sys
sys.path.insert(0, '$PACKAGE_DIR')
from unittest.mock import MagicMock, patch
from unsplash_wallpaper.services.unsplash_service import UnsplashService, UnsplashNetworkError
config = MagicMock()
config.get.return_value = 'test_key_12345'
with patch('requests.Session.get') as mock_get:
    import requests
    mock_get.side_effect = requests.exceptions.Timeout('Timed out')
    svc = UnsplashService(config)
    try:
        svc.get_random_photo(retries=2)
        print('ERROR: Should have raised')
        sys.exit(1)
    except UnsplashNetworkError as e:
        print(f'Correctly handled timeout: {e}')
"

# 6. Test missing wallpaper files in history
echo ""
echo "--- Test 6: Ghost Wallpaper References ---"
check "handles missing wallpaper files" \
    python3 -c "
import sys
sys.path.insert(0, '$PACKAGE_DIR')
from pathlib import Path
from unsplash_wallpaper.database import Database
from unsplash_wallpaper.services.storage_service import StorageService
from unsplash_wallpaper.services.history_service import HistoryService
from unsplash_wallpaper.config import Config
from unsplash_wallpaper.models.wallpaper import Wallpaper

db = Database(Path('$DATABASE_PATH'))
db.initialize()
storage = StorageService(Path('$WALLPAPERS_DIR'))
config = Config(db)
history = HistoryService(db, storage, config)

wp = Wallpaper(unsplash_id='ghost', local_path=str(Path('$WALLPAPERS_DIR') / 'ghost.jpg'))
history.add(wp)
Path(wp.local_path).unlink(missing_ok=True)
assert not Path(wp.local_path).exists()

latest = history.get_latest()
assert latest is not None
assert latest.unsplash_id == 'ghost'
print('Ghost reference handled correctly')
history.delete(latest.id)
db.close_all()
"

# 7. Test database with WAL mode
echo ""
echo "--- Test 7: Database WAL Mode ---"
check "database WAL mode enabled" \
    python3 -c "
import sys
sys.path.insert(0, '$PACKAGE_DIR')
from pathlib import Path
from unsplash_wallpaper.database import Database
db_path = Path('$TEMP_DIR/wal_test.db')
db = Database(db_path)
db.initialize()
conn = db._get_connection()
cur = conn.execute('PRAGMA journal_mode')
mode = cur.fetchone()[0]
assert mode.lower() == 'wal', f'Expected WAL, got {mode}'
print(f'WAL mode confirmed: {mode}')
db.close_all()
"

# 8. Test concurrent database access
echo ""
echo "--- Test 8: Concurrent Database Access ---"
check "handles concurrent database access" \
    python3 -c "
import sys
sys.path.insert(0, '$PACKAGE_DIR')
import threading
from pathlib import Path
from unsplash_wallpaper.database import Database
from unsplash_wallpaper.config import Config
from unsplash_wallpaper.models.wallpaper import Wallpaper
from unsplash_wallpaper.services.history_service import HistoryService
from unsplash_wallpaper.services.storage_service import StorageService

db = Database(Path('$DATABASE_PATH'))
db.initialize()
storage = StorageService(Path('$WALLPAPERS_DIR'))
config = Config(db)
history = HistoryService(db, storage, config)
errors = []

def add_and_check(idx):
    try:
        wp = Wallpaper(unsplash_id=f'concurrent_{idx}')
        history.add(wp)
        count = history.count()
    except Exception as e:
        errors.append(str(e))

threads = [threading.Thread(target=add_and_check, args=(i,)) for i in range(20)]
for t in threads: t.start()
for t in threads: t.join()

assert len(errors) == 0, f'Errors: {errors}'
print(f'Concurrent access OK - {history.count()} wallpapers')
db.close_all()
"

echo ""
echo "========================================"
echo "  Results: $PASS passed, $FAIL failed, $SKIP skipped"
echo "========================================"

exit $FAIL
