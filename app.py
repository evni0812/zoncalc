import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from datetime import date

st.set_page_config(page_title="Zonnepanelen Terugverdientijd Calculator", layout="wide")

st.title("🌞 Zonnepanelen Terugverdientijd Calculator")

# Sidebar for inputs
with st.sidebar:
    st.header("Invoergegevens")
    
    # 0. Algemene instellingen
    with st.expander("⚙️ Algemene instellingen", expanded=True):
        startdatum = st.date_input("Startdatum berekening", value=date(2025, 1, 1))
        saldering_einddatum = st.date_input("Einddatum saldering", value=date(2027, 1, 1))
        jaarlijks_verbruik = st.number_input("Jaarlijks stroomverbruik huishouden (kWh)", value=3600, step=100)
        vervangingstermijn = st.number_input("Vervangingstermijn zonnepanelen (jaren)", value=25, step=1, min_value=10, max_value=40)
    
    # 1. Kosten
    with st.expander("💰 Kosten", expanded=True):
        aanschafkosten = st.number_input("Aanschafkosten (EUR)", value=4500, step=100)
        omvormer_kosten = st.number_input("Kosten vervanging omvormer (EUR)", value=1200, step=100)
        omvormer_afschrijving = st.number_input("Afschrijftijd omvormer (jaren)", value=12, step=1)

    # 2. Opbrengsten
    with st.expander("📈 Opbrengsten", expanded=True):
        vermogen_per_paneel = st.number_input("Geïnstalleerd vermogen per paneel (Wp)", value=400, step=10)
        aantal_panelen = st.number_input("Aantal zonnepanelen", value=10, step=1)
        opbrengst_per_wp = st.number_input("Opbrengst per wattpiek per jaar (kWh/Wp/jaar)", value=0.85, step=0.01)
        degradatie = st.number_input("Degradering opbrengst (% per jaar)", value=0.70, step=0.1) / 100
        eigen_gebruik = st.number_input("Percentage eigen gebruik (%)", value=30, step=1) / 100

    # 3. Energieprijzen en belastingen
    with st.expander("⚡ Energieprijzen", expanded=True):
        leveringstarief = st.number_input("Leveringstarief elektriciteit ex. BTW (EUR/kWh)", value=0.15, step=0.01)
        prijsstijging = st.number_input("Elektriciteitsprijsstijging (% per jaar)", value=1.38, step=0.1) / 100
        prijs_vanaf_2035 = st.number_input("Elektriciteitsprijs vanaf 2035 (EUR/kWh)", value=0.18, step=0.01)
        
        st.markdown("---")
        
        energiebelasting = st.number_input("Energiebelasting (EUR/kWh)", value=0.09, step=0.01)
        belasting_trend = st.number_input("Energiebelasting trend (% per jaar)", value=-1.74, step=0.1) / 100
        belasting_vanaf_2035 = st.number_input("Energiebelasting vanaf 2035 (EUR/kWh)", value=0.09, step=0.01)
    
    with st.expander("💸 Terugleververgoeding", expanded=True):
        btw = st.number_input("BTW-tarief (%)", value=21, step=1) / 100
        teruglever_percentage = st.number_input("Terugleververgoeding (% van leveringstarief)", value=25, step=5) / 100
        terugleverkosten = st.number_input("Terugleverkosten tot 2027 (EUR/jaar)", value=274, step=10)

# Berekeningen
jaren = range(1, vervangingstermijn + 1)  # Analyse periode op basis van vervangingstermijn
totaal_vermogen = vermogen_per_paneel * aantal_panelen

# Jaarlijkse opbrengst berekening
opbrengsten_saldering = []
opbrengsten_eigen_verbruik = []
opbrengsten_teruglevering = []
kosten = []
cumulatief = [-aanschafkosten]  # Start met initiële investering

for jaar in jaren:
    huidige_datum = date(startdatum.year + jaar - 1, startdatum.month, startdatum.day)
    saldering_actief = huidige_datum < saldering_einddatum
    
    # Degradatie van opbrengst
    degradatie_factor = (1 - degradatie) ** (jaar - 1)
    jaarlijkse_opbrengst = totaal_vermogen * opbrengst_per_wp * degradatie_factor
    
    # Prijzen voor dit jaar
    if huidige_datum.year < 2035:
        actueel_leveringstarief = leveringstarief * (1 + prijsstijging) ** (jaar - 1)
        actuele_energiebelasting = energiebelasting * (1 + belasting_trend) ** (jaar - 1)
    else:
        actueel_leveringstarief = prijs_vanaf_2035
        actuele_energiebelasting = belasting_vanaf_2035
    
    # Berekening opbrengsten
    prijs_met_belasting = (actueel_leveringstarief + actuele_energiebelasting) * (1 + btw)
    
    # Bereken eerst eigen verbruik (dit is altijd hetzelfde)
    opbrengst_eigen_verbruik = jaarlijkse_opbrengst * eigen_gebruik * prijs_met_belasting
    
    if saldering_actief:
        # Met saldering: teruggeleverde stroom tegen vol tarief, maar maximaal tot jaarlijks verbruik
        teruggeleverde_stroom = jaarlijkse_opbrengst * (1 - eigen_gebruik)
        direct_verbruik = jaarlijkse_opbrengst * eigen_gebruik
        
        # Bereken hoeveel er nog gesaldeerd kan worden
        nog_te_salderen = max(0, jaarlijks_verbruik - direct_verbruik)
        gesaldeerde_stroom = min(teruggeleverde_stroom, nog_te_salderen)
        
        # Wat overblijft krijgt terugleververgoeding
        overgebleven_stroom = max(0, teruggeleverde_stroom - nog_te_salderen)
        
        opbrengst_saldering = gesaldeerde_stroom * prijs_met_belasting
        opbrengst_teruglevering = overgebleven_stroom * actueel_leveringstarief * teruglever_percentage
    else:
        # Na saldering: teruglevering tegen teruglevertarief
        opbrengst_saldering = 0
        opbrengst_teruglevering = jaarlijkse_opbrengst * (1 - eigen_gebruik) * actueel_leveringstarief * teruglever_percentage
    
    # Terugleverkosten tot einddatum saldering
    extra_kosten = terugleverkosten if huidige_datum < saldering_einddatum else 0
    
    # Omvormer vervanging (niet als panelen binnen 10 jaar vervangen worden)
    jaren_tot_vervanging = vervangingstermijn - jaar
    if jaar % omvormer_afschrijving == 0 and jaren_tot_vervanging > 10:
        extra_kosten += omvormer_kosten
    
    jaarlijkse_opbrengst_eur = opbrengst_eigen_verbruik + opbrengst_saldering + opbrengst_teruglevering - extra_kosten
    opbrengsten_saldering.append(opbrengst_saldering)
    opbrengsten_eigen_verbruik.append(opbrengst_eigen_verbruik)
    opbrengsten_teruglevering.append(opbrengst_teruglevering)
    kosten.append(-extra_kosten)
    
    cumulatief.append(cumulatief[-1] + jaarlijkse_opbrengst_eur)

# Terugverdientijd berekening
terugverdientijd = None
for i, cum in enumerate(cumulatief[1:], 1):  # Start vanaf jaar 1
    if cum >= 0:
        # Lineaire interpolatie voor nauwkeurigere schatting
        vorig_bedrag = cumulatief[i-1]
        huidig_bedrag = cum
        fractie = abs(vorig_bedrag) / (abs(vorig_bedrag) + abs(huidig_bedrag))
        terugverdientijd = i - 1 + fractie
        break

# Visualisatie
fig = go.Figure()

# Opbrengsten lijnen
fig.add_trace(go.Bar(
    x=list(range(1, vervangingstermijn + 1)),
    y=opbrengsten_saldering,
    name='Opbrengst saldering',
    marker_color='#2ecc71'
))

fig.add_trace(go.Bar(
    x=list(range(1, vervangingstermijn + 1)),
    y=opbrengsten_eigen_verbruik,
    name='Opbrengst eigen verbruik',
    marker_color='#3498db'
))

fig.add_trace(go.Bar(
    x=list(range(1, vervangingstermijn + 1)),
    y=opbrengsten_teruglevering,
    name='Opbrengst teruglevering',
    marker_color='#f1c40f'
))

fig.add_trace(go.Bar(
    x=list(range(1, vervangingstermijn + 1)),
    y=kosten[:-1],  # Exclude initial investment
    name='Kosten',
    marker_color='#e74c3c'
))

# Cumulatieve lijn
fig.add_trace(go.Scatter(
    x=list(range(vervangingstermijn + 1)),
    y=cumulatief,
    name='Cumulatief resultaat',
    line=dict(color='#2c3e50', width=3)
))

# Break-even lijn
fig.add_hline(y=0, line_dash="dash", line_color="gray")

# Layout
fig.update_layout(
    title='Terugverdientijd Zonnepanelen',
    xaxis_title='Jaren',
    yaxis_title='Resultaat (EUR)',
    hovermode='x unified',
    template='plotly_white',
    barmode='relative'
)

# Toon resultaten
col1, col2 = st.columns(2)

with col1:
    st.metric(
        "Terugverdientijd",
        f"{terugverdientijd:.1f} jaar" if terugverdientijd else "Niet terugverdiend binnen 25 jaar"
    )
    
with col2:
    st.metric(
        "Totale opbrengst na 25 jaar",
        f"€ {int(cumulatief[-1]):,}".replace(",", ".")
    )

st.plotly_chart(fig, use_container_width=True)

# Aannames en uitgangspunten
st.subheader("ℹ️ Aannames en uitgangspunten")

with st.expander("💰 Kosten aannames"):
    st.markdown("""
    - Aanschafkosten: €{:,.0f}
    - Omvormer vervangingskosten: €{:,.0f}
    - Omvormer wordt elke {} jaar vervangen
    """.format(aanschafkosten, omvormer_kosten, omvormer_afschrijving))

with st.expander("🌞 Opbrengst aannames"):
    st.markdown("""
    - Vermogen per paneel: {} Wp
    - Aantal panelen: {}
    - Opbrengst per Wp per jaar: {:.2f} kWh
    - Jaarlijkse degradatie: {:.1f}%
    - Eigen gebruik: {:.0f}%
    """.format(vermogen_per_paneel, aantal_panelen, opbrengst_per_wp, degradatie*100, eigen_gebruik*100))

with st.expander("⚡ Energieprijzen aannames"):
    st.markdown("""
    - Leveringstarief: €{:.2f}/kWh
    - Jaarlijkse prijsstijging: {:.1f}%
    - Prijs vanaf 2035: €{:.2f}/kWh
    - Energiebelasting: €{:.2f}/kWh
    - Energiebelasting trend: {:.1f}%
    - Energiebelasting vanaf 2035: €{:.2f}/kWh
    """.format(leveringstarief, prijsstijging*100, prijs_vanaf_2035, 
               energiebelasting, belasting_trend*100, belasting_vanaf_2035))

with st.expander("💸 Terugleververgoeding aannames"):
    st.markdown("""
    - BTW-tarief: {:.0f}%
    - Terugleververgoeding: {:.0f}% van leveringstarief
    - Terugleverkosten tot 2027: €{:.0f}/jaar
    """.format(btw*100, teruglever_percentage*100, terugleverkosten))

# Extra informatie
st.subheader("📊 Jaarlijkse details")
df = pd.DataFrame({
    'Jaar': list(range(vervangingstermijn + 1)),
    'Cumulatief resultaat': [round(x, 2) for x in cumulatief],
    'Opbrengst saldering': [0] + [round(x, 2) for x in opbrengsten_saldering],
    'Opbrengst eigen verbruik': [0] + [round(x, 2) for x in opbrengsten_eigen_verbruik],
    'Opbrengst teruglevering': [0] + [round(x, 2) for x in opbrengsten_teruglevering],
    'Kosten': [round(-aanschafkosten, 2)] + [round(x, 2) for x in kosten]
})

st.dataframe(df, use_container_width=True) 