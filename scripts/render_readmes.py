import yaml
import os
import sys
from typing import Any


# =========================
# Global Error Handler
# =========================

error_messages = []

def handle_error(message: str) -> None:
    """
    Centralised error handler.
    Change this function to log, raise, or store errors globally.
    """
    error_messages.append(message)


# =========================
# Markdown Table Generator
# =========================

def matrix_to_markdown_table(data: list[list[Any]]) -> str:
    if not data or len(data) < 2:
        handle_error("Markdown table requires at least a header and one row.")
        return ""

    header_len = len(data[0])

    # Normalise rows to header length
    normalised = []
    for idx, row in enumerate(data):
        if len(row) != header_len:
            handle_error(
                f"Row {idx} has {len(row)} columns; expected {header_len}. Padding/truncating."
            )
        fixed_row = (row + [""] * header_len)[:header_len]
        normalised.append([str(cell) for cell in fixed_row])

    try:
        col_widths = [
            max(len(row[i]) for row in normalised)
            for i in range(header_len)
        ]
    except Exception as e:
        handle_error(f"Failed to calculate column widths: {e}")
        return ""

    def format_row(row):
        return "| " + " | ".join(
            row[i].ljust(col_widths[i]) for i in range(header_len)
        ) + " |"

    lines = [
        format_row(normalised[0]),
        "| " + " | ".join("-" * w for w in col_widths) + " |"
    ]

    for row in normalised[1:]:
        lines.append(format_row(row))

    return "\n".join(lines)


# =========================
# Progress Table Generator
# =========================

def progress_by_parts_table(progress: Any) -> str:
    if not isinstance(progress, dict):
        handle_error("Progress data must be a dictionary.")
        return ""

    data = [["Part", "Pages Complete", "Percentage Completion"]]
    total_completed = 0
    total_pages = 0

    for part, stats in progress.items():
        if not isinstance(stats, dict):
            handle_error(f"Stats for part '{part}' must be a dictionary.")
            continue

        completed = stats.get("completed_pages")
        pages = stats.get("total_pages")

        if not isinstance(completed, int) or not isinstance(pages, int):
            handle_error(f"Invalid page counts for part '{part}'.")
            continue

        if pages <= 0:
            handle_error(f"Total pages for part '{part}' must be > 0.")
            percent = "INVALID"
        else:
            percent = f"{(completed / pages * 100):.0f}%"
            total_completed += completed
            total_pages += pages

        data.append([part, f"{completed}/{pages}", percent])

    if total_pages > 0:
        total_percent = f"{(total_completed / total_pages * 100):.0f}%"
    else:
        handle_error("Total pages across all parts is zero.")
        total_percent = "INVALID"

    data.append(
        ["**Total**", f"**{total_completed}/{total_pages}**", f"**{total_percent}**"]
    )

    return matrix_to_markdown_table(data)


# =========================
# Main Logic
# =========================

def main() -> None:
    base_dir = os.path.abspath(".")

    try:
        with open("progress.yaml", encoding="utf-8") as f:
            progress = yaml.safe_load(f)
    except Exception as e:
        handle_error(f"Failed to load progress.yaml: {e}")
        return

    if not isinstance(progress, dict):
        handle_error("Top-level YAML structure must be a dictionary.")
        return

    for category, stats in progress.items():
        if not isinstance(stats, dict):
            handle_error(f"Category '{category}' must be a dictionary.")
            continue

        parts = stats.get("parts")
        files = stats.get("files", [])

        if not isinstance(parts, dict):
            handle_error(f"Missing or invalid 'parts' for category '{category}'.")
            continue

        table = progress_by_parts_table(parts)
        if not table:
            continue

        if not isinstance(files, list):
            handle_error(f"'files' for category '{category}' must be a list.")
            continue

        for file in files:
            try:
                abs_path = os.path.abspath(file)
                if not abs_path.startswith(base_dir):
                    handle_error(f"File path outside allowed directory: {file}")
                    continue

                with open(abs_path, "r", encoding="utf-8") as f:
                    lines = f.read().splitlines()

                start_marker = f"<!-- {category} -->"
                end_marker = "<!-- AUTO-GENERATED END -->"

                if start_marker not in lines or end_marker not in lines:
                    handle_error(f"Missing markers in file: {file}")
                    continue

                start_idx = lines.index(start_marker) + 1
                end_idx = lines.index(end_marker, start_idx)

                new_lines = lines[:start_idx] + [table] + lines[end_idx:]

                with open(abs_path, "w", encoding="utf-8") as f:
                    f.write("\n".join(new_lines))

            except Exception as e:
                handle_error(f"Failed processing file '{file}': {e}")


if __name__ == "__main__":
    main()

    if error_messages:
        print(f"{len(error_messages)} error(s) occurred during execution:", file=sys.stderr)
        for i, msg in enumerate(error_messages, start=1):
            print(f"{i}. {msg}", file=sys.stderr)
        sys.exit(1)
