import streamlit as st
import pandas as pd
import numpy as np

# 1. Configuração de Estética e Layout
st.set_page_config(
    page_title="Fluxo de Caixa - Contas a Pagar", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# CSS Customizado
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; background-color: #0E1117; }
    h1 { color: #FFFFFF; font-weight: 700; letter-spacing: -1px; }
    div[data-testid="metric-container"] {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 25px;
        border-radius: 16px;
        backdrop-filter: blur(10px);
    }
    div[data-testid="stMetricValue"] { color: #38bdf8; font-size: 32px !important; }
    div[data-testid="stMetricLabel"] { color: #94a3b8; font-size: 14px; text-transform: uppercase; }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; padding-bottom: 20px; }
    .stTabs [data-baseweb="tab"] {
        background-color: transparent;
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 8px;
        color: #94a3b8;
        padding: 8px 16px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #38bdf8 !important;
        color: #0E1117 !important;
        border: 1px solid #38bdf8;
    }
    section[data-testid="stSidebar"] {
        background-color: #111827;
        border-right: 1px solid rgba(255, 255, 255, 0.05);
    }
    </style>
    """, unsafe_allow_html=True)

def format_brl(val):
    return f"R$ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def processar_dados(file):
    try:
        # Tenta ler como CSV primeiro (não exige openpyxl)
        if file.name.endswith('.csv'):
            df = pd.read_csv(file)
        else:
            # Se for Excel, ele VAI pedir o openpyxl. 
            # Para evitar o erro, avisamos o usuário ou convertemos o fluxo.
            df = pd.read_excel(file)
        
        c_data, c_cat, c_valor = 'Data de pagamento', 'Categoria', 'Valor categoria/centro de custo'
        
        def limpar(v):
            if isinstance(v, str):
                v = v.replace('R$', '').replace('.', '').replace(' ', '').replace(',', '.')
                try: return float(v)
                except: return 0.0
            return float(v) if pd.notnull(v) else 0.0

        df[c_valor] = df[c_valor].apply(limpar)
        df[c_data] = pd.to_datetime(df[c_data], dayfirst=True, errors='coerce')
        df = df.dropna(subset=[c_data]).sort_values(c_data)
        
        df['Mes_Ano'] = df[c_data].dt.strftime('%m/%Y')
        df['Periodo_Sort'] = df[c_data].dt.to_period('M')
        
        termos_fiscal = ['ISS', 'IRPJ', 'CSLL', 'PIS', 'COFINS', 'RETIDO', 'IMPOSTO', 'TAXA']
        df['Natureza'] = df[c_cat].apply(
            lambda x: '🏛️ Fiscal' if any(t in str(x).upper() for t in termos_fiscal) else '⚙️ Operacional'
        )
        return df
    except Exception as e:
        if "openpyxl" in str(e):
            st.error("⚠️ Este sistema prefere arquivos **.CSV**. Para usar Excel (.xlsx), a biblioteca 'openpyxl' é obrigatória no servidor.")
        else:
            st.error(f"Erro: {e}")
        return None

# --- SIDEBAR ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3135/3135706.png", width=60)
    st.markdown("### Painel de Controle")
    uploaded_file = st.file_uploader("Subir planilha (Recomendado: .CSV)", type=['csv', 'xlsx'])
    st.divider()
    st.caption("v2.2 - CFO Strategic Intelligence")

# --- CONTEÚDO PRINCIPAL ---
if uploaded_file:
    df_raw = processar_dados(uploaded_file)
    
    if df_raw is not None:
        c_v = 'Valor categoria/centro de custo'
        st.title("Fluxo de Caixa Contas a Pagar")
        
        # Filtro de Mês no Topo
        lista_meses = sorted(df_raw['Mes_Ano'].unique(), key=lambda x: pd.to_datetime(x, format='%m/%Y'))
        lista_meses.insert(0, "Todos os Meses")
        
        col_f1, col_f2 = st.columns([1, 3])
        with col_f1:
            mes_selecionado = st.selectbox("📅 Selecione o Período:", lista_meses)
        
        df = df_raw[df_raw['Mes_Ano'] == mes_selecionado].copy() if mes_selecionado != "Todos os Meses" else df_raw.copy()

        st.write("---")

        # KPIs
        total_out = df[df[c_v] < 0][c_v].sum()
        fiscal_out = df[df['Natureza'] == '🏛️ Fiscal'][c_v].sum()
        op_out = df[df['Natureza'] == '⚙️ Operacional'][c_v].sum()

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Saída Total", format_brl(abs(total_out)))
        perc_fiscal = abs(fiscal_out/total_out)*100 if total_out != 0 else 0
        m2.metric("Custos Fiscais", format_brl(abs(fiscal_out)), f"{perc_fiscal:.1f}%")
        m3.metric("Custos Operacionais", format_brl(abs(op_out)))
        m4.metric("Aging (Itens)", f"{len(df)} contas")

        st.write("##")

        # Abas
        tab_proj, tab_burn, tab_pareto, tab_data = st.tabs(["📊 Projeção Mensal", "🔥 Cash Burn", "🎯 Pareto 80/20", "📋 Detalhamento"])

        with tab_proj:
            st.subheader("Evolução Histórica Mensal")
            proj_mensal = df_raw[df_raw[c_v] < 0].groupby('Periodo_Sort')[c_v].sum().abs().reset_index()
            proj_mensal['Mês/Ano'] = proj_mensal['Periodo_Sort'].astype(str)
            
            c_p1, c_p2 = st.columns([2, 1])
            with c_p1:
                st.bar_chart(proj_mensal.set_index('Mês/Ano')[c_v], color="#38bdf8")
            with c_p2:
                st.markdown("#### Totais por Mês")
                st.dataframe(proj_mensal[['Mês/Ano', c_v]].style.format({c_v: "R$ {:,.2f}"}), hide_index=True, use_container_width=True)

        with tab_burn:
            st.subheader("Consumo Acumulado")
            if not df.empty:
                burn = df.groupby('Data de pagamento')[c_v].sum().cumsum().reset_index()
                st.area_chart(burn.set_index('Data de pagamento'), color="#f43f5e")

        with tab_pareto:
            st.subheader("Pareto (Maiores Gastos)")
            saidas = df[df[c_v] < 0]
            if not saidas.empty:
                p_df = saidas.groupby('Categoria')[c_v].sum().abs().sort_values(ascending=False).reset_index()
                p_df['% Acum.'] = (p_df[c_v].cumsum() / p_df[c_v].sum()) * 100
                st.dataframe(p_df[p_df['% Acum.'] <= 85][['Categoria', c_v]].style.format({c_v: "R$ {:,.2f}"}), use_container_width=True)

        with tab_data:
            st.subheader("Lançamentos")
            st.data_editor(df, column_config={c_v: st.column_config.NumberColumn("Valor", format="R$ %.2f"), "Data de pagamento": st.column_config.DateColumn("Vencimento", format="DD/MM/YYYY")}, hide_index=True, use_container_width=True)
else:
    st.title("Fluxo de Caixa Contas a Pagar")
    st.info("Suba um arquivo CSV para começar.")

