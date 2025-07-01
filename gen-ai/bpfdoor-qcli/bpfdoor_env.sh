#!/bin/bash
echo "echo [*] Detecting processes with BPFDoor environment variable manipulati
on..."
echo "Target : HOME=/tmp, HISTFILE=/dev/null, MYSQL_HISTFILE=/dev/null"
CHECK_ENV=("HOME=/tmp" "HISTFILE=/dev/null" "MYSQL_HISTFILE=/dev/null")
# Process scanning
for pid in $(ls /proc/ | grep -E '^[0-9]+$'); do
 if [ -r /proc/$pid/environ ]; then
 env_data=$(tr '\0' '\n' < /proc/$pid/environ)
 match_all=true
 for check_item in "${CHECK_ENV[@]}"; do
 if ! echo "$env_data" | grep -q "$check_item"; then
 match_all=false
 break
 fi
 done
 if [ "$match_all" = true ]; then
 echo "Warning: Process with all suspicious environment variables detected
(PID: $pid)"
 echo " → $(ps -p $pid -o user=,pid=,ppid=,cmd=)"
 echo ""
 fi
 fi
done