import streamlit as st
import pandas as pd
from pathlib import Path

#befehl für terminal um app lokal zu starten: streamlit run app/src/app.py

#grundeinstellung für streamlit
st.set_page_config(page_title="Übungsapotheke", layout="wide")

#PFADE
APP_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = APP_DIR / "data"
IMAGES_DIR = DATA_DIR / "images"
DATA_FULL_PATH = DATA_DIR / "data_full.xlsx"
EVIDENCE_PATH = DATA_DIR / "data_evidence.xlsx"

#HILFSFUNKTIONEN
#text vereinheitlichen: string, trimm, klein
def norm(text) -> str:
    return str(text).strip().lower()

#text an semikolon trennen und als liste zurückgeben
def split_semicolon(text) -> list:
    parts = str(text).split(";")
    clean = []
    for p in parts:
        p = p.strip()
        if p != "":
            clean.append(p)
    return clean

#bild zur pzn im IMAGES_DIR finden
def find_image_for_pzn(pzn):
    pzn = str(pzn).strip()
    matches = list(IMAGES_DIR.glob(f"{pzn}.*"))
    if len(matches) > 0:
        return matches[0]
    return None

#DATEN LADEN
@st.cache_data
def load_data():
    df = pd.read_excel(DATA_FULL_PATH, dtype={"pzn": str})
    #spalten vereinheitlichen
    df.columns = [norm(c) for c in df.columns]
    #pzn sauber formatieren (8-stellig, führende Nullen)
    df["pzn"] = df["pzn"].astype(str).str.strip().str.zfill(8)
    #plant normalisieren
    if "plant" in df.columns:
        df["plant"] = df["plant"].fillna("").apply(norm)

    #hilfslisten für filter für indikation und wirkstoffe
    ind_lists = []
    drug_lists = []

    for _, row in df.iterrows():
        inds = split_semicolon(row.get("indication", ""))
        inds_norm = []
        for i in inds:
            inds_norm.append(norm(i))
        ind_lists.append(inds_norm)

        drugs = split_semicolon(row.get("drug", ""))
        drugs_norm = []
        for d in drugs:
            drugs_norm.append(norm(d))
        drug_lists.append(drugs_norm)

    df["ind_list"] = ind_lists
    df["drug_list"] = drug_lists

    return df

@st.cache_data
def load_evidence():
    ev = pd.read_excel(EVIDENCE_PATH)
    #spalten vereinheitlichen
    ev.columns = [norm(c) for c in ev.columns]

    #long-format: pro indikation und pro wirkstoff eine zeile
    rows = []

    for _, r in ev.iterrows():
        ind_raw = r.get("ind", "")
        ind_key = norm(ind_raw)

        drug_raw = r.get("drug", "")
        drug_key = split_semicolon(drug_raw)

        for key in drug_key:
            new_row = dict(r)
            new_row["ind_key"] = ind_key
            new_row["drug_key"] = norm(key)
            rows.append(new_row)

    ev_long = pd.DataFrame(rows)
    return ev_long

#eigentlicher Start: daten laden
df = load_data()
ev_df = load_evidence()

#Titel, disclaimer, hinweis
st.title("Beratungshilfe: Selbstmedikation bei Erkältung")

with st.expander("Disclaimer"):
    st.write('''Die Auswahl der dargestellten Fertigarzneimittel dient der Orientierung über in der Selbstmedikation 
    bei Erkältungssymptomen verfügbaren Präparate und stellt weder eine Abgabeempfehlung noch eine Bewertung oder Bevorzugung einzelner Fertigarzneimittel dar.''')
    st.write(''' Diese Beratungshilfe wird ausschließlich zu Lehr- und Übungszwecken im Rahmen des Praktikums "Krankheitslehre I - Übungsapotheke" im 
    Studiengang Pharmazie an der Universität Leipzig eingesetzt.''')
    st.write('''Die enthaltenen Informationen basieren unter anderem auf Angaben aus Fachinformationen und sind ausschließlich für pharmazeutisches Fachpersonal bestimmt.
    Eine Weitergabe oder Anwendung der Inhalte außerhalb des genannten Lehrkontextes ist nicht vorgesehen.''')


st.info(":material/lightbulb: Nutze die Filter in der Seitenleiste, um passende Präparate zu finden. "
    "Wähle anschließend ein Präparat aus, um die Informationen zum Präparat anzuzeigen.")

#sidebar filter
st.sidebar.header("Filter")

#indikationen
all_inds = []
for inds in df["ind_list"]:
    for i in inds:
        all_inds.append(i)
all_inds_unique = sorted(list(set(all_inds)))

#für schöne anzeige: anfangsbuchstabe groß anzeigen
pretty_to_norm = {}
for i in all_inds_unique:
    pretty_to_norm[i.title()] = i

ind_options_pretty = sorted(pretty_to_norm.keys())

indikationen_filter_pretty = st.sidebar.multiselect(
    "Nach Indikationen filtern",
    options=ind_options_pretty,
    default=[]
)

indikationen_filter = []
for p in indikationen_filter_pretty:
    indikationen_filter.append(pretty_to_norm[p])

#daten nach indikationen filtern
df_ind = df.copy()
if len(indikationen_filter) > 0:
    selected = set(indikationen_filter)
    keep_rows = []

    for _, row in df_ind.iterrows():
        row_inds = row["ind_list"]
        found = False
        for i in row_inds:
            if i in selected:
                found = True
                break
        keep_rows.append(found)
    df_ind = df_ind[keep_rows]

#Darreichungsformen
drf_set = set()
for x in df_ind["drf"].dropna().tolist():
    drf_set.add(x)

ls_drf = sorted(list(drf_set))

#wenn der filter indikation geändert wird, auswahl drf nur behalten wenn noch gültig
prev = st.session_state.get("darreichung_filter", [])
prev_valid = []
for x in prev:
    if x in ls_drf:
        prev_valid.append(x)

darreichung_filter = st.sidebar.multiselect(
    "Nach Darreichungsformen filtern",
    options=ls_drf,
    default=prev_valid,
    key="darreichung_filter")

#pflanzlich filter
pflanzenwahl = st.sidebar.selectbox(
    "Nach pflanzlich/nicht pflanzlich filtern",
    options=["keine Auswahl", "Pflanzlich", "Nicht Pflanzlich"],
    index=0
)

st.sidebar.divider()
#freitextsuche
suchtext = st.sidebar.text_input("Freitextsuche (Präparat oder Wirkstoff)")

#wenn was in excel geändert wurde: reload data (nur anschalten, wenn App überarbeitet wird)
if st.sidebar.button("Daten neu laden"):
    st.cache_data.clear()
    st.rerun()

#FILTER ANWENDEN
filtered = df_ind.copy()

#drf
if len(darreichung_filter) > 0:
    keep_rows = []
    for _, row in filtered.iterrows():
        keep_rows.append(row.get("drf") in darreichung_filter)
    filtered = filtered[keep_rows]

#pflanzlich
if pflanzenwahl != "keine Auswahl":
    keep_rows = []
    for _, row in filtered.iterrows():
        plant_val = row["plant"]
        if pflanzenwahl == "Pflanzlich":
          keep_rows.append(row["plant"] == "ja")
        else:
            keep_rows.append(row["plant"] == "nein")
    filtered = filtered[keep_rows]

#freitextsuche
q = norm(suchtext)
if q != "":
    keep_rows = []
    for _, row in filtered.iterrows():
        name = norm(row.get("handelsname", ""))
        drugs = norm(row.get("drug", ""))
        hit = (q in name) or (q in drugs)
        keep_rows.append(hit)
    filtered = filtered[keep_rows]

st.caption(f"Gefundene Präparate: {len(filtered)}")

if len(filtered) == 0:
    st.info("Keine Präparate mit diesen Kriterien gefunden.")
    st.stop()

#DETAILANSICHT
def show_details(row: pd.Series):
    st.divider()
    st.header(row["handelsname"])

    col1, _, col3 = st.columns([3,1,2])

    with col1:
        tab_info, tab_guideline = st.tabs(["Details", "Leitlinie"])

        #tab infos zu präparat
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
            hinweise = row.get("hinweise", "")
            if isinstance(hinweise, str) and hinweise.strip() != "":
                st.write(f"Weitere Hinweise: {row['hinweise']}")
            st.divider()

            st.subheader(":material/error: Grenzen der Selbstmedikation")
            st.write(f"Anwendungsdauer ohne ärztliche Rücksprache: {row['grenzen']}")
            st.divider()

            st.subheader(":material/document_search: Quelle")
            st.write(f"{row['source']}")

        #tab zur leitlinien empfehlung
        with tab_guideline:
            ind_list = row["ind_list"]
            drug_list = row["drug_list"]

            #evidenz nach indikation filtern
            ev_ind_rows = []
            for _, erow in ev_df.iterrows():
                if erow["ind_key"] in ind_list:
                    ev_ind_rows.append(erow)

            if len(ev_ind_rows) == 0:
                st.info("Keine Leitlinie zur Indikation gefunden.")
                return

            ev_ind = pd.DataFrame(ev_ind_rows)

            #treffer für wirkstoff in evidenzdaten
            hits_rows = []

            for drug in drug_list:
                for _, erow in ev_ind.iterrows():
                    key = erow["drug_key"]
                    if key != "" and key in drug:
                        hits_rows.append(erow)
            if len(hits_rows) == 0:
                st.info("Die Wirkstoffe dieses Präparats werden nicht in der Leitlinie genannt.")
                return

            hits_df = pd.DataFrame(hits_rows).drop_duplicates()

            #gruppieren der treffer
            groups = {}
            for _, r in hits_df.iterrows():
                group_key = (r.get("ind"), r.get("ws_gruppe"), r.get("recom"), r.get("source"), r.get("stand"))
                drug_key = r.get("drug_key", "")

                if group_key not in groups:
                    groups[group_key] = set()
                groups[group_key].add(drug_key)

            #ausgabe vorbereiten
            output_rows = []
            for group_key, drug_key in groups.items():
                ind, ws_gruppe, recom, source, stand = group_key
                kws_pretty = []
                for x in sorted(list(drug_key)):
                    kws_pretty.append(x.title())
                drug_list_text = ", ".join(kws_pretty)
                output_rows.append((ind, ws_gruppe, recom, source, stand, drug_list_text))

            output_rows.sort(key=lambda x: (str(x[0]), str(x[1])))

            #anzeigen nach indikation
            current_ind = None
            for (ind, ws_gruppe, recom, source, stand, drug_list_text) in output_rows:
                if ind != current_ind:
                    st.markdown(f"**Bei {ind}:**")
                    current_ind = ind
                st.info(f"- {ws_gruppe} ({drug_list_text}) **{recom}** ({source}, Stand: {stand})")

    with col3:
        img_path = find_image_for_pzn(row["pzn"])
        if img_path:
            st.image(str(img_path), width="content", caption=f"Copyright: {row['image_cr']}")

#HAUPTBEREICH
st.subheader("Präparateübersicht")

display_df = filtered[["handelsname", "indication", "drug", "drf"]].rename(
    columns={
        "handelsname": "Name Fertigarzneimittel/Präparat",
        "indication": "Indikation",
        "drug": "Wirkstoff(e)",
        "drf": "Darreichungsform",
    }
)

st.dataframe(display_df, hide_index=True)

auswahl = st.selectbox("Präparat auswählen", options=filtered["handelsname"].unique())

if auswahl:
    row = filtered[filtered["handelsname"] == auswahl].iloc[0]
    show_details(row)

st.divider()

#infos zur app etc
st.caption('''© 2025 · Tanjana Harings · Lehrtool für das Praktikum „Krankheitslehre I - Übungsapotheke"''')

with st.expander("Über diese App"):
    st.caption('''Diese webbasierte Beratungshilfe wurde als Lehr- und Übungstool für das Praktikum "Krankheitslehre I - Übungsapotheke" im Studiengang Pharmazie an der Universität Leipzig entwickelt.''')
    st.caption('''Konzeption und Umsetzung: Nele Sebök, Tanjana Harings''')
    st.caption('''Kontakt: Tanjana Harings, Apothekerin, Wissenschaftliche Mitarbeiterin, Klinische Pharmazie, Institut für Pharmazie, Medizinische Fakultät, Universität Leipzig, tanjana.harings@uni-leipzig.de''')