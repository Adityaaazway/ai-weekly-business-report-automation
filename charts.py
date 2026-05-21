import os
import math
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Circle


PRIMARY = "#1F4E79"
SUCCESS = "#2E8B57"
ACCENT = "#D97706"
TEXT = "#1F2937"
MUTED = "#6B7280"
BG = "#FFFFFF"
GRID = "#E5E7EB"

SERIES = ["#1F4E79", "#2E8B57", "#D97706", "#7C3AED", "#DC2626", "#0891B2"]


def _setup_style():
    plt.style.use("default")
    plt.rcParams.update({
        "figure.facecolor": BG,
        "axes.facecolor": BG,
        "axes.edgecolor": GRID,
        "axes.labelcolor": TEXT,
        "text.color": TEXT,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "axes.titleweight": "bold",
        "axes.titlesize": 14,
        "axes.labelsize": 10,
        "font.size": 10,
        "grid.color": GRID,
        "grid.linestyle": "--",
        "grid.linewidth": 0.8,
    })


def _save(fig, output_dir, filename):
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, filename)
    fig.savefig(path, dpi=220, bbox_inches="tight", facecolor=BG)
    plt.close(fig)
    return path


def _safe_col(df, candidates):
    for col in candidates:
        if col in df.columns:
            return col
    return None


def _label_step(n_points, max_labels=12):
    if n_points <= max_labels:
        return 1
    return math.ceil(n_points / max_labels)


def generate_charts(df_clean, summary, output_dir="charts"):
    _setup_style()

    chart_paths = {}

    latest_week = summary["latest_week"]
    previous_week = summary["previous_week"]

    latest_kpis = latest_week.get("basic_kpis", {})
    previous_kpis = previous_week.get("basic_kpis", {})

    latest_revenue = latest_kpis.get("total_revenue", 0)
    previous_revenue = previous_kpis.get("total_revenue", 0)

    latest_orders = latest_kpis.get("total_orders", 0)
    previous_orders = previous_kpis.get("total_orders", 0)

    date_col = _safe_col(df_clean, ["date", "order_date", "created_at", "Date"])
    revenue_col = _safe_col(df_clean, ["revenue", "sales", "amount", "Revenue"])
    channel_col = _safe_col(df_clean, ["channel", "source", "Channel"])
    product_col = _safe_col(df_clean, ["top_product_sku", "sku", "product", "item_name", "SKU"])

    df = df_clean.copy()

    if date_col:
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")

    if revenue_col:
        df[revenue_col] = pd.to_numeric(df[revenue_col], errors="coerce").fillna(0)

    # 1. Revenue WoW bar chart
    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    labels = ["Previous Week", "Latest Week"]
    values = [previous_revenue, latest_revenue]
    colors = [MUTED, PRIMARY]

    bars = ax.bar(labels, values, color=colors, width=0.55)
    ax.set_title("Revenue Week-over-Week")
    ax.set_ylabel("Revenue (₹)")
    ax.grid(axis="y")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    for bar in bars:
        y = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            y,
            f"₹{y:,.0f}",
            ha="center",
            va="bottom",
            fontsize=10,
            fontweight="bold",
            color=TEXT
        )

    chart_paths["revenue_wow"] = _save(fig, output_dir, "revenue_wow.png")

    # 2. Orders WoW bar chart
    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    labels = ["Previous Week", "Latest Week"]
    values = [previous_orders, latest_orders]
    colors = [MUTED, SUCCESS]

    bars = ax.bar(labels, values, color=colors, width=0.55)
    ax.set_title("Orders Week-over-Week")
    ax.set_ylabel("Orders")
    ax.grid(axis="y")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    for bar in bars:
        y = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            y,
            f"{y:,.0f}",
            ha="center",
            va="bottom",
            fontsize=10,
            fontweight="bold",
            color=TEXT
        )

    chart_paths["orders_wow"] = _save(fig, output_dir, "orders_wow.png")

    # 3. Daily revenue trend line chart
    if date_col and revenue_col:
        valid_dates = df[df[date_col].notna()].copy()

        if not valid_dates.empty:
            valid_dates["plot_date"] = valid_dates[date_col].dt.normalize()

            daily = (
                valid_dates.groupby("plot_date", as_index=False)[revenue_col]
                .sum()
                .sort_values("plot_date")
            )

            if not daily.empty:
                fig, ax = plt.subplots(figsize=(9, 4.8))

                ax.plot(
                    daily["plot_date"],
                    daily[revenue_col],
                    color=PRIMARY,
                    linewidth=2.5,
                    marker="o",
                    markersize=4
                )

                ax.fill_between(
                    daily["plot_date"],
                    daily[revenue_col].values,
                    color=PRIMARY,
                    alpha=0.08
                )

                ax.set_title("Daily Revenue Trend")
                ax.set_ylabel("Revenue (₹)")
                ax.grid(axis="y")
                ax.spines["top"].set_visible(False)
                ax.spines["right"].set_visible(False)

                step = _label_step(len(daily), max_labels=12)
                tick_dates = daily["plot_date"].iloc[::step]

                ax.set_xticks(tick_dates)
                ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
                plt.xticks(rotation=45, ha="right")

                chart_paths["daily_revenue_trend"] = _save(fig, output_dir, "daily_revenue_trend.png")

    # 4. Channel mix donut chart
    if channel_col and revenue_col:
        channel_df = (
            df.groupby(channel_col)[revenue_col]
            .sum()
            .reset_index()
            .sort_values(revenue_col, ascending=False)
            .head(5)
        )

        if not channel_df.empty:
            fig, ax = plt.subplots(figsize=(7, 5.5))
            wedges, texts, autotexts = ax.pie(
                channel_df[revenue_col],
                labels=channel_df[channel_col],
                autopct="%1.1f%%",
                startangle=90,
                colors=SERIES[:len(channel_df)],
                pctdistance=0.82,
                wedgeprops={"width": 0.38, "edgecolor": BG}
            )

            centre_circle = Circle((0, 0), 0.50, fc=BG)
            ax.add_artist(centre_circle)
            ax.set_title("Revenue Share by Channel")

            for t in autotexts:
                t.set_color("white")
                t.set_fontsize(9)
                t.set_weight("bold")

            chart_paths["channel_mix"] = _save(fig, output_dir, "channel_mix.png")

    # 5. Top products horizontal bar chart
    if product_col and revenue_col:
        product_df = (
            df.groupby(product_col)[revenue_col]
            .sum()
            .reset_index()
            .sort_values(revenue_col, ascending=False)
            .head(7)
            .sort_values(revenue_col, ascending=True)
        )

        if not product_df.empty:
            fig, ax = plt.subplots(figsize=(8.5, 5.2))
            bars = ax.barh(product_df[product_col].astype(str), product_df[revenue_col], color=ACCENT)
            ax.set_title("Top Products by Revenue")
            ax.set_xlabel("Revenue (₹)")
            ax.grid(axis="x")
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)

            for bar in bars:
                x = bar.get_width()
                ax.text(
                    x,
                    bar.get_y() + bar.get_height() / 2,
                    f" ₹{x:,.0f}",
                    va="center",
                    ha="left",
                    fontsize=9,
                    fontweight="bold",
                    color=TEXT
                )

            chart_paths["top_products"] = _save(fig, output_dir, "top_products.png")

    return chart_paths