import pandas as pd
import numpy as np

REQUIRED_COLUMNS = ["date", "product", "category", "region", "quantity", "price"]

def load_sales(source):
    try:
        df = pd.read_csv(source, encoding="utf-8-sig")
    except pd.errors.EmptyDataError:
        raise ValueError("The CSV file is empty.")
    except UnicodeDecodeError:
        raise ValueError("The CSV must use UTF-8 encoding. Save it as CSV UTF-8 and try again.")
    except Exception as exc:
        raise ValueError(f"Could not read this CSV file: {exc}")
    df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError("Missing required columns: " + ", ".join(missing))
    df = df[REQUIRED_COLUMNS].copy()
    for col in ["product", "category", "region"]:
        df[col] = df[col].astype("string").str.strip()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce")
    df["price"] = pd.to_numeric(df["price"], errors="coerce")
    df = df.dropna(subset=REQUIRED_COLUMNS)
    df = df[(df["product"] != "") & (df["category"] != "") & (df["region"] != "")]
    df = df[(df["quantity"] > 0) & (df["price"] >= 0)]
    if df.empty:
        raise ValueError("No valid sales rows found. Check dates, names, quantity and price.")
    if not np.isfinite(df["quantity"]).all() or not np.isfinite(df["price"]).all():
        raise ValueError("Quantity and price must contain finite numeric values.")
    df["quantity"] = df["quantity"].astype(int)
    df["revenue"] = df["quantity"] * df["price"]
    return df.sort_values("date").reset_index(drop=True)

def filter_sales(df, filters):
    work = df.copy()
    if filters.get("start"):
        start = pd.to_datetime(filters["start"], errors="coerce")
        if pd.isna(start): raise ValueError("Invalid start date.")
        work = work[work["date"] >= start]
    if filters.get("end"):
        end = pd.to_datetime(filters["end"], errors="coerce")
        if pd.isna(end): raise ValueError("Invalid end date.")
        work = work[work["date"] <= end + pd.Timedelta(days=1) - pd.Timedelta(microseconds=1)]
    if filters.get("region"): work = work[work["region"] == filters["region"]]
    if filters.get("category"): work = work[work["category"] == filters["category"]]
    return work

def group_data(df, column, limit=None):
    grouped = df.groupby(column)["revenue"].sum().sort_values(ascending=False)
    if limit: grouped = grouped.head(limit)
    return {"labels": grouped.index.astype(str).tolist(), "values": [round(float(x), 2) for x in grouped.values]}

def build_report(df):
    total = float(df["revenue"].sum()) if len(df) else 0
    orders = int(len(df))
    monthly = df.groupby(df["date"].dt.to_period("M"))["revenue"].sum().sort_index()
    months = monthly.reset_index()
    growth = []
    for i, value in enumerate(monthly.values):
        previous = monthly.values[i-1] if i else 0
        growth.append(round(((value-previous)/previous)*100, 1) if previous else None)
    return {
        "summary": {
            "total_revenue": round(total, 2),
            "total_units": int(df["quantity"].sum()) if len(df) else 0,
            "orders": orders,
            "avg_order_value": round(total/orders, 2) if orders else 0,
            "date_from": df["date"].min().strftime("%d %b %Y") if len(df) else "—",
            "date_to": df["date"].max().strftime("%d %b %Y") if len(df) else "—",
        },
        "monthly": {"labels":[p.strftime("%b %Y") for p in monthly.index], "values":[round(float(v),2) for v in monthly.values], "growth":growth},
        "products": group_data(df, "product", 8),
        "regions": group_data(df, "region"),
        "categories": group_data(df, "category"),
    }

def insights(df):
    if df.empty:
        return {"mean":0,"median":0,"std":0,"best_product":"—","best_region":"—","growth":None,"outliers":[]}
    product = df.groupby("product")["revenue"].sum()
    region = df.groupby("region")["revenue"].sum()
    grouped = df.groupby("product")["quantity"]
    means = grouped.transform("mean")
    stds = grouped.transform("std").fillna(0)
    z = (df["quantity"] - means) / stds.replace(0, np.nan)
    unusual = df[z.abs() >= 2].copy()
    unusual["z_score"] = z[z.abs() >= 2].round(2)
    return {
        "mean":round(float(df["revenue"].mean()),2),
        "median":round(float(df["revenue"].median()),2),
        "std":round(float(df["revenue"].std(ddof=1) or 0),2),
        "best_product":str(product.idxmax()),
        "best_region":str(region.idxmax()),
        "growth":build_report(df)["monthly"]["growth"][-1] if len(build_report(df)["monthly"]["growth"]) else None,
        "outliers":[{"date":r.date.strftime("%Y-%m-%d"),"product":r.product,"quantity":int(r.quantity),"z_score":float(r.z_score)} for r in unusual.head(10).itertuples()],
    }
