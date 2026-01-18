import math
import os
import sys
from typing import Any, List, Dict, Optional
import xml.sax.saxutils as sax
import yaml


# =========================
# Global Error & Warning Handler
# =========================

error_messages: List[str] = []
warning_messages: List[str] = []


def handle_error(message: str) -> None:
    """
    Centralised error handler.
    Append errors to a global list.
    """
    error_messages.append(message)


def handle_warning(message: str) -> None:
    """
    Centralised warning handler.
    Append warnings to a global list.
    """
    warning_messages.append(message)


# =========================
# SVG Rendering Logic
# =========================

def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def rgb_to_hex(rgb):
    return "#{:02X}{:02X}{:02X}".format(*rgb)


def interpolate_color(colors, value):
    """
    colors: list of (position, hex_color) tuples, positions in [0, 1]
            e.g. [(0.0, "#FF0000"), (0.5, "#00FF00"), (1.0, "#0000FF")]
    value: float in [0, 1]
    """

    if not 0 <= value <= 1:
        raise ValueError("Value must be between 0 and 1")

    # Ensure colors are sorted by position
    colors = sorted(colors, key=lambda x: x[0])

    # Clamp to endpoints
    if value <= colors[0][0]:
        return colors[0][1]
    if value >= colors[-1][0]:
        return colors[-1][1]

    # Find surrounding colors
    for (p1, c1), (p2, c2) in zip(colors, colors[1:]):
        if p1 <= value <= p2:
            t = (value - p1) / (p2 - p1)

            r1, g1, b1 = hex_to_rgb(c1)
            r2, g2, b2 = hex_to_rgb(c2)

            r = round(r1 + (r2 - r1) * t)
            g = round(g1 + (g2 - g1) * t)
            b = round(b1 + (b2 - b1) * t)

            return rgb_to_hex((r, g, b))


def compute_state_counters(section):
    """
    Compute counters for each state (except 0).
    A unit at state N counts as completed for all states < N.
    Returns dict: state -> (completed, total)
    """
    states = section.get("states", {})
    # collect unit values from all groups recursively
    unit_states = []
    total_units = 0

    def collect_units(node):
        nonlocal total_units
        if not node:
            return
        if isinstance(node, dict):
            if "units" in node:
                for _, val in node["units"].items():
                    unit_states.append(int(val))
                    total_units += 1
            for sub in node.get("subgroups", []):
                collect_units(sub)

    for grp in section.get("groups", []):
        collect_units(grp)

    counters = {}
    # states keys might be ints or strings; normalize them to ints
    state_keys = sorted([int(k) for k in states.keys()])
    for s in state_keys:
        if s == 0:
            continue
        completed = sum(1 for v in unit_states if v >= s)
        counters[s] = (completed, total_units)
    return counters, total_units


def generate_svg_from_lines(lines, out_path, svg_width, svg_height):
    """
    Interpret a list of command strings and write an SVG file.

    Commands supported (simple, extensible):
      - STYLE|<css-text>
      - TEXT|x|y|class|content
      - RECT|x|y|width|height|rx|ry|class
      - GROUP_OPEN|id|transform(optional)
      - GROUP_CLOSE
    Any unknown command is emitted verbatim as an SVG fragment.
    """
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    style_blocks = []
    body_elements = []

    for raw in lines:
        if not raw or not isinstance(raw, str):
            continue

        # split into up to 5 parts to keep content as a single piece
        parts = raw.split("|", 4)

        cmd = parts[0].strip().upper()

        if cmd == "STYLE":
            # whole CSS in parts[1] (or join remainder)
            css = parts[1] if len(parts) > 1 else ""
            style_blocks.append(css)
        elif cmd == "TEXT":
            # TEXT|x|y|class|content
            if len(parts) < 5:
                raise ValueError("TEXT command requires 4 arguments: x, y, class, content")
            _, x, y, cls, content = parts
            body_elements.append(f'<text x="{x}" y="{y}" class="{cls}">{sax.escape(content)}</text>')
        elif cmd == "RECT":
            # RECT|x|y|width|height|rx|ry|class  (we use split with max 8 fields if needed)
            rect_parts = raw.split("|", 8)
            if len(rect_parts) < 8:
                raise ValueError("RECT command requires 7 arguments: x,y,width,height,rx,ry,class")
            _, x, y, w, h, rx, ry, cls = rect_parts[:8]
            body_elements.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" ry="{ry}" class="{cls}" />')
        elif cmd == "GROUP_OPEN":
            # GROUP_OPEN|id|transform(optional)
            gid = parts[1] if len(parts) > 1 else ""
            transform = parts[2] if len(parts) > 2 else ""
            transform_attr = f' transform="{sax.escape(transform)}"' if transform else ""
            body_elements.append(f'<g id="{sax.escape(gid)}"{transform_attr}>')
        elif cmd == "GROUP_CLOSE":
            body_elements.append("</g>")
        else:
            # Unknown command: treat as raw svg fragment
            body_elements.append(raw)

    # Assemble final SVG
    svg_lines = []
    svg_lines.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{svg_width}" viewBox="0 0 {svg_width} {svg_height}">')
    if style_blocks:
        svg_lines.append("<style>")
        for css in style_blocks:
            svg_lines.append(css)
        svg_lines.append("</style>")
    svg_lines.extend(body_elements)
    svg_lines.append("</svg>")

    svg_content = "\n".join(svg_lines)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(svg_content)

    print(f"Wrote SVG to {out_path} (width {svg_width}, height {svg_height})")


def generate_grid_commands(
    group,
    origin_x,
    origin_y,
    cols=16,
    cell_size=14,
    gap=4,
    rx=2,
    ry=2,
    show_unit_ids=False,
    unit_order=None
):
    """
    Generate commands that draw a simple grid of square cells for the given group.

    Parameters:
      - group: dict containing 'units' (mapping unit_id -> integer state) and optionally 'total'
      - origin_x, origin_y: top-left coordinates where grid begins
      - cols: desired number of columns (will be clamped based on item count)
      - cell_size: side length of each square cell (px)
      - gap: spacing between cells (px)
      - rx, ry: corner radii for cells
      - show_unit_ids: if True adds a small TEXT label per cell with the unit id (for debugging)
      - unit_order: optional list to force ordering of unit ids (fallback: sorted keys)
      - unit_id_pattern: optional regex string (not validated here) — kept for compatibility

    Returns:
      - (commands_list, total_height)
        commands_list: list of command strings (RECT and optional TEXT)
        total_height: vertical space consumed by the grid (including gaps) — caller must add margin as needed.

    Notes:
      - Each cell RECT uses class "square state-{N}" where N is the unit's integer state (0..max_state).
      - If a unit is missing or its value is not an int, it's treated as 0.
      - The function does not attempt to compute or validate colors/styles.
    """
    # Label positioning for unit IDs (when debugging)
    LABEL_OFFSET_BELOW_CELL = 10

    cmds = []
    units_map = group.get("units", {}) or {}
    group_id = group.get("id", "group")

    # Determine number of cells
    if units_map:
        unit_ids = list(unit_order) if unit_order else sorted(units_map.keys())
        n_cells = len(unit_ids)
    else:
        # fallback: use group's declared total if no units listed
        n_cells = group.get("total", 0) or 0
        # create placeholder IDs so cells are drawn (but states default to 0)
        unit_ids = [f"{group_id}-{i+1:03d}" for i in range(n_cells)]

    if n_cells == 0:
        # nothing to draw
        return ([], 0)

    # Clamp columns: at most n_cells, at least 1
    cols = max(1, min(int(cols), n_cells))
    rows = math.ceil(n_cells / cols)

    # For each cell compute coordinates and emit RECT with class based on state
    x0 = origin_x
    y0 = origin_y

    # Open group wrapper
    cmds.append('GROUP_OPEN|grid|')

    # iterate and emit
    idx = 0
    for r in range(rows):
        for c in range(cols):
            if idx >= n_cells:
                break
            uid = unit_ids[idx]
            # get state value
            try:
                state_val = int(units_map.get(uid, 0))
            except Exception:
                state_val = 0
            cell_x = x0 + c * (cell_size + gap)
            cell_y = y0 + r * (cell_size + gap)
            # Emit rect command: RECT|x|y|w|h|rx|ry|class
            cmds.append(f'RECT|{cell_x}|{cell_y}|{cell_size}|{cell_size}|{rx}|{ry}|square state-{state_val}')
            if show_unit_ids:
                # small unit id labels centered below cell (debugging)
                label_x = cell_x + (cell_size / 2)
                label_y = cell_y + cell_size + LABEL_OFFSET_BELOW_CELL
                cmds.append(f'TEXT|{label_x}|{label_y}|body|{uid}')
            idx += 1

    # Close group wrapper
    cmds.append('GROUP_CLOSE|')

    total_height = rows * cell_size + (rows - 1) * gap
    return (cmds, total_height)


def render_section_svg(
    section,
    out_path,
    canvas_width=500,
    margin=24,
    show_title=False,
    title_gap=32,
    path_gap=24,
    # grid parameters (passed into generate_grid_commands)
    grid_cols=12,
    grid_cell_size=24,
    grid_gap=8,
    grid_rx=2,
    grid_ry=2,
    legend_square_size=16,
    legend_spacing=20,
    legend_padding_bottom=16,
):
    """
    Build a list of simple command strings and hand off to generate_svg_from_lines.
    This keeps layout logic separate from SVG serialization.
    """
    # Text baseline offset for vertical centering
    TEXT_BASELINE_OFFSET = 14
    # Spacing after grid sections
    GRID_POST_SPACING = 16
    # Pre-legend spacing
    LEGEND_PRE_SPACING = 16
    # Offset of legend square from text baseline
    LEGEND_SQUARE_BASELINE_OFFSET = 14
    # Horizontal offset of text from legend square
    LEGEND_TEXT_OFFSET = 8
    # Spacing after uncatalogued warning
    UNCATALOGUED_SPACING = 30
    # Gradient for state colors (Github contribution graph gradient)
    GRADIENT = [
        (0.00, "#161c23"),
        (0.25, "#0e4527"),
        (0.50, "#006e34"),
        (0.75, "#28a541"),
        (1.00, "#39d255"),
    ]

    # Normalise state keys
    states = section.get("states", {})
    state_keys = sorted([int(k) for k in states.keys()])

    # Cursor
    x = margin
    y = margin

    # Track right-most used x to compute width dynamically
    max_x = x

    # Padding to add on the right edge
    RIGHT_PADDING = margin

    AVG_CHAR_WIDTH = {
        "title": 11,    # bold 20px sans-serif
        "path": 9,     # 16px sans-serif
        "legend": 9,   # 16px sans-serif
        "body": 9,     # 16px sans-serif
    }

    def estimate_text_width(text, cls="path"):
        # crude estimation: number of characters * average character width
        # treat None gracefully
        if text is None:
            return 0
        return len(str(text)) * AVG_CHAR_WIDTH.get(cls, 8)

    def update_max_for_text(xpos, text, cls="path"):
        nonlocal max_x
        w = estimate_text_width(text, cls)
        max_x = max(max_x, xpos + w + RIGHT_PADDING)

    def update_max_for_rect(xpos, width):
        nonlocal max_x
        max_x = max(max_x, float(xpos) + float(width) + RIGHT_PADDING)

    # Prepare command lines list
    cmds = []

    # Centralised CSS (class definitions left intentionally unfilled for per-state colors)
    css_lines = [
        '.bg { fill: #0d1116; rx: 10px; ry: 10px; }',
        '.title { font: bold 20px sans-serif; fill: #fff; }',
        '.path { font: 16px sans-serif; fill: #fff; }',
        '.legend { font: 16px sans-serif; fill: #fff; }',
        '.body { font: 16px sans-serif; fill: #fff; }',
        '.square { rx: 2px; fill: none; }',
    ]
    for i, s in enumerate(state_keys):
        percent = i / (len(state_keys) - 1) if len(state_keys) > 1 else 0.5
        css_lines.append(f'.square.state-{s} {{ fill: {interpolate_color(GRADIENT, percent)}; }}')

    cmds.append("STYLE|" + "\n".join(css_lines))

    # Title
    if show_title:
        cmds.append(f'TEXT|{x}|{y+TEXT_BASELINE_OFFSET}|title|{section.get("title","Section")}')
        y += title_gap

    # helper: append_text and append_rect via commands
    def append_text_at(text, xpos, ypos, cls="path"):
        cmds.append(f'TEXT|{xpos}|{ypos+TEXT_BASELINE_OFFSET}|{cls}|{text}')

    def render_group(group, path):
        nonlocal y
        current_path = path + [group.get("label", group.get("id", ""))]
        # Leaf groups: have units
        if "units" in group and group["units"] is not None:
            header = "/".join(current_path)
            append_text_at(header, x, y, "path")
            y += path_gap  # spacing under header
            if group.get("total", 0) == 0:
                handle_warning(f"Group '{header}' has total=0; considered uncatalogued.")
                append_text_at("Units have not yet been catalogued for tracking progress.", x, y, "body")
                y += UNCATALOGUED_SPACING
                return

            render_grid_section(group)

        # Recurse into subgroups
        for sub in group.get("subgroups", []):
            render_group(sub, current_path)

    def render_grid_section(group):
        """Render a grid for the given group and advance y cursor."""
        nonlocal y
        grid_cmds, grid_height = generate_grid_commands(
            group=group,
            origin_x=x,
            origin_y=y,
            cols=grid_cols,
            cell_size=grid_cell_size,
            gap=grid_gap,
            rx=grid_rx,
            ry=grid_ry,
            show_unit_ids=False,
        )
        cmds.extend(grid_cmds)
        y += grid_height + GRID_POST_SPACING

    # Handle ungrouped sections
    if not section.get("groups"):
        units_map = section.get("units", {})
        if len(units_map) == 0:
            handle_warning(f"Section '{section.get('title','')}' has no units; considered uncatalogued.")
            append_text_at('Units have not yet been catalogued for tracking progress.', x, y, "body")
            y += UNCATALOGUED_SPACING
        else:
            # build a synthetic group for top-level units
            synthetic_group = {"id": "all", "label": "All", "units": units_map}
            render_grid_section(synthetic_group)
    else:
        # Render subgroups; top-level headers are omitted when they have subgroups (path-style used in leaves)
        for grp in section.get("groups", []):
            render_group(grp, [])

    # Legend: compute counters
    counters, total_units = compute_state_counters(section=section)

    legend_y = y + LEGEND_PRE_SPACING
    legend_x = x

    # Legend entries
    for s in state_keys:
        label = states.get(s, states.get(str(s), ""))
        sq_x = legend_x
        sq_y = legend_y
        sq_size = legend_square_size
        # square rect in legend
        cmds.append(f'RECT|{sq_x}|{sq_y-LEGEND_SQUARE_BASELINE_OFFSET}|{sq_size}|{sq_size}|2|2|square state-{s}')
        # label and optional counters
        if s == 0:
            text = f'{label}'
        else:
            completed, total = counters.get(s, (0, total_units))
            pct = (completed / total * 100) if total else 0.0
            unit_plural = section.get("unit", {}).get("plural", "units")
            text = f'{label} ({completed}/{total} {unit_plural}, {pct:.1f}%)'
        cmds.append(f'TEXT|{sq_x + sq_size + LEGEND_TEXT_OFFSET}|{sq_y}|legend|{text}')
        legend_y += legend_spacing

    final_height = legend_y + legend_padding_bottom

    cmds.insert(0, 'RECT|0|0|{0}|{1}|0|0|bg'.format(canvas_width, final_height))

    # Call helper to generate svg
    generate_svg_from_lines(cmds, out_path, svg_width=canvas_width, svg_height=final_height)


# =========================
# Interpretation Logic
# =========================

def interpret_sections(progress: Any) -> Optional[List[Dict[str, Any]]]:
    """
    Interpret the 'sections' format from progress.yaml.

    This version handles:
      - sections with 'groups' where groups contain 'subgroups' (original format)
      - groups that instead carry 'total' and 'units' directly (treated as a single subgroup)
      - sections that have top-level 'units' and no 'groups' (treated as section-level units)

    Returns a list of section dictionaries or None on fatal input problems.
    Non-fatal issues are recorded via handle_error and processing continues where possible.
    """
    if not isinstance(progress, dict):
        handle_error("Top-level progress structure must be a mapping/dictionary.")
        return None

    sections_raw = progress.get("sections")
    if sections_raw is None:
        handle_error("Missing top-level 'sections' key in progress.yaml.")
        return None

    if not isinstance(sections_raw, dict):
        handle_error("'sections' must be a mapping/dictionary.")
        return None

    sections_out: List[Dict[str, Any]] = []

    for section_key, sec in sections_raw.items():
        if not isinstance(sec, dict):
            handle_error(f"Section '{section_key}' must be an object/dictionary.")
            continue

        title = sec.get("title", "")
        unit = sec.get("unit")
        states = sec.get("states", {})
        final_state = sec.get("final_state")
        groups = sec.get("groups", None)   # may be absent
        section_units = sec.get("units", None)  # may be present at section-level

        # Validate unit
        if not isinstance(unit, dict) or "name" not in unit:
            if unit is None:
                # allowed - some sections might omit unit (but we warn)
                handle_error(f"Section '{section_key}': missing 'unit' mapping; using empty placeholders.")
                unit = {"name": "", "plural": ""}
            else:
                handle_error(f"Section '{section_key}': 'unit' must be a mapping with at least 'name'. Normalising.")
                unit = {
                    "name": unit.get("name", "") if isinstance(unit, dict) else "",
                    "plural": unit.get("plural", "") if isinstance(unit, dict) else ""
                }

        # Normalize states: convert keys to ints where possible
        normalized_states: Dict[int, str] = {}
        if isinstance(states, dict):
            for k, v in states.items():
                # allow keys that are int or strings representing ints
                try:
                    key_int = int(k) if not isinstance(k, int) else k
                except Exception:
                    handle_error(f"Section '{section_key}': state key '{k}' is not an integer; skipping.")
                    continue
                if not isinstance(v, str):
                    handle_error(f"Section '{section_key}': state value for '{k}' should be a string; casting.")
                    v = str(v)
                normalized_states[key_int] = v
        else:
            handle_error(f"Section '{section_key}': 'states' must be a mapping; defaulting to empty.")
            normalized_states = {}

        # Validate final_state
        if final_state is not None:
            try:
                final_state = int(final_state)
            except Exception:
                handle_error(f"Section '{section_key}': 'final_state' must be an integer. Setting to None.")
                final_state = None

        # Process groups (if present). Some sections may instead use top-level 'units'.
        groups_out: List[Dict[str, Any]] = []

        if groups is None:
            # No groups provided. If section-level units exist, keep them in output.
            if section_units is not None and not isinstance(section_units, dict):
                handle_error(f"Section '{section_key}': top-level 'units' must be a mapping; using empty dict.")
                section_units = {}
        else:
            if not isinstance(groups, list):
                handle_error(f"Section '{section_key}': 'groups' must be a list.")
                groups = []

            if len(groups) == 0:
                handle_warning(f"Section '{section_key}': 'groups' is empty.")
                pass

            for gi, group in enumerate(groups):
                if not isinstance(group, dict):
                    handle_error(f"Section '{section_key}': group at index {gi} must be a mapping; skipping.")
                    continue

                gid = group.get("id")
                glabel = group.get("label", "")
                g_subgroups = group.get("subgroups", None)
                g_total = group.get("total", None)
                g_units = group.get("units", None)

                if gid is None:
                    handle_error(f"Section '{section_key}': group at index {gi} missing 'id'; skipping.")
                    continue

                # Case A: group contains explicit 'subgroups' list -> process as before
                if g_subgroups is not None:
                    if not isinstance(g_subgroups, list):
                        handle_error(f"Section '{section_key}', group '{gid}': 'subgroups' must be a list.")
                        g_subgroups = []

                    subgroups_out: List[Dict[str, Any]] = []
                    for si, sg in enumerate(g_subgroups):
                        if not isinstance(sg, dict):
                            handle_error(f"Section '{section_key}', group '{gid}': subgroup at index {si} invalid; skipping.")
                            continue

                        sid = sg.get("id")
                        slabel = sg.get("label", "")
                        total = sg.get("total")
                        units = sg.get("units", {})

                        if sid is None:
                            handle_error(f"Section '{section_key}', group '{gid}': subgroup at index {si} missing 'id'; skipping.")
                            continue

                        # Validate total
                        if total is None:
                            handle_warning(f"Section '{section_key}', group '{gid}', subgroup '{sid}': missing 'total'. Setting to 0.")
                            total = 0
                        else:
                            try:
                                total = int(total)
                            except Exception:
                                handle_error(f"Section '{section_key}', group '{gid}', subgroup '{sid}': 'total' not an integer; setting to 0.")
                                total = 0

                        if not isinstance(units, dict):
                            handle_error(f"Section '{section_key}', group '{gid}', subgroup '{sid}': 'units' must be a mapping; using empty dict.")
                            units = {}

                        subgroups_out.append({
                            "id": sid,
                            "label": slabel,
                            "total": total,
                            "units": units
                        })

                    groups_out.append({
                        "id": gid,
                        "label": glabel,
                        "subgroups": subgroups_out
                    })
                else:
                    # Case B: group does NOT have 'subgroups' — treat group itself as a single subgroup
                    # Accept group-level 'total' and 'units' or default them
                    if g_total is None:
                        # If total missing, warn and set 0
                        handle_warning(f"Section '{section_key}', group '{gid}': missing 'total'. Setting to 0.")
                        g_total_val = 0
                    else:
                        try:
                            g_total_val = int(g_total)
                        except Exception:
                            handle_error(f"Section '{section_key}', group '{gid}': 'total' not an integer; setting to 0.")
                            g_total_val = 0

                    if g_units is None:
                        g_units_val: Dict[str, Any] = {}
                    elif not isinstance(g_units, dict):
                        handle_error(f"Section '{section_key}', group '{gid}': 'units' must be a mapping; using empty dict.")
                        g_units_val = {}
                    else:
                        g_units_val = g_units

                    groups_out.append({
                        "id": gid,
                        "label": glabel,
                        "total": g_total_val,
                        "units": g_units_val
                    })

        # Build section output. Include top-level 'units' if present in the source.
        section_entry: Dict[str, Any] = {
            "id": section_key,
            "title": title,
            "unit": {"name": unit.get("name", ""), "plural": unit.get("plural", "")},
            "states": normalized_states,
            "final_state": final_state,
            "groups": groups_out
        }
        if section_units is not None:
            # include the raw top-level units mapping if present in the YAML
            section_entry["units"] = section_units if isinstance(section_units, dict) else {}

            if len(section_entry["units"].keys()) == 0:
                handle_warning(f"Section '{section_key}': top-level 'units' is empty.")

        sections_out.append(section_entry)

    return sections_out


# =========================
# Main Logic
# =========================

def main() -> None:
    try:
        with open("progress.yaml", encoding="utf-8") as f:
            progress = yaml.safe_load(f)
    except FileNotFoundError:
        handle_error("progress.yaml not found in current directory.")
        progress = None
    except Exception as e:
        handle_error(f"Failed to load progress.yaml: {e}")
        progress = None

    if progress is None:
        return

    sections = interpret_sections(progress)
    if sections is None:
        return

    for section in sections:
        section_id = section.get("id", "unknown")
        out_svg_path = os.path.join("progress", f"{section_id}.svg")
        render_section_svg(section, out_svg_path)


if __name__ == "__main__":
    main()

    if warning_messages:
        print(
            f"\n{len(warning_messages)} warning{'s' if len(warning_messages) != 1 else ''} occurred during execution:",
            file=sys.stderr,
        )
        for i, msg in enumerate(warning_messages, start=1):
            print(f"{i}. {msg}", file=sys.stderr)

    if error_messages:
        print(
            f"\n{len(error_messages)} error{'s' if len(error_messages) != 1 else ''} occurred during execution:",
            file=sys.stderr,
        )
        for i, msg in enumerate(error_messages, start=1):
            print(f"{i}. {msg}", file=sys.stderr)
        sys.exit(1)
