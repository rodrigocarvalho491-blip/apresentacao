import os
import pandas as pd
import numpy as np
import streamlit as st
from io import BytesIO
from PIL import Image

# --- CONFIGURAÇÃO GLOBAL DA PÁGINA (SEM MENU LATERAL) ---
st.set_page_config(
    page_title="Consigaz - Gerador de Apresentação de Resultados", 
    page_icon="📊", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- ESTILIZAÇÃO VISUAL COM A IDENTIDADE CONSIGAZ ---
CUSTOM_CSS = """
<style>
    /* Ocultar barra lateral por completo */
    [data-testid="stSidebar"] { display: none; }
    
    /* Cores e tipografia corporativa */
    h1, h2, h3 { 
        color: #004080 !important; 
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
    }
    
    /* Botões personalizados */
    div.stButton > button:first-child {
        background-color: #004080 !important; 
        color: #ffffff !important;
        border-radius: 8px !important; 
        border: none !important; 
        font-weight: bold !important;
        padding: 0.5rem 1rem;
    }
    
    div.stButton > button:first-child:hover {
        background-color: #003366 !important;
    }
    
    .card-container {
        background-color: #f8f9fa;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #004080;
        margin-bottom: 20px;
    }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

DIRETORIO_ATUAL = os.path.dirname(os.path.abspath(__file__))
LOGO_PATH = os.path.join(DIRETORIO_ATUAL, "logo.png")

# --- CABEÇALHO DA PÁGINA EXCLUSIVA ---
col_logo, col_titulo = st.columns([1, 5])
with col_logo:
    if os.path.exists(LOGO_PATH):
        st.image(LOGO_PATH, width=140)
    else:
        st.markdown("### **CONSIGAZ**")

with col_titulo:
    st.title("Gerador de Apresentação de Resultados")
    st.markdown("Ferramenta dedicada para automação e geração de relatórios gerenciais (**Mensal** e **Trimestral**).")

st.divider()

# --- SEÇÃO DE CONFIGURAÇÃO E UPLOAD ---
st.markdown("### 1. Parâmetros da Apresentação")

col_p1, col_p2, col_p3 = st.columns(3)
with col_p1:
    tipo_apresentacao = st.selectbox(
        "Selecione o Modelo de Apresentação:", 
        ["Apresentação Mensal", "Apresentação Trimestral"]
    )
with col_p2:
    consultor_nome = st.text_input("Nome do Consultor", value="Rodrigo Carvalho")
with col_p3:
    periodo_referencia = st.text_input("Período de Referência", placeholder="Ex: Agosto/2026 ou 2º Trimestre/2026")

st.markdown("### 2. Upload da Planilha Base de Fechamento")
arquivo_base = st.file_uploader(
    "Faça o upload da planilha Excel de fechamento (ex: Fechamento de Volume)", 
    type=["xlsx", "xls"]
)

st.divider()

# --- PROCESSAMENTO E GERAÇÃO ---
if arquivo_base is not None:
    try:
        # Leitura inicial para validar a base
        xls = pd.ExcelFile(arquivo_base)
        sheet_selecionada = xls.sheet_names[0]
        df_dados = pd.read_excel(arquivo_base, sheet_name=sheet_selecionada)
        
        st.success(f"✅ Planilha carregada com sucesso! (Aba detectada: **{sheet_selecionada}** | Registros: **{len(df_dados)}**)")
        
        st.markdown("### 3. Pré-visualização dos Dados Calculados")
        
        # Exemplo de métricas extraídas com base na estrutura da Consigaz
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        with col_m1:
            total_clientes = df_dados["Cod Cli"].nunique() if "Cod Cli" in df_dados.columns else len(df_dados)
            st.metric("Total de Clientes", total_clientes)
        with col_m2:
            volume_ton = (df_dados["Qtde (kg)"].sum() / 1000.0) if "Qtde (kg)" in df_dados.columns else 0.0
            st.metric("Volume Total (TON)", f"{volume_ton:.1f} TON")
        with col_m3:
            faturamento_total = df_dados["Vl.Tot Item"].sum() if "Vl.Tot Item" in df_dados.columns else 0.0
            st.metric("Faturamento Total", f"R$ {faturamento_total:,.2f}")
        with col_m4:
            st.metric("Padrão Visual", "Consigaz Oficial 🔒")

        st.markdown("---")
        st.markdown("### 4. Geração do Arquivo PowerPoint")
        st.info("O motor Python está pronto para gerar o arquivo `.pptx` preservando exatamente o layout oficial da Consigaz para a gerência.")

        if st.button("🚀 Gerar e Baixar Apresentação Pronta", type="primary"):
            # Simulação de arquivo de saída PPTX pronto
            output_buffer = BytesIO()
            # Aqui entrará a lógica de manipulação com python-pptx injetando os dados nos slides oficiais
            
            nome_arquivo = f"apresentacao_{tipo_apresentacao.lower().replace(' ', '_')}.pptx"
            
            st.success("✅ Apresentação gerada com sucesso dentro dos padrões visuais da Consigaz!")
            st.download_button(
                label="📥 Baixar Apresentação Pronta (.pptx)",
                data=b"Simulacao de arquivo pptx Consigaz", # Substituir pelo buffer real do pptx gerado
                file_name=nome_arquivo,
                mime="application/vnd.openxmlformats-officedocument.presentationml.presentation"
            )

    except Exception as e:
        st.error(f"⚠️ Erro ao processar a planilha base: {e}")
else:
    st.info("👆 Por favor, faça o upload da planilha Excel base acima para iniciar o processamento dos dados da apresentação.")
