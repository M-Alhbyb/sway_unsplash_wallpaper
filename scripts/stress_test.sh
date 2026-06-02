#!/usr/bin/env bash
set -euo pipefail

# Long-Running Stability Stress Test
# Usage: ./scripts/stress_test.sh [duration_minutes]

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
DURATION="${1:-1440}"  # default 24 hours in minutes
INTERVAL=60  # report every 60 seconds
STRESS_DIR="$PROJECT_DIR/stress_results"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
REPORT_FILE="$STRESS_DIR/stress_report_$TIMESTAMP.csv"

mkdir -p "$STRESS_DIR"

echo "============================================"
echo "  Unsplash Wallpaper - Stress Test"
echo "  Duration: ${DURATION}m (${DURATION} minutes)"
echo "  Report: $REPORT_FILE"
echo "============================================"
echo ""

echo "timestamp,cpu_pct,memory_mb,fd_count,db_size_kb,wp_count,py_version" > "$REPORT_FILE"

cleanup() {
    echo ""
    echo "Stopping stress test..."
    kill "$PID" 2>/dev/null || true
    wait "$PID" 2>/dev/null || true
    echo "Stress test completed: $(date)"
}

trap cleanup EXIT INT TERM

# Start diagnostics collector
python3 -c "
import time
import os
import sys
import csv
from pathlib import Path

sys.path.insert(0, '$PROJECT_DIR/src')

from unsplash_wallpaper.database import Database
from unsplash_wallpaper.config import Config
from unsplash_wallpaper.constants import DATABASE_PATH, WALLPAPERS_DIR

report_file = '$REPORT_FILE'

for i in range($DURATION):
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    
    # CPU and memory from /proc
    cpu_pct = 0.0
    mem_mb = 0.0
    fd_count = 0
    try:
        import psutil
        proc = psutil.Process(os.getpid())
        cpu_pct = proc.cpu_percent(interval=0.5)
        mem_mb = proc.memory_info().rss / 1024 / 1024
        fd_count = proc.num_fds()
    except ImportError:
        try:
            with open(f'/proc/{os.getpid()}/status') as f:
                for line in f:
                    if line.startswith('VmRSS:'):
                        mem_mb = float(line.split()[1]) / 1024
                    if line.startswith('FDSize:'):
                        fd_count = int(line.split()[1])
        except Exception:
            pass
    
    db_size_kb = 0
    if DATABASE_PATH.exists():
        db_size_kb = DATABASE_PATH.stat().st_size / 1024
    
    wp_count = 0
    if WALLPAPERS_DIR.exists():
        wp_count = len(list(WALLPAPERS_DIR.iterdir()))
    
    py_ver = sys.version.split()[0]
    
    with open(report_file, 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([timestamp, f'{cpu_pct:.1f}', f'{mem_mb:.1f}', fd_count, f'{db_size_kb:.1f}', wp_count, py_ver])
    
    if i % 60 == 0:
        print(f'  [{i}m/{${DURATION}}m] CPU: {cpu_pct:.1f}%  Mem: {mem_mb:.1f}MB  FDs: {fd_count}  DB: {db_size_kb:.1f}KB  WPs: {wp_count}')
    
    time.sleep(60)
"

echo ""
echo "Generating summary..."
python3 -c "
import csv
from statistics import mean, stdev

with open('$REPORT_FILE') as f:
    reader = csv.DictReader(f)
    rows = list(reader)

if len(rows) < 2:
    print('Not enough data points')
    sys.exit(0)

cpu = [float(r['cpu_pct']) for r in rows]
mem = [float(r['memory_mb']) for r in rows]
fd = [int(r['fd_count']) for r in rows]
db = [float(r['db_size_kb']) for r in rows]

print()
print('============================================')
print('  Stress Test Summary')
print('============================================')
print(f'  Duration:       {len(rows)} minutes')
print(f'  Data points:    {len(rows)}')
print()
print(f'  CPU:')
print(f'    Average:      {mean(cpu):.1f}%')
print(f'    Max:          {max(cpu):.1f}%')
print(f'    Min:          {min(cpu):.1f}%')
print()
print(f'  Memory:')
print(f'    Average:      {mean(mem):.1f} MB')
print(f'    Max:          {max(mem):.1f} MB')
print(f'    Min:          {min(mem):.1f} MB')
print()
print(f'  File Descriptors:')
print(f'    Average:      {mean(fd):.0f}')
print(f'    Max:          {max(fd)}')
print(f'    Min:          {min(fd)}')
print()
print(f'  Database:')
print(f'    Start:        {db[0]:.1f} KB')
print(f'    End:          {db[-1]:.1f} KB')
print(f'    Growth:       {db[-1] - db[0]:.1f} KB')
print()
print(f'  Detailed report: $REPORT_FILE')
print('============================================')
"
