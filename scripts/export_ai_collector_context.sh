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
    echo "# Juniper SRX Prometheus Exporter - LLM Repository Context"
    echo
    echo "Generated: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo
    echo "Purpose:"
    echo "Provide only the source files needed to add a collector."
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

echo "Created: $OUTPUT_FILE"
echo
echo "Review it before sharing:"
echo "  less \"$OUTPUT_FILE\""
echo
echo "Paste these into the LLM in this order:"
echo "  1. AI_COLLECTOR_INSTRUCTIONS.md"
echo "  2. $OUTPUT_FILE"
echo "  3. Junos '| display xml' output"
echo "  4. Junos '| display xml rpc' output"
