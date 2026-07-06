import json
from typing import Any

import pandas as pd

from app.core.logger import get_logger
from app.services.settings_service import get_settings

logger = get_logger(__name__)

_ARABIC_PIE_KEYWORDS = ("نسبة", "توزيع", "حصة", "نسبة مئوية", "pie", "share", "percentage", "proportion", "breakdown")


def _detect_chart_type_from_settings() -> str:
    try:
        settings = get_settings()
        return (settings.get("visualization") or {}).get("default_chart_type", "auto")
    except Exception:
        return "auto"


def _coerce_columns(df: pd.DataFrame) -> tuple[list[str], list[str], list[str]]:
    for column in df.columns:
        if df[column].dtype != "object":
            continue
        numeric = pd.to_numeric(df[column], errors="coerce")
        if numeric.notna().mean() >= 0.8:
            df[column] = numeric
            continue
        parsed = pd.to_datetime(df[column], errors="coerce")
        if parsed.notna().mean() >= 0.8:
            df[column] = parsed

    numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    datetime_cols = [c for c in df.columns if pd.api.types.is_datetime64_any_dtype(df[c])]
    categorical_cols = [c for c in df.columns if c not in numeric_cols and c not in datetime_cols]
    return numeric_cols, datetime_cols, categorical_cols


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

        numeric_cols, datetime_cols, categorical_cols = _coerce_columns(df)
        chart_type = _detect_chart_type_from_settings()

        fig = None
        x_col = ""
        y_col = ""
        normalized_question = question.lower()

        if chart_type != "auto":
            forced = _build_forced_chart(df, chart_type, numeric_cols, datetime_cols, categorical_cols)
            if forced:
                return forced
            chart_type = "auto"

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
            wants_pie = any(token in normalized_question for token in _ARABIC_PIE_KEYWORDS)
            if wants_pie and grouped[x_col].nunique() <= 8:
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


def _build_forced_chart(df, chart_type, numeric_cols, datetime_cols, categorical_cols):
    import plotly.express as px

    if chart_type == "line" and datetime_cols and numeric_cols:
        return {
            "library": "plotly", "chart_type": "line",
            "x": datetime_cols[0], "y": numeric_cols[0],
            "spec": json.loads(px.line(df.sort_values(datetime_cols[0]), x=datetime_cols[0], y=numeric_cols[0]).update_layout(template="plotly_white").to_json()),
        }

    if chart_type == "pie" and categorical_cols and numeric_cols:
        grouped = df.groupby(categorical_cols[0], dropna=False)[numeric_cols[0]].sum().reset_index()
        if grouped[categorical_cols[0]].nunique() > 15:
            grouped = grouped.sort_values(numeric_cols[0], ascending=False).head(15)
        return {
            "library": "plotly", "chart_type": "pie",
            "x": categorical_cols[0], "y": numeric_cols[0],
            "spec": json.loads(px.pie(grouped, names=categorical_cols[0], values=numeric_cols[0]).update_layout(template="plotly_white").to_json()),
        }

    if chart_type == "scatter" and len(numeric_cols) >= 2:
        return {
            "library": "plotly", "chart_type": "scatter",
            "x": numeric_cols[0], "y": numeric_cols[1],
            "spec": json.loads(px.scatter(df, x=numeric_cols[0], y=numeric_cols[1]).update_layout(template="plotly_white").to_json()),
        }

    if chart_type == "histogram" and len(numeric_cols) >= 1:
        return {
            "library": "plotly", "chart_type": "histogram",
            "x": "", "y": numeric_cols[0],
            "spec": json.loads(px.histogram(df, x=numeric_cols[0], nbins=30).update_layout(template="plotly_white").to_json()),
        }

    if chart_type == "bar" and categorical_cols and numeric_cols:
        grouped = df.groupby(categorical_cols[0], dropna=False)[numeric_cols[0]].sum().sort_values(ascending=False).head(20).reset_index()
        return {
            "library": "plotly", "chart_type": "bar",
            "x": categorical_cols[0], "y": numeric_cols[0],
            "spec": json.loads(px.bar(grouped, x=categorical_cols[0], y=numeric_cols[0]).update_layout(template="plotly_white").to_json()),
        }

    return None
