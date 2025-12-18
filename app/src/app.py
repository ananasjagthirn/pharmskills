import streamlit as st
import pandas as pd
from pathlib import Path

#befehl für terminal um app zu starten: streamlit run app/src/app.py

st.set_page_config(page_title="Übungsapotheke", layout="wide")

#pfade zu ordner und bildern
APP_DIR = Path(__file__).resolve().parent.parent
IMAGES_DIR = APP_DIR / "data" / "images"

#daten laden
@st.cache_data
def load_data():
    base_dir = Path(__file__).resolve().parent.parent
    data_path = base_dir / "data" / "data_full.xlsx"
    df = pd.read_excel(data_path, dtype={"pzn": str})
    df["pzn"] = df["pzn"].str.strip().str.zfill(8)
    return df

#bild anhand der pzn finden
def find_image_for_pzn(pzn):
    pzn = str(pzn).strip()
    matches = list(IMAGES_DIR.glob(f"{pzn}.*"))
    return matches[0] if matches else None

df = load_data()
df.columns = df.columns.str.strip().str.lower()

st.title("Beratungshilfe: Selbstmedikation bei Erkältung")

with st.expander("Disclaimer"):
    st.write('''Die Auswahl der Fertigarzneimittel dient einer ersten Orientierung 
    in den verfügbaren Fertigarzneimitteln der Selbstmedikation. Die Auswahl der
    dargestellten Fertigarzneimittel entspricht nicht einer Abgabeempfehlung oder 
    dem Vorzug von bestimmten Präparaten.''')

st.markdown("Nutze die Filter in der Seitenleiste, um passende Präparate zu finden, "
    "und wähle anschließend ein Präparat aus, um Details für das Beratungsgespräch zu sehen."
)

#sidebar
st.sidebar.header("Filter")

#dynamische Listen aus den Daten für filter
#Indikationen
#1. indikationen splitten
#ls_ind = []
#for index, row in df.iterrows():
#    if isinstance(row["indication"], str):
#        ls_ind.extend(row["indication"].split(", "))
#ls_ind = list(set(ls_ind))

#vereinfacht laut chatgpt
ls_ind = sorted(set(df["indication"].str.split(",").explode().str.strip()))

#2. multiselect
indikationen_filter = st.sidebar.multiselect(
    "Nach Indikation filtern",
    options=ls_ind,
    default=[])

#3. filter anwenden
df_ind = df.copy()
if indikationen_filter:
    selected = set(indikationen_filter)
    df_ind = df_ind[df_ind["indication"].apply(lambda s: bool(selected.intersection({i.strip() for i in s.split(",")})))]

ls_drf = sorted(df_ind["drf"].dropna().unique().tolist())
#wenn der filter indikation geändert wird
prev = st.session_state.get("darreichung_filter", [])
prev = [x for x in prev if x in ls_drf]

darreichung_filter = st.sidebar.multiselect(
    "Nach Darreichungsform filtern",
    options=ls_drf,
    default=prev,
    key="darreichung_filter")

#darreichungen
#ls_drf = []
#for index, row in df.iterrows():
#    if isinstance(row["drf"], str):
#        ls_drf.append(row["drf"])
#ls_drf = sorted(list(set(ls_drf)))

#darreichung_filter = st.sidebar.multiselect(
#    "Nach Darreichungsform filtern",
#    options=ls_drf,
#    default=[])

pflanzlich_filter = st.sidebar.checkbox("Nur pflanzliche Präparate anzeigen")

st.sidebar.divider()

suchtext = st.sidebar.text_input("Freitextsuche (Präparat oder Wirkstoff)")

#wenn was in excel geändert wurde
if st.sidebar.button("Daten neu laden"):
    st.cache_data.clear()
    st.rerun()

#filter anwenden
filtered = df_ind.copy()

#if indikationen_filter:
#    selected = set(indikationen_filter)
#    filtered = filtered[
#        df["indication"].apply(
#            lambda s: bool(selected.intersection({i.strip() for i in s.split(",")}))
#        )
#    ]
    #filtered = filtered[filtered["indication"].isin(indikationen_filter)]

if darreichung_filter:
    filtered = filtered[filtered["drf"].isin(darreichung_filter)]

if pflanzlich_filter:
    filtered = filtered[filtered["plant"].str.lower() == "ja"]

if suchtext:
    mask = (filtered["handelsname"].str.contains(suchtext, case=False, na=False) | filtered["drug"].str.contains(suchtext, case=False, na=False))
    filtered = filtered[mask]

st.write(f"Gefundene Präparate: {len(filtered)}")

if len(filtered) == 0:
    st.info("Keine Präparate mit diesen Kriterien gefunden.")
    st.stop()


#Detailansicht

def show_details(row: pd.Series):
    st.divider()

    col1, col2, col3 = st.columns(spec=[3,1,2])

    with col1:
        st.header(row["handelsname"])
        st.subheader(":material/info: Infos")
        st.write(f"Indikation: {row['indication']}")
        st.write(f"Wirkstoff(e): {row['drug']}")
        st.write(f"Darreichungsform: {row['drf']}")
        st.divider()

        st.subheader(":material/pill: Dosierung und Anwendung")
        st.write(f"Anwendung: {row['use']}")
        st.write(f"Einzeldosis: {row['ed']}")
        st.write(f"Tagesmaximaldosis: {row['td']}")
        st.divider()

        st.subheader(":material/error: Grenzen der Selbstmedikation")
        st.write(f"Anwendungsdauer ohne ärztliche Rücksprache: {row['grenzen']}")
        st.divider()

        st.caption(f"Quelle: {row['source']}")

    with col3:
        img_path = find_image_for_pzn(row["pzn"])
        if img_path:
            st.image(str(img_path), width="content", caption=f"Copyright: {row['image_cr']}")

#hauptbereich
st.subheader("Präparateübersicht")

st.dataframe(
    filtered[["handelsname", "indication", "drug", "drf"]])

auswahl = st.selectbox("Präparat auswählen", options=filtered["handelsname"].unique())

if auswahl:
    row = filtered[filtered["handelsname"] == auswahl].iloc[0]
    show_details(row)