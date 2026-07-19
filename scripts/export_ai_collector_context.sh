#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="${1:-$HOME/srx-collector}"
OUTPUT_FILE="${2:-$PROJECT_DIR/ai-collector-context.txt}"

cd "$PROJECT_DIR"

required_files=(
    collector.py
    exporter.py
    exporters/prometheus.py
    lib/netconf.py
    config.example.yaml
)

for file in "${required_files[@]}"; do
    if [[ ! -f "$file" ]]; then
        echo "ERROR: Missing required context file: $PROJECT_DIR/$file" >&2
        exit 1
    fi
done

mapfile -t collector_files < <(
    find collectors \
        -maxdepth 1 \
        -type f \
        -name '*.py' \
        -printf '%p\n' |
    sort
)

files=(
    collector.py
    exporter.py
    exporters/prometheus.py
    lib/netconf.py
    config.example.yaml
    "${collector_files[@]}"
)

: > "$OUTPUT_FILE"

{
    echo "# Juniper SRX Prometheus Exporter - Optional LLM Source Context"
    echo
    echo "Generated: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo
    echo "Use this only when AI_COLLECTOR_INSTRUCTIONS.md and"
    echo "REPOSITORY_MAP.md are insufficient."
    echo
    echo "The live config.yaml file is deliberately excluded."
    echo "Review this output before sharing it with an LLM."
    echo
} >> "$OUTPUT_FILE"

for file in "${files[@]}"; do
    {
        echo
        echo "================================================================"
        echo "FILE: $file"
        echo "================================================================"

        sed -E \
            -e 's/(password:[[:space:]]*).*/\1REDACTED/I' \
            -e 's/(password[[:space:]]*=[[:space:]]*)[^,)]*/\1"REDACTED"/I' \
            "$file"
    } >> "$OUTPUT_FILE"
done

chmod 600 "$OUTPUT_FILE"

echo "Created optional repository context:"
echo "  $OUTPUT_FILE"
echo
echo "This file is not required for a normal collector request."
echo
echo "Only paste it when the LLM identifies a specific need for repository"
echo "source context."
echo
echo "To display the file:"
echo "  cat \"$OUTPUT_FILE\""
