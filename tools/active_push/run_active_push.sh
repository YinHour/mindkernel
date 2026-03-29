#!/bin/bash
# Active Push Worker launchd bootstrapper
# Label: com.zhengwang.mindkernel.active-push

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DB_PATH="$SCRIPT_DIR/../../../data/mindkernel_v0_1.sqlite"
INTERVAL=300  # 5 minutes

exec python3 "$SCRIPT_DIR/active_push_worker_v0_1.py" \
    --db "$DB_PATH" \
    --daemon \
    --interval $INTERVAL \
    2>>/Users/zhengwang/.logs/mindkernel-active-push.log
