import json
from typing import Any

import pandas as pd

from app.core.logger import get_logger

logger = get_logger(__name__)


def generate_visualization(query_results: list[dict[str, Any]], question: str = "") -> dict[str, Any] | None:
    if not query_results:
        return None

    try:
        import plotly.express as px
    except Exception as exc:
        logger.warning("Visualization dependencies unavailable: %s", exc)
        return None

    try:
        df = pd.DataFrame(query_results)
        if df.empty:
            return None

        for column in df.columns:
            if df[column].dtype != "object":
                continue
            numeric = pd.to_numeric(df[column], errors="coerce")
            if numeric.notna().mean() >= 0.8:
                df[column] = numeric
                continue
            if any(token in str(column).lower() for token in ("date", "time", "timestamp")):
                parsed = pd.to_datetime(df[column], errors="coerce")
                if parsed.notna().mean() >= 0.8:
                    df[column] = parsed

        numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
        datetime_cols = [c for c in df.columns if pd.api.types.is_datetime64_any_dtype(df[c])]
        categorical_cols = [c for c in df.columns if c not in numeric_cols and c not in datetime_cols]

        fig = None
        chart_type = ""
        x_col = ""
        y_col = ""
        normalized_question = question.lower()

        if datetime_cols and numeric_cols:
            x_col = datetime_cols[0]
            y_col = numeric_cols[0]
            fig = px.line(df.sort_values(x_col), x=x_col, y=y_col, title=f"{y_col} over {x_col}")
            chart_type = "line"
        elif categorical_cols and numeric_cols:
            x_col = categorical_cols[0]
            y_col = numeric_cols[0]
            grouped = (
                df.groupby(x_col, dropna=False)[y_col]
                .sum()
                .sort_values(ascending=False)
                .head(20)
                .reset_index()
            )
            wants_share = any(token in normalized_question for token in ("share", "percentage", "proportion", "breakdown", "pie"))
            if wants_share and grouped[x_col].nunique() <= 8:
                fig = px.pie(grouped, names=x_col, values=y_col, title=f"{y_col} breakdown by {x_col}")
                chart_type = "pie"
            else:
                fig = px.bar(grouped, x=x_col, y=y_col, title=f"{y_col} by {x_col}")
                chart_type = "bar"
        elif len(numeric_cols) >= 2:
            x_col = numeric_cols[0]
            y_col = numeric_cols[1]
            fig = px.scatter(df, x=x_col, y=y_col, title=f"{y_col} vs {x_col}")
            chart_type = "scatter"
        elif len(numeric_cols) == 1:
            y_col = numeric_cols[0]
            fig = px.histogram(df, x=y_col, nbins=min(30, max(10, len(df) // 10)), title=f"Distribution of {y_col}")
            chart_type = "histogram"
        elif categorical_cols:
            x_col = categorical_cols[0]
            counts = (
                df[x_col]
                .astype(str)
                .fillna("N/A")
                .value_counts()
                .head(20)
                .rename_axis(x_col)
                .reset_index(name="count")
            )
            fig = px.bar(counts, x=x_col, y="count", title=f"Top values of {x_col}")
            chart_type = "bar"
            y_col = "count"

        if fig is None:
            return None

        fig.update_layout(template="plotly_white")
        return {
            "library": "plotly",
            "chart_type": chart_type,
            "x": x_col,
            "y": y_col,
            "spec": json.loads(fig.to_json()),
        }
    except Exception as exc:
        logger.warning("Visualization generation failed: %s", exc)
        return None
