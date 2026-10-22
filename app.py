import os
import pandas as pd
import numpy as np
import streamlit as st
from io import BytesIO
from PIL import Image

try:
    import pptx
except ImportError:
    pptx = None

# --- CONFIGURAÇÃO GLOBAL DA PÁGINA (SEM MENU LATERAL) ---
st.set_page_config(
    page_title="Gerador de Apresentação | Consigaz", 
    page_icon="🔥", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

DIRETORIO_ATUAL = os.path.dirname(os.path.abspath(__file__))
LOGO_PATH = os.path.join(DIRETORIO_ATUAL, "logo.png")

# =====================================================================
# IDENTIDADE VISUAL CONSIGAZ - DESIGN MODERNO (PÁGINA DEDICADA)
# =====================================================================
CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

:root {
  --cg-azul-principal: #003366;
  --cg-azul-vibrante: #0055A5;
  --cg-laranja: #F28C28;
}

html, body, [class*="css"] {
  font-family: 'Plus Jakarta Sans', 'Segoe UI', Roboto, Helvetica, Arial, sans-serif !important;
}

[data-testid="stSidebar"] { display: none; }
[data-testid="stHeader"] { background: transparent; }
#MainMenu, footer { visibility: hidden; }

/* Bloco principal flutuante e moderno com bordas arredondadas */
.block-container, [data-testid="stMainBlockContainer"] {
  max-width: 1200px !important;
  margin: 1.5rem auto !important;
  padding: 2.5rem !important;
  border-radius: 24px !important;
  box-shadow: 0 10px 30px rgba(0, 51, 102, 0.08);
  border: 1px solid rgba(120, 140, 160, 0.2);
}

/* Cabeçalho Consigaz com destaque refinado */
.cg-header { 
  display: flex; 
  align-items: center; 
  gap: 1.8rem; 
  position: relative;
  padding-bottom: 1.5rem; 
  margin-bottom: 2rem; 
  border-bottom: 2px solid rgba(120, 140, 160, 0.2); 
}
.cg-header::after { 
  content: ""; 
  position: absolute; 
  left: 0; 
  bottom: -2px; 
  width: 160px; 
  height: 4px; 
  border-radius: 4px; 
  background: linear-gradient(90deg, var(--cg-azul-vibrante) 0%, var(--cg-laranja) 100%); 
}

/* Logotipo em evidência com cantos arredondados, padding e sombra suave */
.cg-logo-wrapper {
  background: #FFFFFF;
  padding: 8px 14px;
  border-radius: 14px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid rgba(255, 255, 255, 0.1);
}
.cg-logo { height: 68px; width: auto; display: block; }

.cg-header-sep { width: 2px; align-self: stretch; background: rgba(120, 140, 160, 0.3); }
.cg-title { font-size: 1.8rem; font-weight: 800; line-height: 1.2; letter-spacing: -0.02em; }
.cg-subtitle { font-size: 0.98rem; margin-top: 0.3rem; opacity: 0.8; font-weight: 500; }

/* Títulos de Seção Estilizados */
.stApp h3 {
  font-size: 1.15rem !important;
  font-weight: 700 !important;
  color: var(--cg-azul-vibrante) !important;
  padding: 0.3rem 0 0.3rem 0.8rem !important;
  border-left: 5px solid var(--cg-laranja) !important;
  background: linear-gradient(90deg, rgba(242, 140, 40, 0.08) 0%, transparent 100%);
  border-radius: 0 8px 8px 0;
  margin-top: 1.8rem !important;
  margin-bottom: 1.2rem !important;
}

/* Inputs, selects e textareas super arredondados e fluidos */
[data-baseweb="input"], [data-baseweb="textarea"], [data-baseweb="select"] > div {
  border-radius: 14px !important;
  border: 1.5px solid rgba(120, 140, 160, 0.3) !important;
  transition: all 0.2s ease;
}
[data-baseweb="input"]:focus-within, [data-baseweb="textarea"]:focus-within, [data-baseweb="select"] > div:focus-within {
  border-color: var(--cg-azul-vibrante) !important;
  box-shadow: 0 0 0 4px rgba(0, 85, 165, 0.15) !important;
}

/* Botões modernos, arredondados e com sombras suaves */
.stButton > button, .stDownloadButton > button {
  border-radius: 14px !important;
  font-weight: 700 !important;
  padding: 0.6rem 1.4rem !important;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
  box-shadow: 0 2px 5px rgba(0,0,0,0.02);
}

.stButton > button[kind="primary"], .stButton > button[data-testid="stBaseButton-primary"], .stDownloadButton > button {
  background: linear-gradient(135deg, var(--cg-azul-vibrante) 0%, var(--cg-azul-principal) 100%) !important;
  color: #FFFFFF !important;
  border: none !important;
  box-shadow: 0 4px 15px rgba(0, 85, 165, 0.25) !important;
}
.stButton > button[kind="primary"]:hover, .stButton > button[data-testid="stBaseButton-primary"]:hover, .stDownloadButton > button:hover {
  opacity: 0.95;
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(0, 85, 165, 0.35) !important;
}

/* Divisor elegante */
hr { border-color: rgba(120, 140, 160, 0.2) !important; margin: 2rem 0 !important; }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


@st.cache_data(show_spinner=False)
def _logo_base64(caminho):
    try:
        with open(caminho, "rb") as f:
            return base64.b64encode(f.read()).decode("ascii")
    except Exception:
        return ""


def _logo_html(classe_img, classe_wrapper=""):
    b64 = _logo_base64(LOGO_PATH)
    if not b64:
        return ""
    img_tag = f'<img class="{classe_img}" src="data:image/png;base64,{b64}" alt="Consigaz">'
    if classe_wrapper:
        return f'<div class="{classe_wrapper}">{img_tag}</div>'
    return img_tag


def cabecalho_pagina(titulo, subtitulo):
    logo = _logo_html("cg-logo", "cg-logo-wrapper")
    separador = '<div class="cg-header-sep"></div>' if logo else ""
    st.markdown(
        f'<div class="cg-header">{logo}{separador}<div>'
        f'<div class="cg-title">{titulo}</div>'
        f'<div class="cg-subtitle">{subtitulo}</div>'
        f'</div></div>',
        unsafe_allow_html=True,
    )


# --- CABEÇALHO DA PÁGINA EXCLUSIVA ---
cabecalho_pagina(
    "Gerador de Apresentação de Resultados", 
    "Página dedicada e exclusiva para automação e geração de relatórios gerenciais com base nos modelos oficiais Consigaz."
)

st.divider()

# --- SEÇÃO 1: PARÂMETROS E CONSULTOR ---
st.subheader("1. Parâmetros da Apresentação")

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
st.subheader("2. Upload da Planilha Base de Fechamento")

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
    
    if "Trimestral" in tipo_modelo:
        modelo_path = os.path.join(DIRETORIO_ATUAL, "rodrigo_sjc_2T2026_2.pptx")
    else:
        modelo_path = os.path.join(DIRETORIO_ATUAL, "rodrigo_ago26.pptx")
    
    if not os.path.exists(modelo_path):
        modelo_path = os.path.join(DIRETORIO_ATUAL, "rodrigo_ago26.pptx")
        if not os.path.exists(modelo_path):
            raise FileNotFoundError("Nenhum arquivo de modelo PPTX válido foi encontrado na pasta do sistema.")
    
    prs = pptx.Presentation(modelo_path)
    
    for slide in prs.slides:
        for shape in slide.shapes:
            if shape.has_text_frame:
                for paragraph in shape.text_frame.paragraphs:
                    if "Rodrigo Carvalho" in paragraph.text and consultor != "Rodrigo Carvalho":
                        paragraph.text = paragraph.text.replace("Rodrigo Carvalho", consultor)
                    if ("Agosto/2026" in paragraph.text or "2º Trimestre/2026" in paragraph.text) and periodo:
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
        
        st.subheader("3. Pré-visualização dos Indicadores")
        
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

        st.divider()
        st.subheader("4. Geração do Arquivo da Apresentação")
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
