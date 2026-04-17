import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px # Pense à faire 'pip install plotly' si besoin
import os

# Configuration
st.set_page_config(page_title="Pilotage Conseil", layout="wide")

DB_FILE = "missions.csv"

def load_data():
    if os.path.exists(DB_FILE):
        df = pd.read_csv(DB_FILE)
        df['Date_Debut'] = pd.to_datetime(df['Date_Debut'], errors='coerce')
        df['Date_Fin'] = pd.to_datetime(df['Date_Fin'], errors='coerce')
        return df
    else:
        return pd.DataFrame(columns=["Client", "Consultant", "Date_Debut", "Date_Fin", "TJM_HT", "Marge_Perc", "Statut"])

df = load_data()

st.title("🚀 Pilotage de l'Activité")

# --- GESTION DES DONNÉES (Calculs automatiques) ---
def calculer_jours_nets(row):
    try:
        d1 = row['Date_Debut'].date()
        d2 = row['Date_Fin'].date()
        if d2 <= d1: return 0
        # Calcul jours ouvrés - 7% de congés
        return round((np.busday_count(d1, d2) + 1) * 0.93, 1)
    except:
        return 0

# Appliquer les formules
df['Jours Nets'] = df.apply(calculer_jours_nets, axis=1)
df['CA Previsionnel (€)'] = df['Jours Nets'] * df['TJM_HT']
df['Marge (€)'] = df['CA Previsionnel (€)'] * (df['Marge_Perc'] / 100)

# --- CRÉATION DES ONGLETS ---
tab1, tab2, tab3 = st.tabs(["📋 Saisie des Missions", "📊 Forecast CA", "💰 Forecast Marge"])

# On définit les objectifs de CA et de Marge (40% du CA)
objectifs_ca = {
    1: 100000, 2: 200000, 3: 450000, 4: 590000, 5: 700000, 6: 800000, 
    7: 1100000, 8: 1300000, 9: 1400000, 10: 1700000, 11: 1900000, 12: 2000000
}
objectifs_marge = {k: v * 0.40 for k, v in objectifs_ca.items()}

with tab1:
    st.subheader("Gestion des missions")
    cols_vue = ["Client", "Consultant", "Date_Debut", "Date_Fin", "TJM_HT", "Marge_Perc", "Statut", "Jours Nets", "CA Previsionnel (€)", "Marge (€)"]
    edited_df = st.data_editor(
        df[cols_vue], use_container_width=True, num_rows="dynamic", hide_index=True,
        column_config={
            "Date_Debut": st.column_config.DateColumn("Début"),
            "Date_Fin": st.column_config.DateColumn("Fin"),
            "TJM_HT": st.column_config.NumberColumn("TJM HT", format="%d €"),
            "Marge_Perc": st.column_config.NumberColumn("% Marge", format="%d%%"),
            "Statut": st.column_config.SelectboxColumn("Statut", options=["Signé", "Prospect", "Terminé"]),
            "Jours Nets": st.column_config.NumberColumn("Jours (-7%)", disabled=True),
            "CA Previsionnel (€)": st.column_config.NumberColumn("CA Prévisionnel", format="%d €", disabled=True),
            "Marge (€)": st.column_config.NumberColumn("Marge (€)", format="%d €", disabled=True),
        }
    )
    if st.button("💾 Enregistrer toutes les modifications"):
        cols_sauvegarde = ["Client", "Consultant", "Date_Debut", "Date_Fin", "TJM_HT", "Marge_Perc", "Statut"]
        final_df = edited_df.dropna(subset=['Client'])
        final_df[cols_sauvegarde].to_csv(DB_FILE, index=False)
        st.success("Données enregistrées !")
        st.rerun()

# --- PRÉPARATION DES DONNÉES GRAPHIQUES ---
df_signe = edited_df[edited_df['Statut'] == "Signé"].copy()
forecast_data = []

if not df_signe.empty:
    for _, row in df_signe.iterrows():
        if pd.notnull(row['Date_Debut']) and pd.notnull(row['Date_Fin']):
            mois_range = pd.date_range(start=row['Date_Debut'], end=row['Date_Fin'], freq='MS')
            if len(mois_range) > 0:
                ca_mensuel = row['CA Previsionnel (€)'] / len(mois_range)
                marge_mensuelle = row['Marge (€)'] / len(mois_range)
                for m in mois_range:
                    forecast_data.append({"Mois": m, "CA": ca_mensuel, "Marge": marge_mensuelle})

if forecast_data:
    df_f = pd.DataFrame(forecast_data).groupby('Mois').sum().reset_index()
    import plotly.graph_objects as go

    # --- ONGLET 2 : FORECAST CA ---
    with tab2:
        st.subheader("Analyse du CA Cumulé vs Objectifs")
        df_f['Cumul_CA_Prec'] = df_f['CA'].cumsum().shift(1).fillna(0)
        df_f['Obj_CA'] = df_f['Mois'].dt.month.map(objectifs_ca)
        
        fig_ca = go.Figure()
        fig_ca.add_trace(go.Bar(x=df_f['Mois'], y=df_f['Cumul_CA_Prec'], name='Acquis', marker_color='#1F618D'))
        fig_ca.add_trace(go.Bar(x=df_f['Mois'], y=df_f['CA'], name='Nouveau CA', marker_color='#AED6F1',
                                text=df_f['CA'].cumsum(), texttemplate='%{text:.2s}€', textposition='outside'))
        fig_ca.add_trace(go.Scatter(x=df_f['Mois'], y=df_f['Obj_CA'], name='Objectif CA', line=dict(color='#E74C3C', dash='dash')))
        fig_ca.update_layout(barmode='stack', title="CA Cumulé", xaxis_tickformat='%b %Y')
        st.plotly_chart(fig_ca, use_container_width=True)

    # --- ONGLET 3 : FORECAST MARGE ---
    with tab3:
        st.subheader("Analyse de la Marge Cumulée vs Objectifs (40%)")
        df_f['Cumul_Marge_Prec'] = df_f['Marge'].cumsum().shift(1).fillna(0)
        df_f['Obj_Marge'] = df_f['Mois'].dt.month.map(objectifs_marge)
        
        fig_marge = go.Figure()
        fig_marge.add_trace(go.Bar(x=df_f['Mois'], y=df_f['Cumul_Marge_Prec'], name='Marge Acquise', marker_color='#145A32')) # Vert foncé
        fig_marge.add_trace(go.Bar(x=df_f['Mois'], y=df_f['Marge'], name='Nouvelle Marge', marker_color='#82E0AA', # Vert clair
                                   text=df_f['Marge'].cumsum(), texttemplate='%{text:.2s}€', textposition='outside'))
        fig_marge.add_trace(go.Scatter(x=df_f['Mois'], y=df_f['Obj_Marge'], name='Objectif Marge (40%)', line=dict(color='#E74C3C', dash='dash')))
        
        fig_marge.update_layout(barmode='stack', title="Marge Cumulée", xaxis_tickformat='%b %Y')
        st.plotly_chart(fig_marge, use_container_width=True)
        
        total_marge_ytd = df_f['Marge'].sum()
        st.metric("Marge Totale Sécurisée", f"{total_marge_ytd:,.0f} €", 
                  delta=f"{(total_marge_ytd/objectifs_marge[12]*100):.1f}% de l'objectif annuel")
else:
    with tab2: st.info("Aucune donnée 'Signé' pour le CA.")
    with tab3: st.info("Aucune donnée 'Signé' pour la Marge.")