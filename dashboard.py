from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import streamlit as st
from matplotlib.ticker import FuncFormatter

sns.set_style("whitegrid")
st.set_page_config(page_title="E-Commerce Dashboard", page_icon="🛒", layout="wide")


@st.cache_data
def load_data():
    path = Path(__file__).parent / "main_data.csv"
    df = pd.read_csv(path, parse_dates=["order_purchase_timestamp"])
    df["order_month"] = df["order_purchase_timestamp"].dt.to_period("M").astype(str)
    return df


def juta(x, _):
    return f"{x / 1e6:.1f} jt"


df = load_data()

# ---------------- Sidebar ----------------
st.sidebar.header("Filter Data")
min_date = df["order_purchase_timestamp"].min().date()
max_date = df["order_purchase_timestamp"].max().date()
default_start = max(min_date, pd.Timestamp("2017-01-01").date())
default_end = min(max_date, pd.Timestamp("2017-12-31").date())

rentang = st.sidebar.date_input(
    "Rentang tanggal order",
    value=(default_start, default_end),
    min_value=min_date,
    max_value=max_date,
)
semua_state = sorted(df["customer_state"].unique())
pilih_state = st.sidebar.multiselect("Negara bagian", semua_state, default=semua_state)

if len(rentang) != 2:
    st.info("Pilih tanggal awal dan tanggal akhir pada filter di samping.")
    st.stop()

mulai, akhir = pd.Timestamp(rentang[0]), pd.Timestamp(rentang[1]) + pd.Timedelta(days=1)
data = df[
    (df["order_purchase_timestamp"] >= mulai)
    & (df["order_purchase_timestamp"] < akhir)
    & (df["customer_state"].isin(pilih_state))
]

st.title("🛒 Dashboard Analisis E-Commerce")
st.caption("Hanya order berstatus delivered. Revenue dihitung dari harga produk (price).")

if data.empty:
    st.warning("Tidak ada data untuk filter yang dipilih.")
    st.stop()

# ---------------- Ringkasan ----------------
c1, c2, c3 = st.columns(3)
c1.metric("Total Revenue", f"R$ {data['revenue'].sum():,.0f}")
c2.metric("Jumlah Order", f"{data['order_id'].nunique():,}")
c3.metric("Jumlah Pelanggan", f"{data['customer_unique_id'].nunique():,}")

# ---------------- Pertanyaan 1 ----------------
st.subheader("1. Revenue per Kategori Produk")
rev_kat = (
    data.groupby("product_category_name_english")["revenue"]
    .sum()
    .sort_values(ascending=False)
    .reset_index()
)
top5 = rev_kat.head(5)
bottom5 = rev_kat.tail(5).sort_values("revenue", ascending=False)

fig, ax = plt.subplots(1, 2, figsize=(16, 5))
sns.barplot(data=top5, x="revenue", y="product_category_name_english", color="#1f77b4", ax=ax[0])
ax[0].set_title("5 Kategori Revenue Tertinggi", fontsize=13)
sns.barplot(data=bottom5, x="revenue", y="product_category_name_english", color="#d62728", ax=ax[1])
ax[1].set_title("5 Kategori Revenue Terendah\n(perhatikan: skala sumbu berbeda)", fontsize=13)
for a in ax:
    a.set_xlabel("Total Revenue (R$)")
    a.set_ylabel("")
    a.margins(x=0.2)
    for container in a.containers:
        a.bar_label(container, fmt="R$ %.0f", padding=3)
plt.tight_layout()
st.pyplot(fig)

# ---------------- Pertanyaan 2 ----------------
st.subheader("2. Tren Order dan Revenue Bulanan")
tren = (
    data.groupby("order_month")
    .agg(jumlah_order=("order_id", "nunique"), total_revenue=("revenue", "sum"))
    .reset_index()
)

fig, ax = plt.subplots(figsize=(12, 5))
ax.plot(tren["order_month"], tren["total_revenue"], marker="o", linewidth=2, color="#1f77b4")
idx = tren["total_revenue"].idxmax()
x_p, y_p = tren.loc[idx, "order_month"], tren.loc[idx, "total_revenue"]
ax.scatter(x_p, y_p, color="#d62728", s=120, zorder=5)
ax.annotate(f"Puncak: {x_p}", (x_p, y_p), textcoords="offset points",
            xytext=(-12, 0), ha="right", va="center", color="#d62728", fontsize=11)
ax.yaxis.set_major_formatter(FuncFormatter(juta))
ax.set_xlabel("Bulan")
ax.set_ylabel("Total Revenue (R$)")
plt.xticks(rotation=45)
ax.grid(axis="y", alpha=0.3)
plt.tight_layout()
st.pyplot(fig)
st.dataframe(tren, use_container_width=True, hide_index=True)

# ---------------- Pertanyaan 3 ----------------
st.subheader("3. Negara Bagian dengan Revenue Tertinggi")
state = (
    data.groupby("customer_state")
    .agg(jumlah_pelanggan=("customer_unique_id", "nunique"), total_revenue=("revenue", "sum"))
    .sort_values("total_revenue", ascending=False)
    .reset_index()
)
top10 = state.head(10)
warna = ["#d62728" if i == 0 else "#b0b0b0" for i in range(len(top10))]

fig, ax = plt.subplots(figsize=(10, 5))
sns.barplot(data=top10, x="customer_state", y="total_revenue",
            palette=warna, hue="customer_state", legend=False, ax=ax)
ax.yaxis.set_major_formatter(FuncFormatter(juta))
ax.set_xlabel("Negara Bagian")
ax.set_ylabel("Total Revenue (R$)")
plt.tight_layout()
st.pyplot(fig)

# ---------------- RFM ----------------
st.subheader("Analisis Lanjutan: RFM")
st.caption("Recency, Frequency, Monetary dihitung dari data sesuai filter di atas.")

acuan = data["order_purchase_timestamp"].max() + pd.Timedelta(days=1)
rfm = (
    data.groupby("customer_unique_id")
    .agg(last_order=("order_purchase_timestamp", "max"),
         frequency=("order_id", "nunique"),
         monetary=("revenue", "sum"))
    .reset_index()
)
rfm["recency"] = (acuan - rfm["last_order"]).dt.days

m1, m2, m3 = st.columns(3)
m1.metric("Rata-rata Recency (hari)", f"{rfm['recency'].mean():.0f}")
m2.metric("Rata-rata Frequency", f"{rfm['frequency'].mean():.2f}")
m3.metric("Rata-rata Monetary", f"R$ {rfm['monetary'].mean():,.1f}")

if len(rfm) >= 4:
    rfm["R"] = pd.qcut(rfm["recency"].rank(method="first"), 4, labels=[4, 3, 2, 1]).astype(int)
    rfm["F"] = pd.qcut(rfm["frequency"].rank(method="first"), 4, labels=[1, 2, 3, 4]).astype(int)
    rfm["M"] = pd.qcut(rfm["monetary"].rank(method="first"), 4, labels=[1, 2, 3, 4]).astype(int)
    total = rfm["R"] + rfm["F"] + rfm["M"]
    rfm["segmen"] = total.apply(
        lambda s: "Pelanggan Terbaik" if s >= 10 else ("Pelanggan Potensial" if s >= 7 else "Pelanggan Berisiko")
    )
    urutan = ["Pelanggan Terbaik", "Pelanggan Potensial", "Pelanggan Berisiko"]
    jml = rfm["segmen"].value_counts().reindex(urutan).fillna(0).astype(int)

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(jml.index, jml.values, color=["#d62728", "#b0b0b0", "#b0b0b0"])
    for i, v in enumerate(jml.values):
        ax.text(i, v, f"{v:,}", ha="center", va="bottom")
    ax.set_ylabel("Jumlah Pelanggan")
    ax.margins(y=0.1)
    plt.tight_layout()
    st.pyplot(fig)
else:
    st.info("Data terlalu sedikit untuk segmentasi RFM.")

st.caption("Proyek Akhir Analisis Data - E-Commerce Public Dataset")
