#!/usr/bin/env bash
# Fully automatic pipeline: generate + publish carousel, no human input needed.
# Logs to output/logs/pipeline.log with timestamps.
#
# Cron setup (Termux) — run twice daily:
#   crontab -e
#   0 14 * * 1-5  cd ~/MemeFactory && bash run.sh   # 7:30 PM IST weekdays
#   30 5 * * 0,6  cd ~/MemeFactory && bash run.sh   # 11:00 AM IST weekends

set -euo pipefail

LOG_DIR="$(dirname "$0")/output/logs"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/pipeline.log"

echo "" >> "$LOG"
echo "=== $(date '+%Y-%m-%d %H:%M:%S') ===" >> "$LOG"

cd "$(dirname "$0")"

python pipeline.py --publish 2>&1 | tee -a "$LOG"
