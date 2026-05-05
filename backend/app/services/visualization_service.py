import json
import pandas as pd
import plotly.express as px
from app.core.logger import get_logger

logger = get_logger(__name__)


def generate_visualization(query_results: list[dict], question: str = "") -> dict | None:
    """
    FR10: Takes raw query results and returns a Plotly chart spec dict,
    or None if no chart can be generated.
    Called by visualization_node() in graph.py.
    """
    if not query_results:
        return None

    try:
        df = pd.DataFrame(query_results)
        if df.empty:
            return None

        # --- Type coercion ---
        for col in df.columns:
            if df[col].dtype == "object":
                numeric = pd.to_numeric(df[col], errors="coerce")
                if numeric.notna().mean() >= 0.8:
                    df[col] = numeric
                    continue
                if any(tok in str(col).lower() for tok in ("date", "time", "timestamp")):
                    dt = pd.to_datetime(df[col], errors="coerce")
                    if dt.notna().mean() >= 0.8:
                        df[col] = dt

        numeric_cols  = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
        datetime_cols = [c for c in df.columns if pd.api.types.is_datetime64_any_dtype(df[c])]
        cat_cols      = [c for c in df.columns if c not in numeric_cols and c not in datetime_cols]

        fig        = None
        chart_type = ""
        x_col      = ""
        y_col      = ""

        q = question.lower()

        # --- Chart-type selection (question keywords first, then data shape) ---
        if datetime_cols and numeric_cols:
            x_col = datetime_cols[0]
            y_col = numeric_cols[0]
            fig = px.line(df.sort_values(x_col), x=x_col, y=y_col,
                          title=f"{y_col} over {x_col}")
            chart_type = "line"

        elif cat_cols and numeric_cols:
            x_col = cat_cols[0]
            y_col = numeric_cols[0]

            # Pie for proportion questions with few categories
            if any(w in q for w in ("proportion", "share", "%", "percentage", "breakdown")) \
                    and df[x_col].nunique() <= 7:
                fig = px.pie(df, names=x_col, values=y_col,
                             title=f"{y_col} breakdown by {x_col}")
                chart_type = "pie"
            else:
                grouped = (
                    df.groupby(x_col, dropna=False)[y_col]
                    .sum()
                    .sort_values(ascending=False)
                    .head(20)
                    .reset_index()
                )
                fig = px.bar(grouped, x=x_col, y=y_col,
                             title=f"{y_col} by {x_col}")
                chart_type = "bar"

        elif len(numeric_cols) >= 2:
            x_col = numeric_cols[0]
            y_col = numeric_cols[1]
            fig = px.scatter(df, x=x_col, y=y_col,
                             title=f"{y_col} vs {x_col}")
            chart_type = "scatter"

        elif len(numeric_cols) == 1:
            y_col = numeric_cols[0]
            fig = px.histogram(df, x=y_col,
                               nbins=min(30, max(10, len(df) // 10)),
                               title=f"Distribution of {y_col}")
            chart_type = "histogram"

        elif cat_cols:
            x_col = cat_cols[0]
            counts = (
                df[x_col].astype(str).fillna("N/A")
                .value_counts().head(20)
                .rename_axis(x_col).reset_index(name="count")
            )
            fig = px.bar(counts, x=x_col, y="count",
                         title=f"Top values of {x_col}")
            chart_type = "bar"
            y_col = "count"

        if fig is None:
            return None

        fig.update_layout(template="plotly_white")

        return {
            "library":    "plotly",
            "chart_type": chart_type,
            "x":          x_col,
            "y":          y_col,
            "spec":       json.loads(fig.to_json()),
        }

    except Exception as exc:
        logger.warning("visualization_service failed: %s", exc)
        return None