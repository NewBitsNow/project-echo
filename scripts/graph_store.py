"""Graph Store — read/write/query across 5 knowledge graphs.

The five graphs (Intent, Decision, Evidence, Operational, Trust) are stored as
YAML files under ~/Documents/twin-output/graphs/. Each graph is a list of entries
with a standard schema: id, type, timestamp, content, source, tags.

Usage:
    python3 graph_store.py list                         # List all graphs
    python3 graph_store.py show <graph>                  # Show entries in a graph
    python3 graph_store.py add <graph> <content>         # Add an entry
    python3 graph_store.py search <graph> <query>        # Search within a graph
    python3 graph_store.py import-adrs                   # Import ADRs from MEMORY.md
"""

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

GRAPHS_DIR = Path("~/Documents/twin-output/graphs").expanduser()

# Standard graph names
GRAPHS = ["intent", "decision", "evidence", "operational", "trust"]

# Default entries for each graph (empty templates)
DEFAULT_ENTRIES = {
    "intent": [],
    "decision": [],
    "evidence": [],
    "operational": [],
    "trust": [],
}


def _graph_path(name: str) -> Path:
    """Get the file path for a graph."""
    return GRAPHS_DIR / f"{name}.yaml"


def init_graphs():
    """Initialize all 5 graphs if they don't exist."""
    GRAPHS_DIR.mkdir(parents=True, exist_ok=True)
    for name in GRAPHS:
        path = _graph_path(name)
        if not path.exists():
            _write_graph(name, DEFAULT_ENTRIES[name])
            print(f"  Created: {path.name}")


def _read_graph(name: str) -> list:
    """Read all entries from a graph."""
    path = _graph_path(name)
    if not path.exists():
        return []
    import yaml
    with open(path) as f:
        data = yaml.safe_load(f) or []
    return data if isinstance(data, list) else []


def _write_graph(name: str, entries: list):
    """Write entries to a graph."""
    import yaml
    path = _graph_path(name)
    with open(path, "w") as f:
        yaml.dump(entries, f, default_flow_style=False, sort_keys=False)


def add_entry(graph: str, content: str, source: str = "manual",
              tags: list = None, entry_type: str = "note"):
    """Add a new entry to a graph."""
    entries = _read_graph(graph)
    entry = {
        "id": f"{graph}-{len(entries) + 1}-{datetime.now().strftime('%H%M%S')}",
        "type": entry_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "content": content,
        "source": source,
        "tags": tags or [],
    }
    entries.append(entry)
    _write_graph(graph, entries)
    return entry


def list_graphs() -> dict:
    """List all graphs with entry counts."""
    result = {}
    for name in GRAPHS:
        entries = _read_graph(name)
        result[name] = {
            "count": len(entries),
            "path": str(_graph_path(name)),
        }
    return result


def search_graph(graph: str, query: str) -> list:
    """Search within a graph for entries matching the query."""
    entries = _read_graph(graph)
    query_lower = query.lower()
    matches = []
    for entry in entries:
        if query_lower in entry.get("content", "").lower():
            matches.append(entry)
        elif any(query_lower in tag.lower() for tag in entry.get("tags", [])):
            matches.append(entry)
    return matches


def import_adrs_from_memory(memory_path: str = None) -> int:
    """Import ADRs from MEMORY.md into the decision graph."""
    if memory_path is None:
        memory_path = "/Volumes/4TB_SSD/FrameHead/MEMORY.md"

    path = Path(memory_path)
    if not path.exists():
        print(f"ERROR: MEMORY.md not found at {memory_path}")
        return 0

    content = path.read_text()

    # Extract ADR blocks
    adr_pattern = r"### ADR-(\d+):\s*(.*?)(?=\n### ADR-|\n## |$)"
    matches = re.findall(adr_pattern, content, re.DOTALL)

    imported = 0
    for adr_num, adr_body in matches:
        lines = adr_body.strip().split("\n")
        title = lines[0].strip() if lines else "Untitled"
        body = "\n".join(lines[1:]).strip() if len(lines) > 1 else ""

        # Extract date
        date_match = re.search(r"- Date:\s*(.*)", body)
        date_str = date_match.group(1).strip() if date_match else "unknown"

        # Extract file references
        file_match = re.search(r"- File:\s*(.*)", body)
        file_ref = file_match.group(1).strip() if file_match else ""

        entry = {
            "id": f"adr-{adr_num}",
            "type": "architecture-decision-record",
            "timestamp": f"{date_str}T00:00:00+00:00" if date_str != "unknown" else datetime.now(timezone.utc).isoformat(),
            "content": f"ADR-{adr_num}: {title}\n\n{body}",
            "source": "MEMORY.md",
            "tags": ["adr", f"adr-{adr_num}"],
            "file_ref": file_ref,
        }

        # Check if already imported
        existing = _read_graph("decision")
        if any(e.get("id") == f"adr-{adr_num}" for e in existing):
            continue

        existing.append(entry)
        _write_graph("decision", existing)
        imported += 1

    return imported


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Graph Store — knowledge graphs")
    sub = parser.add_subparsers(dest="command")

    # list
    sub.add_parser("list", help="List all graphs")

    # show
    show_p = sub.add_parser("show", help="Show entries in a graph")
    show_p.add_argument("graph", choices=GRAPHS, help="Graph name")

    # add
    add_p = sub.add_parser("add", help="Add an entry to a graph")
    add_p.add_argument("graph", choices=GRAPHS, help="Graph name")
    add_p.add_argument("content", help="Entry content")
    add_p.add_argument("--source", default="manual", help="Source of the entry")
    add_p.add_argument("--tags", default="", help="Comma-separated tags")

    # search
    search_p = sub.add_parser("search", help="Search within a graph")
    search_p.add_argument("graph", choices=GRAPHS, help="Graph name")
    search_p.add_argument("query", help="Search query")

    # init
    sub.add_parser("init", help="Initialize all 5 graphs")

    # import-adrs
    sub.add_parser("import-adrs", help="Import ADRs from MEMORY.md")

    args = parser.parse_args()

    if args.command == "list":
        graphs = list_graphs()
        print("=== Knowledge Graphs ===")
        for name, info in graphs.items():
            print(f"  {name}: {info['count']} entries ({info['path']})")

    elif args.command == "show":
        entries = _read_graph(args.graph)
        print(f"=== {args.graph.title()} Graph ({len(entries)} entries) ===")
        for entry in entries:
            print(f"\n  [{entry['id']}] {entry['type']}")
            print(f"      {entry['content'][:100]}...")
            print(f"      Source: {entry['source']} | Tags: {', '.join(entry.get('tags', []))}")

    elif args.command == "add":
        tags = [t.strip() for t in args.tags.split(",") if t.strip()]
        entry = add_entry(args.graph, args.content, args.source, tags)
        print(f"Added: {entry['id']} to {args.graph} graph")

    elif args.command == "search":
        matches = search_graph(args.graph, args.query)
        print(f"=== Found {len(matches)} match(es) in {args.graph} ===")
        for m in matches:
            print(f"\n  [{m['id']}] {m['content'][:120]}...")

    elif args.command == "init":
        print("Initializing graphs...")
        init_graphs()
        print("Done.")

    elif args.command == "import-adrs":
        imported = import_adrs_from_memory()
        print(f"Imported {imported} ADR(s) into decision graph.")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()