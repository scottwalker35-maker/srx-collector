#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="${1:-$HOME/srx-collector}"
OUTPUT_FILE="${2:-$PROJECT_DIR/ai-collector-context.txt}"

cd "$PROJECT_DIR"

files=(
    collector.py
    exporter.py
    exporters/prometheus.py
    lib/netconf.py
    collectors/security_screen.py
    collectors/security_policy_hit_count.py
    config.example.yaml
    README.md
    docs/collectors.md
    docs/metrics.md
)

: > "$OUTPUT_FILE"

{
    echo "# Juniper SRX Prometheus Exporter - LLM Context"
    echo
    echo "Generated: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo
    echo "The live config.yaml file is deliberately excluded."
    echo "Review this output before pasting it into an LLM."
    echo
} >> "$OUTPUT_FILE"

for file in "${files[@]}"; do
    if [[ ! -f "$file" ]]; then
        continue
    fi

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
echo "Then paste these items into the LLM in order:"
echo "  1. AI_COLLECTOR_INSTRUCTIONS.md"
echo "  2. $OUTPUT_FILE"
echo "  3. Junos '| display xml' output"
echo "  4. Junos '| display xml rpc' output"
