import streamlit as st
import pandas as pd
import numpy as np

# 1. Configuração de Estética e Layout
st.set_page_config(
    page_title="Fluxo de Caixa - Contas a Pagar", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# CSS Customizado para Layout "Encantador"
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        background-color: #0E1117;
    }

    /* Títulos e Headers */
    h1 { color: #FFFFFF; font-weight: 700; letter-spacing: -1px; }
    
    /* Customização dos Cards de Métricas */
    div[data-testid="metric-container"] {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 25px;
        border-radius: 16px;
        backdrop-filter: blur(10px);
    }
    div[data-testid="stMetricValue"] { color: #38bdf8; font-size: 32px !important; }
    div[data-testid="stMetricLabel"] { color: #94a3b8; font-size: 14px; text-transform: uppercase; }

    /* Estilização das Abas */
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

    /* Barra Lateral */
    section[data-testid="stSidebar"] {
        background-color: #111827;
        border-right: 1px solid rgba(255, 255, 255, 0.05);
    }
    </style>
    """, unsafe_allow_html=True)

# Funções de Suporte
def format_brl(val):
    return f"R$ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def processar_excel(file):
    try:
        if file.name.endswith('.csv'):
            df = pd.read_csv(file)
        else:
            df = pd.read_excel(file)
        
        c_data, c_cat, c_valor = 'Data de pagamento', 'Categoria', 'Valor categoria/centro de custo'
        
        # Limpeza e Conversão
        def limpar(v):
            if isinstance(v, str):
                v = v.replace('R$', '').replace('.', '').replace(' ', '').replace(',', '.')
                try: return float(v)
                except: return 0.0
            return float(v)

        df[c_valor] = df[c_valor].apply(limpar)
        df[c_data] = pd.to_datetime(df[c_data], dayfirst=True, errors='coerce')
        df = df.dropna(subset=[c_data]).sort_values(c_data)
        
        # Colunas de Tempo para Filtro e Projeção
        df['Mes_Ano'] = df[c_data].dt.strftime('%m/%Y')
        df['Periodo_Sort'] = df[c_data].dt.to_period('M')
        
        # Lógica de Classificação
        termos_fiscal = ['ISS', 'IRPJ', 'CSLL', 'PIS', 'COFINS', 'RETIDO', 'IMPOSTO', 'TAXA']
        df['Natureza'] = df[c_cat].apply(
            lambda x: '🏛️ Fiscal' if any(t in str(x).upper() for t in termos_fiscal) else '⚙️ Operacional'
        )
        return df
    except Exception as e:
        st.error(f"Erro no processamento: {e}")
        return None

# --- SIDEBAR ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3135/3135706.png", width=60)
    st.markdown("### Painel de Controle")
    uploaded_file = st.file_uploader("Subir planilha Excel/CSV", type=['xlsx', 'xls', 'csv'])
    st.divider()
    st.caption("v2.1 - CFO Strategic Intelligence")

# --- CONTEÚDO PRINCIPAL ---
if uploaded_file:
    df_raw = processar_excel(uploaded_file)
    
    if df_raw is not None:
        c_v = 'Valor categoria/centro de custo'
        
        # Título
        st.title("Fluxo de Caixa Contas a Pagar")
        
        # --- FILTRO DE MÊS NO TOPO ---
        lista_meses = sorted(df_raw['Mes_Ano'].unique(), key=lambda x: pd.to_datetime(x, format='%m/%Y'))
        lista_meses.insert(0, "Todos os Meses")
        
        col_f1, col_f2 = st.columns([1, 3])
        with col_f1:
            mes_selecionado = st.selectbox("📅 Selecione o Período:", lista_meses)
        
        # Aplicar Filtro
        if mes_selecionado != "Todos os Meses":
            df = df_raw[df_raw['Mes_Ano'] == mes_selecionado].copy()
        else:
            df = df_raw.copy()

        st.write("---")

        # KPIs Principais (Baseados no Filtro)
        total_out = df[df[c_v] < 0][c_v].sum()
        fiscal_out = df[df['Natureza'] == '🏛️ Fiscal'][c_v].sum()
        op_out = df[df['Natureza'] == '⚙️ Operacional'][c_v].sum()

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Saída Total", format_brl(abs(total_out)))
        
        # Evitar divisão por zero se não houver saídas
        perc_fiscal = abs(fiscal_out/total_out)*100 if total_out != 0 else 0
        m2.metric("Custos Fiscais", format_brl(abs(fiscal_out)), f"{perc_fiscal:.1f}%")
        
        m3.metric("Custos Operacionais", format_brl(abs(op_out)))
        m4.metric("Aging (Itens)", f"{len(df)} contas")

        st.write("##")

        # Abas de Análise
        tab_proj, tab_burn, tab_pareto, tab_data, tab_guide = st.tabs([
            "📊 Projeção Mensal", "🔥 Cash Burn", "🎯 Pareto 80/20", "📋 Detalhamento", "📖 Guia"
        ])

        with tab_proj:
            st.subheader("Evolução Histórica Mensal")
            # Agrupamento por período real (usando a base bruta para ver o todo)
            proj_mensal = df_raw[df_raw[c_v] < 0].groupby('Periodo_Sort')[c_v].sum().abs().reset_index()
            proj_mensal['Mês/Ano'] = proj_mensal['Periodo_Sort'].astype(str)
            
            c_p1, c_p2 = st.columns([2, 1])
            with c_p1:
                st.bar_chart(proj_mensal.set_index('Mês/Ano')[c_v], color="#38bdf8")
            with c_p2:
                st.markdown("#### Totais por Mês")
                st.dataframe(
                    proj_mensal[['Mês/Ano', c_v]].style.format({c_v: "R$ {:,.2f}"}),
                    hide_index=True,
                    use_container_width=True
                )

        with tab_burn:
            st.subheader("Projeção de Consumo de Caixa (Acumulado)")
            if not df.empty:
                burn = df.groupby('Data de pagamento')[c_v].sum().cumsum().reset_index()
                st.area_chart(burn.set_index('Data de pagamento'), color="#f43f5e")
            else:
                st.info("Selecione um período com dados para visualizar o gráfico.")

        with tab_pareto:
            st.subheader("Análise de Pareto (Maiores Gastos)")
            saidas = df[df[c_v] < 0]
            if not saidas.empty:
                p_df = saidas.groupby('Categoria')[c_v].sum().abs().sort_values(ascending=False).reset_index()
                p_df['% Acum.'] = (p_df[c_v].cumsum() / p_df[c_v].sum()) * 100
                
                c_left, c_right = st.columns([1, 2])
                with c_left:
                    st.dataframe(p_df[p_df['% Acum.'] <= 85][['Categoria', c_v]].style.format({c_v: "R$ {:,.2f}"}), hide_index=True)
                with c_right:
                    st.bar_chart(p_df.head(10).set_index('Categoria')[c_v], color="#38bdf8")

        with tab_data:
            st.subheader("Lista de Lançamentos")
            st.data_editor(
                df,
                column_config={
                    c_v: st.column_config.NumberColumn("Valor", format="R$ %.2f"),
                    "Data de pagamento": st.column_config.DateColumn("Vencimento", format="DD/MM/YYYY"),
                },
                hide_index=True, use_container_width=True
            )

        with tab_guide:
            st.markdown("""
            ### 🧭 Guia de Leitura Estratégica
            - **Projeção Mensal:** Permite comparar se os gastos estão subindo ou descendo ao longo dos meses.
            - **Cash Burn:** Observe a inclinação da curva. Se a linha cair bruscamente, você tem um pico de saída de caixa naquele dia.
            - **Pareto:** Foque sua energia nas categorias que aparecem nesta aba; elas são responsáveis por quase todo o seu gasto.
            - **Natureza:** Separamos o que é imposto do que é operação para você entender o custo tributário do seu negócio.
            """)

else:
    # Estado Vazio
    st.title("Fluxo de Caixa Contas a Pagar")
    st.info("Aguardando upload de arquivo para gerar inteligência estratégica.")
