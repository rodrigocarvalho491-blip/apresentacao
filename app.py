import os
import pandas as pd
import numpy as np
import streamlit as st
from io import BytesIO
from PIL import Image
import pptx

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
    st.markdown("Página dedicada para automação e geração de relatórios gerenciais (**Mensal** e **Trimestral**) com base comparativa anual por consultor.")

st.divider()

# --- SEÇÃO 1: PARÂMETROS E CONSULTOR ---
st.markdown("### 1. Parâmetros da Apresentação")

col_p1, col_p2, col_p3 = st.columns(3)
with col_p1:
    tipo_apresentacao = st.selectbox(
        "Selecione o Modelo de Apresentação:", 
        ["Apresentação Mensal", "Apresentação Trimestral"]
    )
with col_p2:
    consultor_nome = st.text_input("Consultor Responsável", value="Rodrigo Carvalho")
with col_p3:
    periodo_referencia = st.text_input("Período de Referência", placeholder="Ex: Agosto/2026 ou 2º Trimestre/2026")

st.divider()

# --- SEÇÃO 2: UPLOAD DAS PLANILHAS (ANO ATUAL E ANO ANTERIOR) ---
st.markdown("### 2. Upload das Planilhas Base (Comparativo Anual)")

col_up1, col_up2 = st.columns(2)

with col_up1:
    st.markdown("##### 📁 Planilha Base - **Ano Atual**")
    arquivo_atual = st.file_uploader(
        "Faça o upload do fechamento do ano atual", 
        type=["xlsx", "xls"],
        key="up_atual"
    )

with col_up2:
    st.markdown("##### 📁 Planilha Base - **Ano Anterior** (Base Comparativa)")
    arquivo_anterior = st.file_uploader(
        "Faça o upload do fechamento do mesmo período do ano anterior", 
        type=["xlsx", "xls"],
        key="up_anterior"
    )

st.divider()

# --- FUNÇÃO PARA GERAR O PPTX REAL ---
def criar_apresentacao_pptx(tipo, consultor, periodo, v_atual, f_atual, v_ant, f_ant, clientes):
    prs = pptx.Presentation()
    
    # Slide 1: Capa
    slide_layout_title = prs.slide_layouts[0]
    slide1 = prs.slides.add_slide(slide_layout_title)
    slide1.shapes.title.text = f"Resultados - {tipo}"
    slide1.placeholders[1].text = f"Consultor: {consultor}\nPeríodo: {periodo}"
    
    # Slide 2: Resumo de Desempenho e Comparativo Anual
    slide_layout_content = prs.slide_layouts[1]
    slide2 = prs.slides.add_slide(slide_layout_content)
    slide2.shapes.title.text = "Indicadores de Desempenho & Comparativo Anual"
    
    tf = slide2.placeholders[1].text_frame
    tf.text = f"• Total de Clientes Atendidos: {clientes}"
    tf.add_paragraph().text = f"• Volume Atual: {v_atual:.1f} TON (Ano Anterior: {v_ant:.1f} TON)"
    if v_ant > 0:
        cresc_vol = ((v_atual - v_ant) / v_ant) * 100
        tf.add_paragraph().text = f"  -> Crescimento de Volume: {cresch_str := f'{cresc_vol:+.1f}%'}"
    
    tf.add_paragraph().text = f"• Faturamento Atual: R$ {f_atual:,.2f} (Ano Anterior: R$ {f_ant:,.2f})"
    if f_ant > 0:
        cresc_fat = ((f_atual - f_ant) / f_ant) * 100
        tf.add_paragraph().text = f"  -> Crescimento de Faturamento: {cresc_fat:+.1f}%"

    buffer = BytesIO()
    prs.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()

# --- PROCESSAMENTO E COMPARAÇÃO ---
if arquivo_atual is not None:
    try:
        df_atual = pd.read_excel(arquivo_atual)
        df_atual.columns = df_atual.columns.str.strip()
        
        st.success(f"✅ Planilha do Ano Atual carregada com sucesso! (Registros: **{len(df_atual)}**)")
        
        df_anterior = None
        if arquivo_anterior is not None:
            df_anterior = pd.read_excel(arquivo_anterior)
            df_anterior.columns = df_anterior.columns.str.strip()
            st.info(f"📊 Planilha de Base Comparativa (Ano Anterior) carregada com sucesso! (Registros: **{len(df_anterior)}**)")
        
        st.markdown("### 3. Pré-visualização dos Indicadores & Comparativo")
        
        clientes_atual = df_atual["Cod Cli"].nunique() if "Cod Cli" in df_atual.columns else len(df_atual)
        volume_atual_ton = (df_atual["Qtde (kg)"].sum() / 1000.0) if "Qtde (kg)" in df_atual.columns else 0.0
        faturamento_atual = df_atual["Vl.Tot Item"].sum() if "Vl.Tot Item" in df_atual.columns else 0.0
        
        if df_anterior is not None:
            volume_ant_ton = (df_anterior["Qtde (kg)"].sum() / 1000.0) if "Qtde (kg)" in df_anterior.columns else 0.0
            faturamento_ant = df_anterior["Vl.Tot Item"].sum() if "Vl.Tot Item" in df_anterior.columns else 0.0
            
            crescimento_vol = ((volume_atual_ton - volume_ant_ton) / volume_ant_ton * 100) if volume_ant_ton > 0 else 0.0
            crescimento_fat = ((faturamento_atual - faturamento_ant) / faturamento_ant * 100) if faturamento_ant > 0 else 0.0
        else:
            volume_ant_ton, faturamento_ant, crescimento_vol, crescimento_fat = 0.0, 0.0, 0.0, 0.0

        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        with col_m1:
            st.metric("Consultor", consultor_nome)
        with col_m2:
            delta_str = f"{crescimento_vol:+.1f}% vs Ant." if df_anterior is not None else "Envie base anterior"
            st.metric("Volume Total", f"{volume_atual_ton:.1f} TON", delta=delta_str)
        with col_m3:
            delta_fat = f"{crescimento_fat:+.1f}% vs Ant." if df_anterior is not None else "Envie base anterior"
            st.metric("Faturamento", f"R$ {faturamento_atual:,.2f}", delta=delta_fat)
        with col_m4:
            st.metric("Total de Clientes", clientes_atual)

        st.markdown("---")
        st.markdown("### 4. Geração do Arquivo da Apresentação")
        st.info(f"O motor Python gerará a **{tipo_apresentacao}** oficial para o consultor **{consultor_nome}** com todos os dados consolidados.")

        if st.button("🚀 Gerar e Baixar Apresentação Pronta", type="primary"):
            pptx_bytes = criar_apresentacao_pptx(
                tipo_apresentacao, consultor_nome, periodo_referencia,
                volume_atual_ton, faturamento_atual, volume_ant_ton, faturamento_ant, clientes_atual
            )
            
            nome_arquivo = f"apresentacao_{tipo_apresentacao.lower().replace(' ', '_')}_{consultor_nome.lower().replace(' ', '_')}.pptx"
            
            st.success("✅ Apresentação gerada com sucesso e pronta para uso!")
            st.download_button(
                label="📥 Baixar Apresentação Pronta (.pptx)",
                data=pptx_bytes, 
                file_name=nome_arquivo,
                mime="application/vnd.openxmlformats-officedocument.presentationml.presentation"
            )

    except Exception as e:
        st.error(f"⚠️ Erro ao processar as planilhas base: {e}")
else:
    st.info("👆 Por favor, faça o upload da planilha Excel do ano atual para iniciar a análise e geração.")
