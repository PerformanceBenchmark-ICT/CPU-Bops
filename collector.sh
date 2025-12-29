#!/bin/bash
# ----------------------------------------------------
# collector.sh: 采集脚本启动器 (精简版 - BOPs Only)
# ----------------------------------------------------
# 作用：解析命令行参数，并启动核心执行器 agent_executor.sh
# ----------------------------------------------------
set -e # 任何命令失败则立即退出

# --- 1. 初始化参数默认值 ---
TASK_ID=""
UPLOAD_FILE_PATH=""
OUTPUT_PATH="" # 最终结果输出路径
MONITOR_DURATION="60s"
COLLECT_FREQUENCY="1s"

# --- 2. 解析传入的命令行参数 ---
while [ "$#" -gt 0 ]; do
    case "$1" in
        --id=*) TASK_ID="${1#*=}";;
        --upload-file-path=*) UPLOAD_FILE_PATH="${1#*=}";;
        --output-path=*) OUTPUT_PATH="${1#*=}";;
        --monitor-duration=*) MONITOR_DURATION="${1#*=}";;
        --collect-frequency=*) COLLECT_FREQUENCY="${1#*=}";;
        *) echo "警告: 忽略未知参数 $1";;
    esac
    shift
done

# --- 3. 检查必要参数 ---
if [ -z "$TASK_ID" ] || [ -z "$UPLOAD_FILE_PATH" ] || [ -z "$OUTPUT_PATH" ]; then
  echo "错误: --id, --upload-file-path, 和 --output-path 是必需的。" >&2
  exit 1
fi

# --- 4. 检查核心脚本是否存在 ---
if [ ! -f "./agent_executor.sh" ]; then
    echo "错误: 当前目录下找不到 agent_executor.sh" >&2
    exit 1
fi

# --- 5. 调用执行器 agent_executor.sh ---
echo "启动 agent_executor.sh..."
echo "  ID: $TASK_ID"
echo "  负载: $UPLOAD_FILE_PATH"
echo "  时长: $MONITOR_DURATION"

# 确保有执行权限
chmod +x ./agent_executor.sh 2>/dev/null || true

# 只传递需要的 5 个参数
bash ./agent_executor.sh \
    --id="$TASK_ID" \
    --upload-file-path="$UPLOAD_FILE_PATH" \
    --output-path="$OUTPUT_PATH" \
    --monitor-duration="$MONITOR_DURATION" \
    --collect-frequency="$COLLECT_FREQUENCY"

# --- 6. 捕获退出码并返回 ---
exit_code=$?
if [ $exit_code -ne 0 ]; then
    echo "错误: 执行器 agent_executor.sh 异常退出，代码 $exit_code" >&2
fi
exit $exit_code
