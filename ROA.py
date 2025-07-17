import streamlit as st
import pandas as pd
import plotly.express as px
import yfinance as yf

st.set_page_config(page_title="ROA Dashboard", layout="wide")
st.title("📊 ROA Beberapa Perusahaan (2021–2025)")

# === CONFIGURATION ===
EXCEL_PATH = "Kode Saham.xlsx"  # File Excel kamu

# === Load kode saham & kategori
@st.cache_data(show_spinner=True)
def load_kode_saham():
    df_ind = pd.read_excel(EXCEL_PATH, sheet_name="industrial")
    df_mat = pd.read_excel(EXCEL_PATH, sheet_name="material")

    kategori_dict = pd.concat([df_ind, df_mat]).set_index("kode")["kategori"].to_dict()

    return df_ind['kode'].tolist(), df_mat['kode'].tolist(), kategori_dict

# === Ambil ROA dari yfinance
@st.cache_data(show_spinner=True)
def get_roa_perusahaan(kode_saham):
    ticker = yf.Ticker(f"{kode_saham}.JK")
    roa = {}
    for year in range(2021, 2026):
        try:
            income = ticker.financials.loc["Net Income"]
            assets = ticker.balance_sheet.loc["Total Assets"]
            income_y = income.get(f"{year}-12-31")
            assets_y = assets.get(f"{year}-12-31")
            if income_y is not None and assets_y is not None:
                roa[year] = round((income_y / assets_y) * 100, 2)
            else:
                roa[year] = None
        except:
            roa[year] = None
    return roa

@st.cache_data(show_spinner=True)
def fetch_roa_for_list(kode_list):
    data = {}
    for kode in kode_list:
        with st.spinner(f"🔄 Mengambil ROA {kode}..."):
            data[kode] = get_roa_perusahaan(kode)
    return pd.DataFrame(data).T

# === Load data
ind_list, mat_list, kategori_dict = load_kode_saham()
df_ind = fetch_roa_for_list(ind_list)
df_mat = fetch_roa_for_list(mat_list)

# === Pilihan di Sidebar ===
with st.sidebar:
    st.header("⚙️ Filter Data")

    # Pilih sektor
    sektor = st.radio("📌 Pilih sektor:", ["industrial", "material"])
    df = df_ind if sektor == "industrial" else df_mat

    # Pilih kode saham
    all_kode = df.index.tolist()
    select_all = st.checkbox("✅ Pilih semua kode saham", value=False)

    if select_all:
        selected = st.multiselect("🔍 Pilih kode saham:", all_kode, default=all_kode)
    else:
        selected = st.multiselect("🔍 Pilih kode saham:", all_kode, default=all_kode[:5])

# Filter DataFrame sesuai pilihan
df_selected = df.loc[selected]


# === Tabel ROA + kategori
st.subheader("📋 Tabel ROA")
df_display = df_selected.fillna(0.0)
df_display["Kategori"] = df_display.index.map(kategori_dict)
cols_order = [col for col in df_display.columns if col != "Kategori"] + ["Kategori"]
# Hanya format kolom tahun (numerik), bukan kolom 'Kategori'
format_dict = {col: "{:.2f} %" for col in df_display.columns if col != "Kategori"}
st.dataframe(df_display[cols_order].style.format(format_dict), use_container_width=True)


# === Grafik per saham
df_long = df_display.reset_index().melt(id_vars=["index", "Kategori"], var_name="Tahun", value_name="ROA")
df_long.columns = ['Kode Saham', 'Kategori', 'Tahun', 'ROA']
df_long["Tahun"] = df_long["Tahun"].astype(str)  # Supaya sumbu X tidak koma

st.subheader("📈 Grafik ROA per Tahun")
fig = px.line(df_long, x="Tahun", y="ROA", color="Kode Saham", markers=True)
st.plotly_chart(fig, use_container_width=True)

# === Rata-rata sektor
df_ind_avg = df_ind.copy().fillna(0.0).mean().reset_index()
df_ind_avg.columns = ['Tahun', 'ROA Industrial']
df_ind_avg = df_ind_avg[df_ind_avg['Tahun'].between(2021, 2025)]

df_mat_avg = df_mat.copy().fillna(0.0).mean().reset_index()
df_mat_avg.columns = ['Tahun', 'ROA Material']
df_mat_avg = df_mat_avg[df_mat_avg['Tahun'].between(2021, 2025)]

# === ROA WTON
st.subheader("📊 Komparasi ROA WIKA Beton dengan Rata-rata Sektor")
with st.spinner("Mengambil data ROA WTON..."):
    wton_roa_dict = get_roa_perusahaan("WTON")
    if wton_roa_dict.get(2021) is None:
        wton_roa_dict[2021] = 1.50

wton_df = pd.DataFrame.from_dict(wton_roa_dict, orient='index', columns=['ROA WTON']).reset_index()
wton_df.columns = ['Tahun', 'ROA WTON']
wton_df = wton_df[wton_df["Tahun"].between(2021, 2025)]

# === Gabungkan semua tren
df_compare = df_ind_avg.merge(df_mat_avg, on="Tahun", how="outer")
df_compare = df_compare.merge(wton_df, on="Tahun", how="outer")
df_compare_long = df_compare.melt(id_vars="Tahun", var_name="Kategori", value_name="ROA")
df_compare["Tahun"] = df_compare["Tahun"].astype(str)
df_compare_long["Tahun"] = df_compare_long["Tahun"].astype(str)

# === Grafik tren
fig3 = px.line(df_compare_long, x="Tahun", y="ROA", color="Kategori", markers=True,
               labels={"ROA": "ROA (%)", "Kategori": "Perbandingan"})
st.plotly_chart(fig3, use_container_width=True)

# === Tabel tren per tahun
st.subheader("📋 Data Tren ROA per Tahun")
df_tren_display = df_compare.set_index("Tahun").T
df_tren_display.index.name = "Kategori"
st.dataframe(df_tren_display.style.format("{:.2f} %"), use_container_width=True)
