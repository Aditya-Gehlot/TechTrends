"""Streamlit operations dashboard for TechTrends."""
from __future__ import annotations

import os
import time
from typing import Any, Dict
from urllib.parse import quote

import pandas as pd
import plotly.express as px
import requests
import streamlit as st

DEFAULT_API_URL = os.environ.get("API_URL", "http://127.0.0.1:8001")


def _fallback_url(url: str) -> str | None:
    if "8001" in url:
        return url.replace("8001", "8000")
    if "8000" in url:
        return url.replace("8000", "8001")
    return None


def api_request(method: str, path: str, **kwargs):
    url = f"{st.session_state.api_url}{path}"
    try:
        response = requests.request(method, url, timeout=kwargs.pop("timeout", 15), **kwargs)
        response.raise_for_status()
        return response.json()
    except Exception:
        fallback = _fallback_url(st.session_state.api_url)
        if fallback:
            response = requests.request(method, f"{fallback}{path}", timeout=15, **kwargs)
            response.raise_for_status()
            st.session_state.api_url = fallback
            return response.json()
        raise


def api_get(path: str, timeout: int = 15):
    return api_request("GET", path, timeout=timeout)


def api_post(path: str, payload: Dict[str, Any], timeout: int = 15):
    return api_request("POST", path, json=payload, timeout=timeout)


def rerun() -> None:
    if hasattr(st, "rerun"):
        st.rerun()
    else:
        st.experimental_rerun()


def value(value_: Any, default: str = "-") -> str:
    if value_ is None or value_ == "":
        return default
    if isinstance(value_, float):
        return f"{value_:,.4f}"
    if isinstance(value_, int):
        return f"{value_:,}"
    return str(value_)


def percent(value_: Any) -> str:
    try:
        return f"{float(value_) * 100:.2f}%"
    except Exception:
        return "-"


def metric_cards(items: list[tuple[str, Any]], columns: int = 4) -> None:
    cols = st.columns(columns)
    for idx, (label, item_value) in enumerate(items):
        cols[idx % columns].metric(label, value(item_value))


def status_color(status: str) -> str:
    return {
        "Pending": "#6b7280",
        "Running": "#2563eb",
        "Completed": "#16a34a",
        "Failed": "#dc2626",
        "Warning": "#f97316",
    }.get(status, "#6b7280")


def stage_table(run: Dict[str, Any]) -> pd.DataFrame:
    rows = []
    for stage in run.get("stages", []):
        rows.append(
            {
                "Stage": stage.get("name"),
                "Status": stage.get("status"),
                "Progress": stage.get("progress"),
                "Start": stage.get("start_time"),
                "End": stage.get("end_time"),
                "Duration": stage.get("duration_seconds"),
                "Records": stage.get("records_processed"),
                "Inserted": stage.get("records_inserted"),
                "Rejected": stage.get("records_rejected"),
                "Duplicates": stage.get("duplicates_removed"),
                "Missing": stage.get("missing_values_found"),
                "Outliers": stage.get("outliers_detected"),
                "Input shape": stage.get("input_shape"),
                "Output shape": stage.get("output_shape"),
                "Error": stage.get("error_details"),
            }
        )
    return pd.DataFrame(rows)


def render_stage_cards(run: Dict[str, Any]) -> None:
    for stage in run.get("stages", []):
        color = status_color(stage.get("status"))
        badge_background = {
            "Pending": "#e5e7eb",
            "Running": "#dbeafe",
            "Completed": "#dcfce7",
            "Failed": "#fee2e2",
            "Warning": "#ffedd5",
        }.get(stage.get("status"), "#e5e7eb")
        st.markdown(
            f"""
            <div style="border:1px solid #e5e7eb;border-left:5px solid {color};border-radius:6px;padding:10px 12px;margin-bottom:8px;background:#fff;">
              <div style="display:flex;justify-content:space-between;gap:12px;">
                <span style="color:#111827;font-weight:700;">{stage.get('name')}</span>
                <span style="color:{color};background:{badge_background};font-weight:700;padding:2px 8px;border-radius:999px;">
                  {stage.get('status')}
                </span>
              </div>
              <div style="font-size:0.88rem;color:#374151;margin-top:4px;">
                {value(stage.get('progress'))}% | records {value(stage.get('records_processed'))} | duration {value(stage.get('duration_seconds'))}s
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_run_detail(run: Dict[str, Any]) -> None:
    top_metrics = [
        ("Status", run.get("status")),
        ("Progress", f"{int(run.get('overall_progress', 0) or 0)}%"),
        ("Records processed", run.get("records_processed")),
        ("Duration seconds", run.get("duration_seconds")),
        ("Features created", run.get("features_created")),
        ("Model score", run.get("model_score")),
        ("Triggered by", run.get("triggered_by")),
        ("Trigger type", run.get("trigger_type")),
    ]
    metric_cards(top_metrics, columns=4)

    meta_left, meta_right = st.columns([1.2, 1.8])
    with meta_left:
        st.markdown("**Run Metadata**")
        meta_rows = [
            {"Field": "Run ID", "Value": run.get("run_id")},
            {"Field": "Started", "Value": run.get("start_time")},
            {"Field": "Ended", "Value": run.get("end_time")},
            {"Field": "Current stage", "Value": run.get("current_stage")},
            {"Field": "Error", "Value": run.get("error_message")},
        ]
        st.dataframe(pd.DataFrame(meta_rows), use_container_width=True, hide_index=True)
    with meta_right:
        parameters = run.get("parameters") or {}
        if parameters:
            st.markdown("**Run Parameters**")
            st.dataframe(
                pd.DataFrame(
                    [{"Parameter": key, "Value": value(item)} for key, item in parameters.items()]
                ),
                use_container_width=True,
                hide_index=True,
            )

    stages = run.get("stages", [])
    if stages:
        st.markdown("**Stage Timeline**")
        render_stage_cards(run)

        stage_df = stage_table(run)
        if not stage_df.empty:
            chart_df = stage_df[["Stage", "Duration", "Progress", "Status"]].copy()
            chart_df["Duration"] = pd.to_numeric(chart_df["Duration"], errors="coerce").fillna(0.0)
            st.plotly_chart(
                px.bar(
                    chart_df,
                    x="Stage",
                    y="Duration",
                    color="Status",
                    title="Stage duration by run",
                    color_discrete_map={
                        "Pending": "#6b7280",
                        "Running": "#2563eb",
                        "Completed": "#16a34a",
                        "Failed": "#dc2626",
                        "Warning": "#f97316",
                    },
                ),
                use_container_width=True,
            )
            st.dataframe(stage_df, use_container_width=True, hide_index=True)

    lower_left, lower_right = st.columns(2)
    with lower_left:
        dims = run.get("dataset_dimensions") or {}
        if dims:
            st.markdown("**Dataset Dimensions**")
            st.dataframe(
                pd.DataFrame([{"Layer": key, "Shape": value(item)} for key, item in dims.items()]),
                use_container_width=True,
                hide_index=True,
            )

        metrics_payload = run.get("metrics") or {}
        if metrics_payload:
            st.markdown("**Pipeline Metrics**")
            st.dataframe(
                pd.DataFrame([{"Metric": key, "Value": value(item)} for key, item in metrics_payload.items()]),
                use_container_width=True,
                hide_index=True,
            )

    with lower_right:
        feature_tracking = run.get("feature_tracking") or {}
        if feature_tracking:
            st.markdown("**Feature Tracking**")
            st.dataframe(
                pd.DataFrame([{"Metric": key, "Value": value(item)} for key, item in feature_tracking.items()]),
                use_container_width=True,
                hide_index=True,
            )

        ml_tracking = run.get("ml_tracking") or {}
        if ml_tracking:
            st.markdown("**ML Tracking**")
            st.dataframe(
                pd.DataFrame([{"Metric": key, "Value": value(item)} for key, item in ml_tracking.items()]),
                use_container_width=True,
                hide_index=True,
            )

    logs = pd.DataFrame(run.get("logs", []))
    if not logs.empty:
        st.markdown("**Run Logs**")
        st.dataframe(logs, use_container_width=True, hide_index=True)


def latest_run_or_status():
    try:
        status_payload = api_get("/pipeline/status")
        return status_payload.get("run"), status_payload.get("status")
    except Exception:
        return None, "Unavailable"


if "api_url" not in st.session_state:
    st.session_state.api_url = DEFAULT_API_URL

st.set_page_config(page_title="TechTrends Control Center", layout="wide")
st.title("TechTrends Control Center")

with st.sidebar:
    st.header("Connection")
    st.session_state.api_url = st.text_input("API URL", value=st.session_state.api_url)
    auto_refresh = st.toggle("Auto refresh while running", value=True)
    if st.button("Refresh"):
        rerun()

current_run, api_status = latest_run_or_status()
running = bool(current_run and current_run.get("status") == "Running")

try:
    metrics_payload = api_get("/pipeline/metrics")
except Exception:
    metrics_payload = {"metrics": {}, "feature_tracking": {}, "ml_tracking": {}, "dataset_dimensions": {}}

metrics = metrics_payload.get("metrics", {})
feature_tracking = metrics_payload.get("feature_tracking", {})
ml_tracking = metrics_payload.get("ml_tracking", {})
dataset_dimensions = metrics_payload.get("dataset_dimensions", {})

tabs = st.tabs([
    "Pipeline Control",
    "Live Insights",
    "Feature Layer",
    "ML & Predictions",
    "Run History",
    "Market Trends",
])

with tabs[0]:
    st.subheader("Pipeline Control Center")
    progress = int(current_run.get("overall_progress", 0)) if current_run else 0
    metric_cards(
        [
            ("Status", current_run.get("status") if current_run else api_status),
            ("Overall progress", f"{progress}%"),
            ("Current stage", current_run.get("current_stage") if current_run else None),
            ("Runtime seconds", current_run.get("duration_seconds") if current_run else None),
        ],
        columns=4,
    )
    st.progress(progress / 100)

    with st.form("pipeline_run_form"):
        left, mid, right = st.columns(3)
        clean = left.checkbox("Clean derived outputs", value=True)
        regenerate_data = mid.checkbox("Regenerate realistic sample data", value=False)
        confirmed = right.checkbox("Confirm full pipeline run", value=True)
        min_rows = left.number_input("Minimum generated rows", min_value=10000, max_value=1000000, value=100000, step=10000)
        scale = mid.number_input("Generation scale", min_value=1.0, max_value=10.0, value=1.0, step=0.5)
        seed = right.number_input("Generation seed", min_value=1, max_value=99999999, value=20260526, step=1)
        submitted = st.form_submit_button("Run Full Pipeline", disabled=running)

    if submitted:
        if not confirmed:
            st.warning("Confirm the full pipeline run before starting.")
        else:
            payload = {
                "trigger_type": "Full",
                "triggered_by": "streamlit-ui",
                "clean": clean,
                "regenerate_data": regenerate_data,
                "min_rows": int(min_rows),
                "scale": float(scale),
                "seed": int(seed),
                "formats": ["csv", "parquet", "ndjson", "es"],
            }
            try:
                result = api_post("/pipeline/run", payload)
                st.success(f"Pipeline started: {result.get('run_id')}")
                time.sleep(1)
                rerun()
            except requests.HTTPError as exc:
                st.error(exc.response.text)
            except Exception as exc:
                st.error(f"Could not start pipeline: {exc}")

    if current_run:
        st.subheader("Stage Progress")
        render_stage_cards(current_run)
        st.dataframe(stage_table(current_run), use_container_width=True, hide_index=True)
        logs = pd.DataFrame(current_run.get("logs", [])[-50:])
        if not logs.empty:
            st.subheader("Live Logs")
            st.dataframe(logs, use_container_width=True, hide_index=True)

with tabs[1]:
    st.subheader("Live Pipeline Insights")
    metric_cards(
        [
            ("Progress", f"{metrics.get('overall_pipeline_progress', 0)}%"),
            ("Current stage", metrics.get("current_running_stage")),
            ("Records processed", metrics.get("total_records_processed")),
            ("Records inserted", metrics.get("total_records_inserted")),
            ("Records rejected", metrics.get("total_records_rejected")),
            ("Duplicates removed", metrics.get("total_duplicate_records_removed")),
            ("Missing values found", metrics.get("total_missing_values_found")),
            ("Missing values handled", metrics.get("total_missing_values_handled")),
            ("Outliers detected", metrics.get("total_outliers_detected")),
            ("Features created", metrics.get("total_features_created")),
            ("Features selected", metrics.get("total_features_selected_applied")),
            ("Prediction count", metrics.get("prediction_output_count")),
        ],
        columns=4,
    )
    dim_rows = [{"Layer": k, "Shape": v} for k, v in dataset_dimensions.items()]
    if dim_rows:
        st.subheader("Dataset Dimensions")
        st.dataframe(pd.DataFrame(dim_rows), use_container_width=True, hide_index=True)

    totals = pd.DataFrame(
        [
            {"Metric": "Processed", "Value": metrics.get("total_records_processed", 0)},
            {"Metric": "Inserted", "Value": metrics.get("total_records_inserted", 0)},
            {"Metric": "Rejected", "Value": metrics.get("total_records_rejected", 0)},
            {"Metric": "Duplicates", "Value": metrics.get("total_duplicate_records_removed", 0)},
            {"Metric": "Missing handled", "Value": metrics.get("total_missing_values_handled", 0)},
            {"Metric": "Outliers", "Value": metrics.get("total_outliers_detected", 0)},
        ]
    )
    fig = px.bar(totals, x="Metric", y="Value", title="Pipeline data quality counters")
    st.plotly_chart(fig, use_container_width=True)

with tabs[2]:
    st.subheader("Feature Engineering Tracking")
    metric_cards(
        [
            ("Original columns", feature_tracking.get("original_column_count")),
            ("New features", feature_tracking.get("new_feature_count")),
            ("Features used", feature_tracking.get("features_used_count")),
            ("Features dropped", feature_tracking.get("features_dropped_count")),
        ],
        columns=4,
    )
    created = feature_tracking.get("created_features", [])
    used = feature_tracking.get("features_used", [])
    dropped = feature_tracking.get("features_dropped", [])
    transformations = feature_tracking.get("transformation_summary", {})
    correlations = feature_tracking.get("correlation_insights", [])

    f1, f2 = st.columns(2)
    with f1:
        st.markdown("**Created Features**")
        st.dataframe(pd.DataFrame({"feature": created}), use_container_width=True, hide_index=True)
    with f2:
        st.markdown("**Features Used In Model**")
        st.dataframe(pd.DataFrame({"feature": used}), use_container_width=True, hide_index=True)

    if dropped:
        st.markdown("**Dropped Features**")
        st.dataframe(pd.DataFrame(dropped), use_container_width=True, hide_index=True)

    if transformations:
        rows = []
        for transform, names in transformations.items():
            rows.append({"Transformation": transform, "Feature count": len(names), "Examples": ", ".join(names[:8])})
        st.markdown("**Feature Transformations Applied**")
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    if correlations:
        corr_df = pd.DataFrame(correlations)
        st.plotly_chart(px.bar(corr_df.head(15), x="correlation", y="feature", orientation="h", title="Top correlations to future growth"), use_container_width=True)
        st.dataframe(corr_df, use_container_width=True, hide_index=True)

    nulls = feature_tracking.get("null_percentage_per_feature", {})
    dtypes = feature_tracking.get("data_type_per_feature", {})
    if nulls or dtypes:
        profile_df = pd.DataFrame(
            [
                {"feature": feature, "null_percent": nulls.get(feature), "dtype": dtypes.get(feature)}
                for feature in sorted(set(nulls) | set(dtypes))
            ]
        )
        st.markdown("**Feature Profile**")
        st.dataframe(profile_df, use_container_width=True, hide_index=True)

with tabs[3]:
    st.subheader("ML Tracking")
    metric_cards(
        [
            ("Model", ml_tracking.get("model_used")),
            ("Target", ml_tracking.get("target_variable")),
            ("Training rows", ml_tracking.get("training_dataset_size")),
            ("Testing rows", ml_tracking.get("testing_dataset_size")),
            ("Accuracy", ml_tracking.get("accuracy")),
            ("MAE", ml_tracking.get("mae")),
            ("R2", ml_tracking.get("r2")),
            ("Predictions", ml_tracking.get("prediction_count")),
        ],
        columns=4,
    )
    st.write("Model file:", ml_tracking.get("model_file_path") or "-")
    st.write("Last trained:", ml_tracking.get("last_trained_date") or "-")
    st.write("Improved vs previous:", value(ml_tracking.get("model_improved_vs_previous_run")))

    try:
        model_payload = api_get("/models/latest")
        importances = model_payload.get("feature_importances") or {}
    except Exception:
        importances = {}
    if importances:
        fi_df = pd.DataFrame([{"feature": k, "importance": v} for k, v in importances.items()])
        fi_df = fi_df.sort_values("importance", ascending=False).head(20)
        st.plotly_chart(px.bar(fi_df, x="importance", y="feature", orientation="h", title="Model feature importance"), use_container_width=True)

    try:
        predictions = api_get("/pipeline/predictions/latest").get("predictions", [])
    except Exception:
        predictions = []
    if predictions:
        pred_df = pd.DataFrame(predictions)
        st.subheader("Latest Predictions")
        st.dataframe(pred_df, use_container_width=True, hide_index=True)
        if {"tech", "predicted_growth"}.issubset(pred_df.columns):
            st.plotly_chart(px.bar(pred_df.sort_values("predicted_growth", ascending=False).head(20), x="tech", y="predicted_growth", color="trend", title="Predicted growth by technology"), use_container_width=True)

with tabs[4]:
    st.subheader("Pipeline Run History")
    try:
        history = api_get("/pipeline/runs?limit=50").get("runs", [])
    except Exception:
        history = []
    history_df = pd.DataFrame(history)
    if history_df.empty:
        st.info("No pipeline runs recorded yet.")
    else:
        st.dataframe(history_df, use_container_width=True, hide_index=True)
        selected_run = st.selectbox("View details", options=history_df["run_id"].tolist())
        if selected_run:
            detail = api_get(f"/pipeline/runs/{selected_run}")
            render_run_detail(detail)

with tabs[5]:
    st.subheader("Market Intelligence")
    try:
        summary = api_get("/sources/summary")
        dataset_summary = summary.get("dataset", {})
        feature_summary = summary.get("features", {})
        model_summary = summary.get("model", {})
        metric_cards(
            [
                ("Sample rows", dataset_summary.get("total_rows")),
                ("Feature rows", feature_summary.get("feature_rows")),
                ("Technologies", feature_summary.get("technologies")),
                ("Model horizon", model_summary.get("horizon_days")),
            ],
            columns=4,
        )
    except Exception:
        st.warning("Source summary is unavailable.")

    try:
        context = api_get("/sources/market-context").get("context")
        if context:
            st.markdown("**Market Context Sources**")
            st.dataframe(pd.DataFrame(context.get("sources", [])), use_container_width=True, hide_index=True)
    except Exception:
        pass

    limit = st.slider("Top technologies", 5, 50, 10)
    top_df = pd.DataFrame()
    try:
        top = api_get(f"/trends/top?limit={limit}").get("top", [])
        top_df = pd.DataFrame(top)
        if not top_df.empty:
            st.plotly_chart(px.bar(top_df, x="tech", y="score", color="momentum", hover_data=["date", "mentions_7d_mean", "trend_score_avg"], title="Top technologies by popularity score"), use_container_width=True)
            st.dataframe(top_df, use_container_width=True, hide_index=True)
    except Exception as exc:
        st.error(f"Could not load top trends: {exc}")

    options = top_df["tech"].tolist() if not top_df.empty and "tech" in top_df.columns else []
    selected = st.selectbox("Technology", options=options) if options else ""
    typed = st.text_input("Technology name", value="" if selected else "AI Agents")
    tech = typed.strip() or selected
    if tech:
        encoded = quote(tech, safe="")
        try:
            forecast = api_get(f"/forecast/{encoded}")
            c1, c2, c3 = st.columns(3)
            c1.metric("Trend", forecast.get("trend"))
            c2.metric("Predicted growth", percent(forecast.get("predicted_growth")))
            c3.metric("Confidence", percent(forecast.get("confidence")))
            history = api_get(f"/trends/history/{encoded}?limit=180").get("history", [])
            hist_df = pd.DataFrame(history)
            if not hist_df.empty:
                hist_df["date"] = pd.to_datetime(hist_df["date"])
                st.plotly_chart(px.line(hist_df, x="date", y=["technology_popularity_score", "ecosystem_momentum_score"], title=f"{tech} history"), use_container_width=True)
        except Exception as exc:
            st.error(f"Could not load forecast for {tech}: {exc}")

if auto_refresh and running:
    time.sleep(3)
    rerun()
