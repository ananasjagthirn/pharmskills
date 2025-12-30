import streamlit as st
import pandas as pd
from pathlib import Path

#befehl für terminal um app lokal zu starten: streamlit run app/src/app.py

st.set_page_config(page_title="Übungsapotheke", layout="wide")

#pfade zu ordner und bildern
APP_DIR = Path(__file__).resolve().parent.parent
IMAGES_DIR = APP_DIR / "data" / "images"
EVIDENCE_DIR = APP_DIR / "data" / "data_evidence.xlsx"

#daten laden
@st.cache_data
def load_data():
    base_dir = Path(__file__).resolve().parent.parent
    data_path = base_dir / "data" / "data_full.xlsx"
    df = pd.read_excel(data_path, dtype={"pzn": str})
    df["pzn"] = df["pzn"].str.strip().str.zfill(8)
    return df

#evidence data laden
@st.cache_data
def load_evidence():
    ev = pd.read_excel(EVIDENCE_DIR)
    ev.columns = ev.columns.str.strip().str.lower()

    #wirkstoff-liste als einzelne keywords
    ev_long = ev.copy()
    ev_long["drug_kw"] = ev_long["drug"].astype(str).str.split(";", regex=True)
    #eine Zeile pro Wirkstoff-keyword
    ev_long = ev_long.explode("drug_kw", ignore_index=True)

    ev_long["drug_kw"] = ev_long["drug_kw"].astype(str).str.strip().str.lower()
    ev_long["ind_key"] = ev_long["ind"].astype(str).str.strip().str.lower()
    return ev_long

#bild anhand der pzn finden
def find_image_for_pzn(pzn):
    pzn = str(pzn).strip()
    matches = list(IMAGES_DIR.glob(f"{pzn}.*"))
    return matches[0] if matches else None

df = load_data()
df.columns = df.columns.str.strip().str.lower()

#wirkstoffe in data_full zerlegen
import re

def split_list(cell: str) -> list[str]:
    parts = re.split(r"[;]", str(cell))
    return [p.strip() for p in parts if p.strip()]

def norm(s: str) -> str:
    return str(s).strip().lower()

ev_df = load_evidence()

st.title("Beratungshilfe: Selbstmedikation bei Erkältung")

with st.expander("Disclaimer"):
    st.write('''Die Auswahl der dargestellten Fertigarzneimittel dient der Orientierung über in der Selbstmedikation 
    bei Erkältungssymptomen verfügbaren Präparate und stellt weder eine Abgabeempfehlung noch eine Bewertung oder Bevorzugung einzelner Fertigarzneimittel dar.''')
    st.write(''' Diese Beratungshilfe wird ausschließlich zu Lehr- und Übungszwecken im Rahmen des Praktikums "Krankheitslehre I - Übungsapotheke" im 
    Studiengang Pharmazie an der Universität Leipzig eingesetzt.''')
    st.write('''Die enthaltenen Informationen basieren unter anderem auf Angaben aus Fachinformationen und sind ausschließlich für pharmazeutisches Fachpersonal bestimmt.
    Eine Weitergabe oder Anwendung der Inhalte außerhalb des genannten Lehrkontextes ist nicht vorgesehen.''')


st.info(
    ":material/lightbulb: Nutze die Filter in der Seitenleiste, um passende Präparate zu finden. "
    "Wähle anschließend ein Präparat aus, um die Informationen zum Präparat anzuzeigen."
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
ls_ind = sorted(set(df["indication"].str.split("; ").explode().str.strip()))

#2. multiselect
indikationen_filter = st.sidebar.multiselect(
    "Nach Indikation filtern",
    options=ls_ind,
    default=[])

#3. filter anwenden
df_ind = df.copy()
if indikationen_filter:
    selected = set(indikationen_filter)
    df_ind = df_ind[df_ind["indication"].apply(lambda s: bool(selected.intersection({i.strip() for i in s.split("; ")})))]

ls_drf = sorted(df_ind["drf"].dropna().unique().tolist())
#wenn der filter indikation geändert wird
prev = st.session_state.get("darreichung_filter", [])
prev = [x for x in prev if x in ls_drf]

darreichung_filter = st.sidebar.multiselect(
    "Nach Darreichungsform filtern",
    options=ls_drf,
    default=prev,
    key="darreichung_filter")


pflanzlich_filter = st.sidebar.checkbox("Nur pflanzliche Präparate anzeigen")

st.sidebar.divider()

suchtext = st.sidebar.text_input("Freitextsuche (Präparat oder Wirkstoff)")

#wenn was in excel geändert wurde, nur anschalten, wenn App überarbeitet wird
if st.sidebar.button("Daten neu laden"):
    st.cache_data.clear()
    st.rerun()

#filter anwenden
filtered = df_ind.copy()

if darreichung_filter:
    filtered = filtered[filtered["drf"].isin(darreichung_filter)]

if pflanzlich_filter:
    filtered = filtered[filtered["plant"].str.lower() == "ja"]

if suchtext:
    mask = (filtered["handelsname"].str.contains(suchtext, case=False, na=False) | filtered["drug"].str.contains(suchtext, case=False, na=False))
    filtered = filtered[mask]

st.caption(f"Gefundene Präparate: {len(filtered)}")

if len(filtered) == 0:
    st.info("Keine Präparate mit diesen Kriterien gefunden.")
    st.stop()


#Detailansicht

def show_details(row: pd.Series):
    st.divider()
    st.header(row["handelsname"])

    col1, col2, col3 = st.columns(spec=[3,1,2])

    with col1:
        tab_info, tab_guideline = st.tabs(
            ["Details", "Leitlinie"]
        )
        with tab_info:

            st.subheader(":material/info: Infos")
            st.write(f"Indikation: {row['indication']}")
            st.write(f"Wirkstoff(e): {row['drug']}")
            st.write(f"Darreichungsform: {row['drf']}")
            st.divider()

            st.subheader(":material/pill: Dosierung und Anwendung")
            st.write(f"Anwendung: {row['use']}")
            st.write(f"Einzeldosis: {row['ed']}")
            st.write(f"Tagesmaximaldosis: {row['td']}")

            #hinweise nur anzeigen, wenn es welche gibt
            hinweise = row.get("hinweise")
            if isinstance(hinweise, str) and hinweise.strip():
                st.write(f"Weitere Hinweise: {row['hinweise']}")
            st.divider()

            st.subheader(":material/error: Grenzen der Selbstmedikation")
            st.write(f"Anwendungsdauer ohne ärztliche Rücksprache: {row['grenzen']}")
            st.divider()

            st.subheader(":material/document_search: Quelle")
            st.write(f"{row['source']}")

        # tab zur leitlinien empfehlung
        with tab_guideline:
            #präparate indikation und wirkstoffe vorbereiten
            ind_list = [norm(x) for x in split_list(row["indication"])]
            ind_list = [i for i in ind_list if i]
            drug_list = [norm(x) for x in split_list(row["drug"])]

            #evidence auf passende indikationen einschränken
            ev_ind = ev_df[ev_df["ind_key"].isin(ind_list)].copy()

            #treffer sammeln: evidenz-keyword muss im präparat-wirkstoff vorkommen (substring)
            hits = []
            for drug in drug_list:
                sub = ev_ind[ev_ind["drug_kw"].apply(lambda kw: kw in drug)]
                if not sub.empty:
                    hits.append(sub)

            if not hits:
                st.info("Die Wirkstoffe dieses Präparates werden nicht in der Leitlinie genannt oder es existiert keine Leitlinie zu der Indikation.")
            else:
                hits_df = pd.concat(hits).drop_duplicates()

                #wenn mehrere Wirkstoffe derselben ws_gruppe matchen: alle unter "drug" auflisten
                grouped = (
                    hits_df
                    .groupby(["ind", "ws_gruppe", "recom", "source", "stand"], dropna=False)["drug_kw"]
                    .apply(lambda s: ", ".join(sorted({x.title() for x in s})))
                    .reset_index(name="drug_list")
                    .sort_values(["ind", "ws_gruppe"])
                )

                #Ausgabe
                for ind, part in grouped.groupby("ind", sort=False):
                    st.markdown(f"**Bei {ind}:**")
                    for _, r2 in part.iterrows():
                        st.info(
                            f"- {r2['ws_gruppe']} ({r2['drug_list']}) "
                            f"**{r2['recom']}** ({r2['source']}, Stand: {r2['stand']})"
                        )

    with col3:
        img_path = find_image_for_pzn(row["pzn"])
        if img_path:
            st.image(str(img_path), width="content", caption=f"Copyright: {row['image_cr']}")

#hauptbereich
st.subheader("Präparateübersicht")

display_df = filtered[["handelsname", "indication", "drug", "drf"]].rename(
    columns={
        "handelsname": "Name Fertigarzneimittel/Präparat",
        "indication": "Indikation",
        "drug": "Wirkstoff(e)",
        "drf": "Darreichungsform",
    }
)

st.dataframe(
    display_df,
    hide_index=True,
)

auswahl = st.selectbox("Präparat auswählen", options=filtered["handelsname"].unique())

if auswahl:
    row = filtered[filtered["handelsname"] == auswahl].iloc[0]
    show_details(row)

st.divider()

st.caption('''© 2025 · Tanjana Harings · Lehrtool für das Praktikum „Krankheitslehre I - Übungsapotheke"''')

with st.expander("Über diese App"):
    st.caption('''Diese webbasierte Beratungshilfe wurde als Lehr- und Übungstool für das Praktikum "Krankheitslehre I - Übungsapotheke" im Studiengang Pharmazie an der Universität Leipzig entwickelt.''')
    st.caption('''Konzeption und Umsetzung: Nele Sebök, Tanjana Harings''')
    st.caption('''Kontakt: Tanjana Harings, Apothekerin, Wissenschaftliche Mitarbeiterin, Klinische Pharmazie, Institut für Pharmazie, Medizinische Fakultät, Universität Leipzig, tanjana.harings@uni-leipzig.de''')
