"""Research Agent — searches arXiv, web, and blogs, then summarizes findings.

Usage:
    python3 research_agent.py "your research query" [--sources arxiv,web,blogs]
    python3 research_agent.py "GRPO reinforcement learning" --max 10
"""

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPTS_DIR = Path("~/Documents/twin-output/scripts").expanduser()
sys.path.insert(0, str(SCRIPTS_DIR))

from routing_logger import log_routing

ARXIV_SCRIPT = Path(
    "/Users/jasonniemi/.hermes/skills/research/arxiv/scripts/search_arxiv.py"
)
TWIN_OUTPUT_DIR = Path("~/Documents/twin-output").expanduser()
AGENT_LOG = TWIN_OUTPUT_DIR / "logs" / "agent-log.jsonl"
OUTPUT_DIR = TWIN_OUTPUT_DIR / "research"


def search_arxiv(query: str, max_results: int = 5) -> list:
    """Search arXiv papers using the helper script."""
    if not ARXIV_SCRIPT.exists():
        return [{"error": "arXiv script not found"}]

    try:
        result = subprocess.run(
            ["python3", str(ARXIV_SCRIPT), query, "--max", str(max_results)],
            capture_output=True, text=True, timeout=30
        )
        output = result.stdout.strip()
        if not output:
            return []
        # Handle rate limiting
        if "429" in output or "rate" in output.lower():
            return [{"error": "arXiv rate limited (429). Try again later."}]
        papers = []
        lines = output.split("\n")
        current = {}
        for line in lines:
            if line.startswith("Title:"):
                if current:
                    papers.append(current)
                current = {"title": line.replace("Title:", "").strip()}
            elif line.startswith("Authors:"):
                current["authors"] = line.replace("Authors:", "").strip()
            elif line.startswith("Published:"):
                current["published"] = line.replace("Published:", "").strip()
            elif line.startswith("Categories:"):
                current["categories"] = line.replace("Categories:", "").strip()
            elif line.startswith("Abstract:"):
                current["abstract"] = line.replace("Abstract:", "").strip()[:300]
            elif line.startswith("PDF:"):
                current["pdf_url"] = line.replace("PDF:", "").strip()
                papers.append(current)
                current = {}
        if current:
            papers.append(current)
        return papers
    except subprocess.TimeoutExpired:
        return [{"error": "arXiv search timed out"}]
    except Exception as e:
        return [{"error": str(e)}]


def search_web(query: str) -> list:
    """Search the web as a fallback. Prints instructions since we can't import web_search here."""
    # web_search is a Hermes tool, not a Python import. The orchestrator handles this.
    return [{"note": "Web search available via orchestrator delegation. Use --sources web from cron context."}]


def search_blogs(query: str) -> list:
    """Search tracked blogs for matching articles via blogwatcher-cli."""
    try:
        result = subprocess.run(
            ["blogwatcher-cli", "articles", "--all"],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode != 0:
            return []
        output = result.stdout.strip()
        lines = output.split("\n")
        matches = []
        for line in lines:
            if query.lower() in line.lower():
                matches.append({"article": line.strip()})
        return matches[:5]
    except FileNotFoundError:
        return [{"error": "blogwatcher-cli not installed"}]
    except Exception:
        return []


def save_report(query: str, arxiv_results: list, blog_results: list, tier: str) -> Path:
    """Save the research report to the output directory."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    slug = "".join(c if c.isalnum() or c in " -_" else "" for c in query[:40])
    slug = slug.replace(" ", "-").lower()
    path = OUTPUT_DIR / f"{slug}-research.md"

    lines = [f"# Research: {query}", ""]
    lines.append(f"**Generated:** {datetime.now(timezone.utc).isoformat()}")
    lines.append(f"**Tier:** {tier}")
    lines.append("")

    if arxiv_results:
        lines.append("## arXiv Papers")
        lines.append("")
        for i, paper in enumerate(arxiv_results, 1):
            if "error" in paper:
                lines.append(f"  Error: {paper['error']}")
                continue
            lines.append(f"### {i}. {paper.get('title', 'Untitled')}")
            lines.append(f"**Authors:** {paper.get('authors', 'Unknown')}")
            lines.append(f"**Published:** {paper.get('published', 'Unknown')}")
            lines.append(f"**Categories:** {paper.get('categories', 'N/A')}")
            lines.append(f"**Abstract:** {paper.get('abstract', 'N/A')[:200]}...")
            lines.append(f"**PDF:** {paper.get('pdf_url', 'N/A')}")
            lines.append("")
    else:
        lines.append("## arXiv Papers")
        lines.append("No results found.")
        lines.append("")

    if blog_results:
        lines.append("## Blog Mentions")
        lines.append("")
        for b in blog_results:
            if "error" in b:
                lines.append(f"  Blog search: {b['error']}")
            else:
                lines.append(f"- {b.get('article', 'Unknown')}")
        lines.append("")

    path.write_text("\n".join(lines))
    return path


def log_agent(query: str, status: str, arxiv_count: int, blog_count: int, tier: str, path: str):
    """Append to the shared agent log."""
    AGENT_LOG.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "agent": "research-agent",
        "action": "search",
        "query": query[:100],
        "arxiv_results": arxiv_count,
        "blog_results": blog_count,
        "tier": tier,
        "status": status,
        "output_path": path,
    }
    with open(AGENT_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Research Agent — search and summarize")
    parser.add_argument("query", help="Research query")
    parser.add_argument("--max", type=int, default=5, help="Max arXiv results")
    parser.add_argument("--sources", default="arxiv,web",
                        help="Comma-separated sources: arxiv,web,blogs")
    args = parser.parse_args()

    print(f"Research Agent: '{args.query}'")
    print(f"Sources: {args.sources}")
    print()

    # Classify — research queries are medium complexity
    from classify_task import classify_task
    routing = classify_task(f"Research: {args.query}")
    log_routing(f"research-{args.query[:20]}", f"Research: {args.query}",
                routing["tier"], routing["model"], routing["provider"],
                routing["complexity"])
    print(f"Routing: {routing['tier']} → {routing['model']}")
    print()

    sources = [s.strip() for s in args.sources.split(",")]
    arxiv_results = []
    blog_results = []

    if "arxiv" in sources:
        print("Searching arXiv...")
        arxiv_results = search_arxiv(args.query, args.max)
        print(f"  Found {len(arxiv_results)} paper(s)")
        for p in arxiv_results[:3]:
            if "title" in p:
                print(f"    - {p['title'][:70]}...")

    if "blogs" in sources:
        print("Searching blogs...")
        blog_results = search_blogs(args.query)
        print(f"  Found {len(blog_results)} result(s)")

    # Save report
    report_path = save_report(args.query, arxiv_results, blog_results, routing["tier"])
    print(f"\nReport saved: {report_path}")

    # Log
    log_agent(args.query, "completed", len(arxiv_results), len(blog_results),
              routing["tier"], str(report_path))

    # Summary
    print()
    print("=== RESEARCH AGENT REPORT ===")
    print(f"Query: {args.query}")
    print(f"Sources: {args.sources}")
    print(f"arXiv papers: {len(arxiv_results)}")
    print(f"Blog matches: {len(blog_results)}")
    print(f"Tier: {routing['tier']} ({routing['model']})")
    print(f"Output: {report_path}")


if __name__ == "__main__":
    main()