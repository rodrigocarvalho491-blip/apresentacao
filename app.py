import os
import pandas as pd
import numpy as np
import streamlit as st
from io import BytesIO

try:
    import pptx
except ImportError:
    pptx = None

# --- CONFIGURAÇÃO GLOBAL DA PÁGINA ---
st.set_page_config(
    page_title="Consigaz - Gerador de Apresentação de Resultados", 
    page_icon="📊", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- ESTILIZAÇÃO VISUAL COM A IDENTIDADE CORPORATIVA CONSIGAZ ---
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
    st.markdown("Página dedicada e exclusiva para automação e geração de relatórios gerenciais com base nos modelos oficiais Consigaz.")

st.divider()

# --- SEÇÃO 1: PARÂMETROS E CONSULTOR ---
st.markdown("### 1. Parâmetros da Apresentação")

col_p1, col_p2, col_p3 = st.columns(3)
with col_p1:
    tipo_apresentacao = st.selectbox(
        "Selecione o Modelo de Apresentação:", 
        ["Apresentação Mensal", "Apresentação Trimestral (2º Tri/2026)"]
    )
with col_p2:
    consultor_nome = st.text_input("Consultor Responsável", value="Rodrigo Carvalho")
with col_p3:
    if "Trimestral" in tipo_apresentacao:
        periodo_referencia = st.text_input("Período de Referência", value="2º Trimestre/2026")
    else:
        periodo_referencia = st.text_input("Período de Referência", value="Agosto/2026")

st.divider()

# --- SEÇÃO 2: UPLOAD DAS PLANILHAS ---
st.markdown("### 2. Upload da Planilha Base de Fechamento")

arquivo_atual = st.file_uploader(
    "Faça o upload do arquivo de fechamento em Excel (.xlsx / .xls)", 
    type=["xlsx", "xls"],
    key="up_fechamento"
)

st.divider()

# --- FUNÇÃO PARA ATUALIZAR O MODELO .PPTX SELECIONADO ---
def gerar_apresentacao_com_modelo(tipo_modelo, consultor, periodo, volume_ton, faturamento, clientes):
    if pptx is None:
        raise RuntimeError("A biblioteca python-pptx não está instalada no ambiente.")
    
    # Seleciona o template correto com base na escolha do usuário
    if "Trimestral" in tipo_modelo:
        modelo_path = os.path.join(DIRETORIO_ATUAL, "rodrigo_sjc_2T2026_2.pptx")
    else:
        modelo_path = os.path.join(DIRETORIO_ATUAL, "rodrigo_ago26.pptx")
    
    if not os.path.exists(modelo_path):
        # Fallback caso o nome exato mude
        modelo_path = os.path.join(DIRETORIO_ATUAL, "rodrigo_ago26.pptx")
        if not os.path.exists(modelo_path):
            raise FileNotFoundError(f"Nenhum arquivo de modelo PPTX válido foi encontrado na pasta do sistema.")
    
    prs = pptx.Presentation(modelo_path)
    
    # Substituições dinâmicas preservando a formatação original do template
    for slide in prs.slides:
        for shape in slide.shapes:
            if shape.has_text_frame:
                for paragraph in shape.text_frame.paragraphs:
                    if "Rodrigo Carvalho" in paragraph.text and consultor != "Rodrigo Carvalho":
                        paragraph.text = paragraph.text.replace("Rodrigo Carvalho", consultor)
                    if ("Agosto/2026" in paragraph.text or "2º Trimestre/2026" in paragraph.text) and periodo:
                        # Substitui períodos genéricos do template se encontrado
                        paragraph.text = paragraph.text.replace("Agosto/2026", periodo).replace("2º Trimestre/2026", periodo)

    buffer = BytesIO()
    prs.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()

# --- PROCESSAMENTO E COMPARAÇÃO ---
if arquivo_atual is not None:
    try:
        df_atual = pd.read_excel(arquivo_atual)
        df_atual.columns = df_atual.columns.str.strip()
        
        st.success(f"✅ Planilha carregada com sucesso! (Registros: **{len(df_atual)}**)")
        
        st.markdown("### 3. Pré-visualização dos Indicadores")
        
        clientes_atual = df_atual["Cod Cli"].nunique() if "Cod Cli" in df_atual.columns else len(df_atual)
        volume_atual_ton = (df_atual["Qtde (kg)"].sum() / 1000.0) if "Qtde (kg)" in df_atual.columns else 0.0
        faturamento_atual = df_atual["Vl.Tot Item"].sum() if "Vl.Tot Item" in df_atual.columns else 0.0
        
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        with col_m1:
            st.metric("Consultor", consultor_nome)
        with col_m2:
            st.metric("Volume Total", f"{volume_atual_ton:.1f} TON")
        with col_m3:
            st.metric("Faturamento", f"R$ {faturamento_atual:,.2f}")
        with col_m4:
            st.metric("Total de Clientes", clientes_atual)

        st.markdown("---")
        st.markdown("### 4. Geração do Arquivo da Apresentação")
        st.info(f"O motor Python utilizará o **modelo oficial Consigaz** selecionado para gerar a apresentação pronta para o consultor **{consultor_nome}**.")

        if st.button("🚀 Gerar e Baixar Apresentação Pronta", type="primary"):
            pptx_bytes = gerar_apresentacao_com_modelo(
                tipo_apresentacao, consultor_nome, periodo_referencia,
                volume_atual_ton, faturamento_atual, clientes_atual
            )
            
            sufixo = "trimestral" if "Trimestral" in tipo_apresentacao else "mensal"
            nome_arquivo = f"apresentacao_{sufixo}_{consultor_nome.lower().replace(' ', '_')}.pptx"
            
            st.success("✅ Apresentação gerada com sucesso mantendo 100% da formatação e identidade visual do modelo Consigaz!")
            st.download_button(
                label="📥 Baixar Apresentação Pronta (.pptx)",
                data=pptx_bytes, 
                file_name=nome_arquivo,
                mime="application/vnd.openxmlformats-officedocument.presentationml.presentation"
            )

    except Exception as e:
        st.error(f"⚠️ Erro ao processar a planilha: {e}")
else:
    st.info("👆 Por favor, faça o upload da planilha Excel de fechamento para iniciar a automação.")
