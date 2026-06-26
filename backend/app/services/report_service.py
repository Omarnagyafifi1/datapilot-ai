from datetime import datetime, timezone
from typing import Any


def build_report(document: dict[str, Any]) -> dict[str, Any]:
    question = document.get("question") or "Untitled analysis"
    sql = document.get("sql") or ""
    insights = document.get("insights") or []
    suggestions = document.get("suggestions") or []
    results = document.get("results") or []
    visualization = document.get("visualization") or {}
    generated_at = datetime.now(timezone.utc).isoformat()

    lines = [
        f"# {question}",
        "",
        f"Generated at: {generated_at}",
        "",
        "## SQL",
        "```sql",
        sql,
        "```",
        "",
        "## Overview",
        f"Rows returned: {len(results)}",
        f"Chart: {visualization.get('chart_type', 'none')}",
        "",
        "## Insights",
    ]

    if insights:
        for item in insights:
            if isinstance(item, dict):
                lines.append(f"- {item.get('ar') or item.get('en') or item}")
            else:
                lines.append(f"- {item}")
    else:
        lines.append("- No insights were generated.")

    lines.extend(["", "## Recommendations"])
    if suggestions:
        for item in suggestions:
            if isinstance(item, dict):
                lines.append(f"- {item.get('ar') or item.get('en') or item}")
            else:
                lines.append(f"- {item}")
    else:
        lines.append("- Ask a more specific follow-up question or filter by a time period.")

    lines.extend(["", "## Sample Results"])
    for row in results[:10]:
        lines.append(f"- {row}")

    markdown = "\n".join(lines)
    return {
        "title": str(question),
        "generated_at": generated_at,
        "markdown": markdown,
        "filename": "datapilot-report.md",
    }
