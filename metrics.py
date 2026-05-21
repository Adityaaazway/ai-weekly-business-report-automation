import pandas as pd


def get_last_full_week(latest_date=None):
    """
    Returns the latest completed Monday-Sunday week
    based on the latest date available in the data.

    Example:
    If latest_date is Wednesday 2026-05-20,
    returns Monday 2026-05-11 to Sunday 2026-05-17.
    """
    if latest_date is None:
        latest_date = pd.Timestamp.today().normalize()
    else:
        latest_date = pd.Timestamp(latest_date).normalize()

    latest_week_monday_anchor = latest_date - pd.Timedelta(days=latest_date.weekday())

    if latest_date.weekday() == 6:
        latest_week_start = latest_week_monday_anchor
        latest_week_end = latest_week_monday_anchor + pd.Timedelta(days=6)
    else:
        latest_week_end = latest_week_monday_anchor - pd.Timedelta(days=1)
        latest_week_start = latest_week_end - pd.Timedelta(days=6)

    return latest_week_start, latest_week_end


def get_previous_week(week_start):
    """
    Returns the week before the selected week.
    """
    previous_week_end = week_start - pd.Timedelta(days=1)
    previous_week_start = previous_week_end - pd.Timedelta(days=6)
    return previous_week_start, previous_week_end


def slice_week(df, start_date, end_date):
    """
    Filter dataframe for a date range.
    """
    temp_df = df.copy()
    temp_df["date"] = pd.to_datetime(temp_df["date"], errors="coerce").dt.normalize()
    temp_df = temp_df.dropna(subset=["date"])

    start_date = pd.Timestamp(start_date).normalize()
    end_date = pd.Timestamp(end_date).normalize()

    return temp_df[(temp_df["date"] >= start_date) & (temp_df["date"] <= end_date)].copy()


def calc_basic_kpis(week_df):
    """
    Basic KPIs: revenue, orders, AOV
    """
    if week_df.empty:
        return {
            "total_revenue": 0.0,
            "total_orders": 0,
            "aov": None
        }

    revenue_series = pd.to_numeric(week_df["revenue"], errors="coerce").fillna(0)
    orders_series = pd.to_numeric(week_df["orders"], errors="coerce").fillna(0)

    total_revenue = round(float(revenue_series.sum()), 2)
    total_orders = int(orders_series.sum())

    aov = round(total_revenue / total_orders, 2) if total_orders > 0 else None

    return {
        "total_revenue": total_revenue,
        "total_orders": total_orders,
        "aov": aov
    }


def calc_customer_split(week_df):
    """
    New vs returning customers
    """
    if week_df.empty:
        return {
            "new_customers": 0,
            "returning_customers": 0,
            "new_pct": 0.0,
            "returning_pct": 0.0
        }

    new_customers = int(pd.to_numeric(week_df["new_customers"], errors="coerce").fillna(0).sum())
    returning_customers = int(pd.to_numeric(week_df["returning_customers"], errors="coerce").fillna(0).sum())
    total_customers = new_customers + returning_customers

    if total_customers > 0:
        new_pct = round((new_customers / total_customers) * 100, 1)
        returning_pct = round((returning_customers / total_customers) * 100, 1)
    else:
        new_pct = 0.0
        returning_pct = 0.0

    return {
        "new_customers": new_customers,
        "returning_customers": returning_customers,
        "new_pct": new_pct,
        "returning_pct": returning_pct
    }


def calc_channel_breakdown(week_df):
    """
    Revenue and orders by channel
    """
    if week_df.empty:
        return []

    temp_df = week_df.copy()
    temp_df["revenue"] = pd.to_numeric(temp_df["revenue"], errors="coerce").fillna(0)
    temp_df["orders"] = pd.to_numeric(temp_df["orders"], errors="coerce").fillna(0)

    grouped = (
        temp_df.groupby("channel", as_index=False)
        .agg({
            "revenue": "sum",
            "orders": "sum"
        })
        .sort_values("revenue", ascending=False)
    )

    total_revenue = grouped["revenue"].sum()

    result = []
    for _, row in grouped.iterrows():
        revenue_share = round((row["revenue"] / total_revenue) * 100, 1) if total_revenue > 0 else 0.0

        result.append({
            "channel": row["channel"],
            "revenue": round(float(row["revenue"]), 2),
            "orders": int(row["orders"]),
            "revenue_share_pct": revenue_share
        })

    return result


def calc_top_products(week_df, top_n=3):
    """
    Top products based on top_product_revenue
    """
    if week_df.empty:
        return []

    temp_df = week_df.copy()
    temp_df["top_product_revenue"] = pd.to_numeric(temp_df["top_product_revenue"], errors="coerce").fillna(0)

    grouped = (
        temp_df.groupby("top_product_sku", as_index=False)
        .agg({
            "top_product_revenue": "sum"
        })
        .sort_values("top_product_revenue", ascending=False)
        .head(top_n)
    )

    result = []
    for rank, (_, row) in enumerate(grouped.iterrows(), start=1):
        result.append({
            "rank": rank,
            "sku": row["top_product_sku"],
            "revenue": round(float(row["top_product_revenue"]), 2)
        })

    return result


def detect_anomaly_days(week_df, z_threshold=2.0):
    """
    Detect unusually high or low revenue days using z-score.
    """
    if week_df.empty:
        return []

    temp_df = week_df.copy()
    temp_df["date"] = pd.to_datetime(temp_df["date"], errors="coerce").dt.normalize()
    temp_df["revenue"] = pd.to_numeric(temp_df["revenue"], errors="coerce").fillna(0)
    temp_df = temp_df.dropna(subset=["date"])

    daily = (
        temp_df.groupby("date", as_index=False)
        .agg({
            "revenue": "sum"
        })
        .sort_values("date")
    )

    if len(daily) < 3:
        return []

    mean_rev = daily["revenue"].mean()
    std_rev = daily["revenue"].std()

    if std_rev == 0 or pd.isna(std_rev):
        return []

    anomalies = []

    for _, row in daily.iterrows():
        z_score = (row["revenue"] - mean_rev) / std_rev

        if abs(z_score) >= z_threshold:
            anomalies.append({
                "date": str(pd.Timestamp(row["date"]).date()),
                "revenue": round(float(row["revenue"]), 2),
                "z_score": round(float(z_score), 2),
                "direction": "high" if z_score > 0 else "low"
            })

    return anomalies


def calculate_pct_change(latest, previous):
    """
    Percentage change helper
    """
    if latest is None or previous is None:
        return None
    if previous == 0:
        return None
    return round(((latest - previous) / previous) * 100, 1)


def get_chart_label_step(n_points, max_labels=15):
    """
    Returns a step size for x-axis labels.
    Keeps all data points, but reduces visible date labels.
    """
    if n_points <= max_labels:
        return 1
    return max(1, n_points // max_labels)


def build_weekly_summary(df):
    """
    Main function for weekly summary.
    Uses the latest available date in the dataset
    instead of today's system date.
    """
    temp_df = df.copy()
    temp_df["date"] = pd.to_datetime(temp_df["date"], errors="coerce").dt.normalize()
    temp_df = temp_df.dropna(subset=["date"])

    latest_date_in_data = temp_df["date"].max()

    latest_week_start, latest_week_end = get_last_full_week(latest_date_in_data)
    previous_week_start, previous_week_end = get_previous_week(latest_week_start)

    latest_week_df = slice_week(temp_df, latest_week_start, latest_week_end)
    previous_week_df = slice_week(temp_df, previous_week_start, previous_week_end)

    latest_basic = calc_basic_kpis(latest_week_df)
    previous_basic = calc_basic_kpis(previous_week_df)

    latest_customers = calc_customer_split(latest_week_df)
    previous_customers = calc_customer_split(previous_week_df)

    summary = {
        "latest_date_in_data": str(latest_date_in_data.date()),
        "week_start": str(latest_week_start.date()),
        "week_end": str(latest_week_end.date()),
        "previous_week_start": str(previous_week_start.date()),
        "previous_week_end": str(previous_week_end.date()),

        "latest_week": {
            "row_count": int(len(latest_week_df)),
            "basic_kpis": latest_basic,
            "customer_split": latest_customers,
            "channel_breakdown": calc_channel_breakdown(latest_week_df),
            "top_products": calc_top_products(latest_week_df, top_n=3),
            "anomaly_days": detect_anomaly_days(latest_week_df)
        },

        "previous_week": {
            "row_count": int(len(previous_week_df)),
            "basic_kpis": previous_basic,
            "customer_split": previous_customers
        },

        "week_over_week_change": {
            "revenue_pct": calculate_pct_change(
                latest_basic["total_revenue"],
                previous_basic["total_revenue"]
            ),
            "orders_pct": calculate_pct_change(
                latest_basic["total_orders"],
                previous_basic["total_orders"]
            ),
            "aov_pct": calculate_pct_change(
                latest_basic["aov"],
                previous_basic["aov"]
            )
        }
    }

    return summary