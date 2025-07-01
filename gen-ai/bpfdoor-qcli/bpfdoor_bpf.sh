#!/bin/bash
echo "[*] Detecting processes with active BPF usage..."
# 1. Extract PIDs directly from ss output
sudo ss -0pb | grep -oP 'pid=\K[0-9]+' | sort -u | while read pid; do
 # 2. For each PID, find the executable path
 if [[ -e "/proc/$pid" ]]; then
 exe_path=$(readlink -f /proc/$pid/exe 2>/dev/null)
 proc_name=$(cat /proc/$pid/comm 2>/dev/null)
 echo ""
 echo "Process Name: ${proc_name:-Unknown}, PID: $pid"
 echo " → Executable: ${exe_path:-Not found}"
 fi
done