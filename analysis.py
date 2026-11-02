"""Sales analysis functions. Every function takes a pandas DataFrame
produced by load_sales() and returns plain Python data (dicts and lists)
that the Flask app can send to the web page."""

import pandas as pd

REQUIRED_COLUMNS = ["date", "product", "category", "region", "quantity", "price"]


def load_sales(source):
    """Read a CSV (file path or uploaded file object) and return a clean DataFrame.
    Raises ValueError with a readable message if the file is not usable."""
    try:
        df = pd.read_csv(source)
    except pd.errors.EmptyDataError:
        raise ValueError("The file is empty.")
    except Exception:
        raise ValueError("The file could not be read as a CSV.")

    df.columns = [c.strip().lower() for c in df.columns]
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError("Missing column(s): " + ", ".join(missing))

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce")
    df["price"] = pd.to_numeric(df["price"], errors="coerce")
    df = df.dropna(subset=REQUIRED_COLUMNS)

    if df.empty:
        raise ValueError("No valid rows found. Check the date, quantity and price values.")

    df["revenue"] = df["quantity"] * df["price"]
    return df


def summary(df):
    """Headline numbers shown at the top of the dashboard."""
    orders = len(df)
    total_revenue = float(df["revenue"].sum())
    return {
        "total_revenue": round(total_revenue, 2),
        "total_units": int(df["quantity"].sum()),
        "orders": orders,
        "avg_order_value": round(total_revenue / orders, 2),
        "date_from": df["date"].min().strftime("%d %b %Y"),
        "date_to": df["date"].max().strftime("%d %b %Y"),
    }


def _group_revenue(df, column, top=None):
    grouped = df.groupby(column)["revenue"].sum().sort_values(ascending=False)
    if top:
        grouped = grouped.head(top)
    return {
        "labels": [str(x) for x in grouped.index],
        "values": [round(float(v), 2) for v in grouped.values],
    }


def top_products(df, n=5):
    return _group_revenue(df, "product", top=n)


def sales_by_region(df):
    return _group_revenue(df, "region")


def sales_by_category(df):
    return _group_revenue(df, "category")


def monthly_trend(df):
    monthly = df.groupby(df["date"].dt.to_period("M"))["revenue"].sum().sort_index()
    return {
        "labels": [p.strftime("%b %Y") for p in monthly.index],
        "values": [round(float(v), 2) for v in monthly.values],
    }


def build_report(df):
    """Everything the dashboard needs in one dictionary."""
    return {
        "summary": summary(df),
        "top_products": top_products(df),
        "regions": sales_by_region(df),
        "categories": sales_by_category(df),
        "monthly": monthly_trend(df),
    }
