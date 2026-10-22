import os
import pandas as pd
import numpy as np
import streamlit as st
from datetime import datetime, timedelta
from io import BytesIO
from PIL import Image
from fpdf import FPDF
import streamlit.components.v1 as components
import requests

try:
    import pptx
except ImportError:
    pptx = None

# --- CONFIGURAÇÃO GLOBAL DA PÁGINA ---
st.set_page_config(page_title="Sistema Integrado Consigaz", page_icon="⚙️", layout="wide")

DIRETORIO_ATUAL = os.path.dirname(os.path.abspath(__file__))
LOGO_PATH = os.path.join(DIRETORIO_ATUAL, "logo.png")
LOGO2_PATH = os.path.join(DIRETORIO_ATUAL, "logo2.png")

CUSTOM_CSS = """
<style>
    h1, h2, h3 { color: #004080 !important; font-family: 'Segoe UI', sans-serif; }
    div.stButton > button:first-child {
        background-color: #004080 !important; color: #ffffff !important;
        border-radius: 8px !important; border: none !important; font-weight: bold !important;
    }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# --- MAPEAMENTO DAS COLUNAS DO EXCEL ---
COL_OCORRENCIA = "Número da ocorrência"
COL_CLIENTE = "Nome do cliente"
COL_ENDERECO = "Endereço de Entrega"
COL_ABERTURA = "Data/Hora de abertura"
COL_PRAZO = "Prazo de Atendimento"
COL_FECHAMENTO = "Data/Hora de fechamento"
COL_SUB_CLASSIF = "Subclassificação Ocorrência"

# --- INICIALIZAÇÃO DO SESSION STATE ---
if "tratadas_manualmente" not in st.session_state:
    st.session_state.tratadas_manualmente = set()

if "ocorrencia_ativa" not in st.session_state:
    st.session_state.ocorrencia_ativa = {"codigo": "", "cliente": ""}

if "reset_counter" not in st.session_state:
    st.session_state.reset_counter = 0

if "eq_key_counter" not in st.session_state:
    st.session_state.eq_key_counter = 0

if "equipamentos" not in st.session_state:
    st.session_state.equipamentos = []

if "last_central" not in st.session_state:
    st.session_state.last_central = "Central"

if "last_tipo_cad" not in st.session_state:
    st.session_state.last_tipo_cad = "Equipamentos"

# --- FUNÇÕES AUXILIARES ---
def extrair_cidade(endereco):
    if pd.isna(endereco):
        return "-"
    s = str(endereco).strip()
    s_norm = s.replace(';', ',').replace('|', ',')
    partes = [p.strip() for p in s_norm.split(',')]
    if len(partes) >= 2:
        cidade = partes[-2].strip()
        if cidade.isdigit() and len(partes) >= 3:
            cidade = partes[-3].strip()
        return cidade.title()
    return s.title()

def calcular_dias_uteis(data_inicio, data_fim):
    h = pd.Timestamp(data_inicio).normalize().date()
    p = pd.Timestamp(data_fim).normalize().date()
    if p > h:
        return int(np.busday_count(h, p))
    elif p < h:
        return -int(np.busday_count(p, h))
    else:
        return 0

def classificar_status_geral(dias_uteis):
    if dias_uteis < 0:
        return "🔴 Vencido"
    elif dias_uteis == 0:
        return "🔵 Vence Hoje"
    elif dias_uteis == 1:
        return "🟠 Vence Amanhã"
    elif 2 <= dias_uteis <= 5:
        return "🟡 Vence na Semana"
    else:
        return "🟢 No Prazo"

def resetar_dados_cliente():
    st.session_state.reset_counter += 1
    st.session_state.eq_key_counter = 0
    st.session_state.equipamentos = []
    st.session_state.last_central = "Central"
    st.session_state.last_tipo_cad = "Equipamentos"

# --- MENU LATERAL DE NAVEGAÇÃO ---
st.sidebar.title("📌 Menu de Navegação")
menu = st.sidebar.radio(
    "Selecione a página:", 
    [
        "📷 Visita de Transferência",
        "📝 Elaboração de Contrato",
        "📊 Gerador de Apresentação de Resultados"
    ]
)

st.sidebar.divider()
if st.sidebar.button("🔄 Resetar Sessão Completa"):
    st.session_state.clear()
    st.rerun()

# =====================================================================
# TELA 1: VISITA DE TRANSFERÊNCIA
# =====================================================================
if menu == "📷 Visita de Transferência":
    rc = st.session_state.reset_counter
    ekc = st.session_state.eq_key_counter

    col_logo, col_titulo = st.columns([1, 4])
    with col_logo:
        if os.path.exists(LOGO_PATH): st.image(LOGO_PATH, width=150)
    with col_titulo:
        st.title("Visita de Transferência & Relatório Técnico")
        st.markdown("Preenchimento técnico e geração do relatório fotográfico.")

    st.divider()
    st.button("🔄 Novo Cliente / Limpar", on_click=resetar_dados_cliente)

    st.subheader("1. Identificação do Cliente")
    val_cod = st.session_state.ocorrencia_ativa["codigo"] if st.session_state.ocorrencia_ativa["codigo"] else ""
    val_nome = st.session_state.ocorrencia_ativa["cliente"] if st.session_state.ocorrencia_ativa["cliente"] else ""

    s1_l1_c1, s1_l1_c2, s1_l1_c3 = st.columns(3)
    with s1_l1_c1:
        cod_cliente = st.text_input("Código do Cliente *", value=val_cod, key=f"input_cod_{rc}")
    with s1_l1_c2:
        nome_cliente = st.text_input("Nome / Razão Social *", value=val_nome, key=f"input_nome_{rc}")
    with s1_l1_c3:
        telefone = st.text_input("Telefone *", key=f"input_tel_{rc}")

    s1_l2_c1, s1_l2_c2, s1_l2_c3 = st.columns(3)
    with s1_l2_c1:
        contato = st.text_input("Contato *", key=f"input_contato_{rc}")
    with s1_l2_c2:
        departamento = st.text_input("Sobrenome ou Departamento *", key=f"input_depto_{rc}")
    with s1_l2_c3:
        st.write("")

    st.divider()

    st.subheader("2. Informações Contratuais")
    s2_l1_c1, s2_l1_c2, s2_l1_c3, s2_l1_c4 = st.columns(4)
    with s2_l1_c1:
        eq_contrato = st.selectbox("Equipamentos de acordo com contrato? *", ["Sim", "Não"], index=None, key=f"eq_contrato_{rc}")
    with s2_l1_c2:
        desc_eq_contrato = st.text_input("Quais equipamentos disponíveis? *", key=f"desc_eq_contrato_{rc}")
    with s2_l1_c3:
        tem_freq = st.selectbox("Possui programação cadastrada? *", ["Sim", "Não"], index=None, key=f"tem_freq_{rc}")
    with s2_l1_c4:
        desc_freq = ""
        if tem_freq == "Sim":
            desc_freq = st.text_input("Qual a programação? *", key=f"freq_cad_sim_{rc}")
        elif tem_freq == "Não":
            desc_freq = st.text_input("Nº OC de Cadastramento *", key=f"freq_cad_nao_{rc}")
        else:
            st.write("")

    s2_l2_c1, s2_l2_c2 = st.columns(2)
    with s2_l2_c1:
        consumo_previsto = st.text_input("Consumo Previsto (kg) *", key=f"cons_prev_{rc}")
    with s2_l2_c2:
        consumo_real = st.text_input("Consumo Real/Médio (kg) *", key=f"cons_real_{rc}")

    s2_l3_c1, s2_l3_c2 = st.columns(2)
    with s2_l3_c1:
        possui_art = st.selectbox("Possui ART? *", ["Sim", "Não"], index=None, key=f"possui_art_{rc}")
    with s2_l3_c2:
        desc_art = ""
        if possui_art == "Sim":
            desc_art = st.text_input("Número da ART *", key=f"art_sim_{rc}")
        elif possui_art == "Não":
            desc_art = st.text_input("Nº OC de Solicitação de Laudo *", key=f"art_nao_{rc}")
        else:
            st.write("")

    s2_l4_c1, s2_l4_c2 = st.columns(2)
    with s2_l4_c1:
        possui_debitos = st.selectbox("Cliente possui débitos? *", ["Sim", "Não"], index=None, key=f"possui_debitos_{rc}")
    with s2_l4_c2:
        desc_debitos = st.text_input("Detalhes dos Débitos", key=f"desc_debitos_{rc}") if possui_debitos == "Sim" else ""

    s2_l5_c1, s2_l5_c2 = st.columns(2)
    with s2_l5_c1:
        central_norma = st.selectbox("Central dentro de norma? *", ["Sim", "Não"], index=None, key=f"central_norma_{rc}")
    with s2_l5_c2:
        desc_central_norma = st.text_input("Motivo da Central fora de norma", key=f"desc_central_norma_{rc}") if central_norma == "Não" else ""

    s2_l6_c1, s2_l6_c2 = st.columns(2)
    with s2_l6_c1:
        rep2_correto = st.selectbox("Representante 2 está correto? *", ["Sim", "Não"], index=None, key=f"rep2_correto_{rc}")
    with s2_l6_c2:
        desc_rep2 = st.text_input("Nº OC de Regularização", key=f"desc_rep2_{rc}") if rep2_correto == "Não" else ""

    st.divider()

    st.subheader("3. Cadastro de Instalação e Equipamentos")
    col_cent1, col_cent2 = st.columns(2)
    with col_cent1:
        qtd_centrais = st.number_input("Quantidade de Centrais no Cliente", min_value=1, value=1, step=1, key=f"qtd_centrais_{rc}")
    with col_cent2:
        if qtd_centrais > 1:
            opcoes_centrais = [f"Central {i:02d}" for i in range(1, int(qtd_centrais) + 1)]
            idx_central = 0
            if st.session_state.last_central in opcoes_centrais:
                idx_central = opcoes_centrais.index(st.session_state.last_central)
            central_selecionada = st.selectbox("Vincular item à qual Central?", opcoes_centrais, index=idx_central, key=f"sel_central_{rc}_{ekc}")
            st.session_state.last_central = central_selecionada
        else:
            central_selecionada = "Central"
            st.session_state.last_central = "Central"
            st.write("")

    opcoes_tipo = ["Equipamentos", "Cilindros", "Condomínio"]
    idx_tipo = 0
    if st.session_state.last_tipo_cad in opcoes_tipo:
        idx_tipo = opcoes_tipo.index(st.session_state.last_tipo_cad)
    tipo_cadastro = st.radio("Selecione o tipo que deseja adicionar:", opcoes_tipo, index=idx_tipo, horizontal=True, key=f"tipo_cad_{rc}_{ekc}")
    st.session_state.last_tipo_cad = tipo_cadastro

    if tipo_cadastro == "Equipamentos":
        col_qtd, col_eq, col_vaz, col_btn = st.columns([1, 2, 2, 1])
        with col_qtd:
            qtd_input = st.number_input("Quantidade", min_value=1, value=1, step=1, key=f"eq_qtd_{rc}_{ekc}")
        with col_eq:
            nome_eq_input = st.text_input("Equipamento", key=f"eq_nome_{rc}_{ekc}")
        with col_vaz:
            vazao_input = st.text_input("Vazão (kg/h)", key=f"eq_vazao_{rc}_{ekc}")
        with col_btn:
            st.write(" "); st.write(" ")
            if st.button("➕ Adicionar", key=f"btn_add_eq_{rc}_{ekc}"):
                if nome_eq_input.strip() and vazao_input.strip():
                    try:
                        vazao_unit = float(vazao_input.replace(",", ".").lower().replace("kg/h", "").strip())
                        qtd = int(qtd_input)
                        vazao_total_item = vazao_unit * qtd
                        vazao_formatada = f"{vazao_total_item:.2f}".replace(".", ",").rstrip("0").rstrip(",")

                        item_dict = {
                            "central": central_selecionada,
                            "tipo": "equipamento",
                            "qtd": qtd,
                            "nome": nome_eq_input.strip().title(),
                            "vazao_total_item": vazao_total_item,
                            "texto": f"{qtd:02d} - {nome_eq_input.strip().title()} - {vazao_formatada} kg/h"
                        }
                        st.session_state.equipamentos.append(item_dict)
                        st.session_state.eq_key_counter += 1
                        st.success("Item adicionado!")
                        st.rerun()
                    except ValueError:
                        st.error("Informe um número válido para a vazão.")
                else:
                    st.warning("Preencha o nome e a vazão.")

    elif tipo_cadastro == "Cilindros":
        col_qtd, col_mod, col_btn = st.columns([1, 4, 1])
        with col_qtd:
            qtd_input = st.number_input("Qtd", min_value=1, value=1, step=1, key=f"cil_qtd_{rc}_{ekc}")
        with col_mod:
            modelo_input = st.text_input("Modelo", key=f"cil_mod_{rc}_{ekc}")
        with col_btn:
            st.write(" "); st.write(" ")
            if st.button("➕ Adicionar", key=f"btn_add_cil_{rc}_{ekc}"):
                if modelo_input.strip():
                    qtd = int(qtd_input)
                    item_dict = {
                        "central": central_selecionada,
                        "tipo": "cilindro",
                        "qtd": qtd,
                        "nome": f"Cilindro {modelo_input.strip().upper()}",
                        "vazao_total_item": 0.0,
                        "texto": f"{qtd:02d} und {modelo_input.strip().upper()}"
                    }
                    st.session_state.equipamentos.append(item_dict)
                    st.session_state.eq_key_counter += 1
                    st.success("Cilindro adicionado!")
                    st.rerun()

    elif tipo_cadastro == "Condomínio":
        col_local, col_qtd, col_tipo, col_btn = st.columns([2, 1, 3, 1])
        with col_local:
            local_input = st.selectbox("Local", ["Apartamentos", "Área Comum"], key=f"cond_local_{rc}_{ekc}")
        with col_qtd:
            qtd_input = st.number_input("Qtd", min_value=1, value=1, step=1, key=f"cond_qtd_{rc}_{ekc}")
        with col_tipo:
            tipo_apt_input = st.selectbox("Instalação", ["Só Fogão", "Fogão + Aquecedor"], key=f"cond_tipo_{rc}_{ekc}")
        with col_btn:
            st.write(" "); st.write(" ")
            if st.button("➕ Adicionar", key=f"btn_add_cond_{rc}_{ekc}"):
                qtd = int(qtd_input)
                vazao_unit = 0.1 if tipo_apt_input == "Só Fogão" else 0.4
                vazao_total = vazao_unit * qtd
                texto = f"{qtd:02d} aps - {tipo_apt_input}" if local_input == "Apartamentos" else f"{qtd:02d} - Área Comum ({tipo_apt_input})"
                
                item_dict = {
                    "central": central_selecionada,
                    "tipo": "condominio",
                    "qtd": qtd,
                    "nome": f"Condomínio ({tipo_apt_input})",
                    "vazao_total_item": vazao_total,
                    "texto": texto
                }
                st.session_state.equipamentos.append(item_dict)
                st.session_state.eq_key_counter += 1
                st.success("Condomínio adicionado!")
                st.rerun()

    if st.session_state.equipamentos:
        st.write("**Itens Cadastrados:**")
        def get_c_name(item, q):
            return "Central" if q == 1 else item.get("central", "Central")
        
        centrais_presentes = sorted(list(set([get_c_name(item, qtd_centrais) for item in st.session_state.equipamentos])))
        for c_nome in centrais_presentes:
            st.markdown(f"**{c_nome.upper()}**")
            vazao_c = 0.0
            for idx, item in enumerate(st.session_state.equipamentos):
                if get_c_name(item, qtd_centrais) == c_nome:
                    vazao_c += item["vazao_total_item"]
                    c_txt, c_del = st.columns([5, 1])
                    c_txt.text(item["texto"])
                    if c_del.button("❌", key=f"del_{idx}_{rc}"):
                        st.session_state.equipamentos.pop(idx)
                        st.rerun()
            v_str = f"{vazao_c:.2f}".replace(".", ",").rstrip("0").rstrip(",") if vazao_c > 0 else "0"
            st.markdown(f"*Vazão Total {c_nome}: {v_str} kg/h*")

    st.divider()

    st.subheader("4. Satisfação & Observações")
    s4_l1_c1, s4_l1_c2 = st.columns(2)
    with s4_l1_c1:
        indica_negocios = st.selectbox("Indicou novos negócios? *", ["Sim", "Não"], index=None, key=f"ind_neg_{rc}")
    with s4_l1_c2:
        cliente_satisfeito = st.selectbox("Cliente satisfeito com a Consigaz? *", ["Sim", "Não"], index=None, key=f"cli_sat_{rc}")

    observacoes = st.text_area("Observações Gerais", key=f"obs_{rc}")

    st.divider()

    st.subheader("5. Relatório Fotográfico")
    def carregar_fotos(label, max_arq=None):
        fotos = st.file_uploader(label, type=["png", "jpg", "jpeg"], accept_multiple_files=True, key=f"up_{label}_{rc}")
        if max_arq and fotos and len(fotos) > max_arq:
            return fotos[:max_arq]
        return fotos

    dic_fotos_final = {}
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        dic_fotos_final["FACHADA"] = carregar_fotos("FACHADA", 2)
    with col_f2:
        dic_fotos_final["CILINDROS"] = carregar_fotos("CILINDROS", 5)

    if qtd_centrais == 1:
        c1, c2, c3 = st.columns(3)
        with c1: dic_fotos_final["ABRIGO"] = carregar_fotos("ABRIGO", 10)
        with c2: dic_fotos_final["CENTRAL"] = carregar_fotos("CENTRAL", 5)
        with c3: dic_fotos_final["EQUIPAMENTOS"] = carregar_fotos("EQUIPAMENTOS")
    else:
        for i in range(1, int(qtd_centrais) + 1):
            st.markdown(f"**📸 CENTRAL {i:02d}**")
            c1, c2, c3 = st.columns(3)
            with c1: dic_fotos_final[f"ABRIGO CENTRAL {i:02d}"] = carregar_fotos(f"ABRIGO CENTRAL {i:02d}", 10)
            with c2: dic_fotos_final[f"CENTRAL {i:02d}"] = carregar_fotos(f"CENTRAL {i:02d}", 5)
            with c3: dic_fotos_final[f"EQUIPAMENTOS CENTRAL {i:02d}"] = carregar_fotos(f"EQUIPAMENTOS CENTRAL {i:02d}")

    st.divider()

    class RelatorioPDF(FPDF):
        def __init__(self, cod="", nome=""):
            super().__init__()
            self.cod = cod.replace(".", "").strip().upper()
            self.nome = nome.strip().upper()

        def header(self):
            if os.path.exists(LOGO2_PATH):
                self.image(LOGO2_PATH, x=10, y=8, w=45)
            if self.page_no() == 1:
                self.set_y(10)
                self.set_font("Arial", "B", 15)
                self.cell(0, 8, "RELATÓRIO FOTOGRÁFICO", align="C", ln=1)
                if self.cod or self.nome:
                    self.set_font("Arial", "B", 11)
                    self.cell(0, 6, f"{self.cod} | {self.nome}", align="C", ln=1)
                self.set_y(35)
            else:
                self.set_y(35)

        def footer(self):
            self.set_y(-15)
            self.set_font("Arial", "I", 8)
            self.cell(0, 10, f"Página {self.page_no()}", align="C")

    def gerar_pdf(equipamentos, dic_fotos, cod, nome, qty_c):
        pdf = RelatorioPDF(cod, nome)
        pdf.set_margins(10, 35, 10)
        pdf.set_auto_page_break(auto=True, margin=20)

        for cat, arquivos in dic_fotos.items():
            if arquivos:
                pdf.add_page()
                pdf.set_font("Arial", "B", 11)
                pdf.cell(0, 6, cat.upper(), ln=1, align="L")
                pdf.ln(2)
                for idx, arq in enumerate(arquivos):
                    try:
                        img = Image.open(arq)
                        if img.mode != "RGB": img = img.convert("RGB")
                        t_path = f"temp_{cat}_{idx}.jpg"
                        img.save(t_path)
                        w_p, h_p = img.size
                        prop = h_p / w_p
                        w_alv = 130
                        h_alv = w_alv * prop
                        if h_alv > 110:
                            h_alv = 110
                            w_alv = h_alv / prop
                        pos_x = (210 - w_alv) / 2
                        if pdf.get_y() + h_alv > 270: pdf.add_page()
                        pdf.image(t_path, x=pos_x, y=pdf.get_y(), w=w_alv, h=h_alv)
                        pdf.set_y(pdf.get_y() + h_alv + 5)
                        if os.path.exists(t_path): os.remove(t_path)
                    except Exception:
                        pass

        if equipamentos:
            pdf.add_page()
            pdf.set_font("Arial", "B", 11)
            pdf.cell(0, 6, "LISTA DE ITENS E VAZÕES", ln=1, align="L")
            pdf.ln(2)
            
            def get_c_pdf(it): return "Central" if qty_c == 1 else it.get("central", "Central")
            centrais_p = sorted(list(set([get_c_pdf(it) for it in equipamentos])))
            
            for c_nome in centrais_p:
                pdf.set_font("Arial", "B", 10)
                pdf.cell(0, 6, c_nome.upper(), ln=1, align="L")
                pdf.set_fill_color(230, 230, 230)
                pdf.cell(20, 7, "QTD", border=1, align="C", fill=True)
                pdf.cell(120, 7, "ITEM / EQUIPAMENTO", border=1, align="C", fill=True)
                pdf.cell(50, 7, "VAZÃO TOTAL", border=1, align="C", fill=True, ln=1)
                
                pdf.set_font("Arial", "", 10)
                tot_v = 0.0
                for it in equipamentos:
                    if get_c_pdf(it) == c_nome:
                        tot_v += it["vazao_total_item"]
                        v_disp = "-" if it.get("tipo") == "cilindro" else f"{it['vazao_total_item']:.2f}".replace(".", ",").rstrip("0").rstrip(",") + " kg/h"
                        pdf.cell(20, 6, f"{it['qtd']:02d}", border=1, align="C")
                        pdf.cell(120, 6, f"{it['nome']}", border=1, align="L")
                        pdf.cell(50, 6, v_disp, border=1, align="C", ln=1)
                
                v_tot_str = f"{tot_v:.2f}".replace(".", ",").rstrip("0").rstrip(",")
                pdf.set_font("Arial", "B", 10)
                pdf.cell(140, 7, f"VAZÃO TOTAL {c_nome.upper()}:", border=1, align="R", fill=True)
                pdf.cell(50, 7, f"{v_tot_str} kg/h", border=1, align="C", fill=True, ln=1)
                pdf.ln(4)

        res = pdf.output(dest="S")
        if isinstance(res, str):
            return res.encode("latin-1")
        return bytes(res)

    st.subheader("6. Ações Finais")
    col_a1, col_a2 = st.columns(2)

    with col_a1:
        if st.button("📄 Gerar Relatório PDF"):
            if not cod_cliente.strip() or not nome_cliente.strip():
                st.error("⚠️ Preencha pelo menos o Código e o Nome do Cliente.")
            else:
                pdf_bytes = gerar_pdf(st.session_state.equipamentos, dic_fotos_final, cod_cliente, nome_cliente, qtd_centrais)
                st.success("✅ PDF gerado com sucesso!")
                st.download_button(
                    label="📥 Baixar Relatório (PDF)",
                    data=pdf_bytes,
                    file_name=f"relatorio_{cod_cliente}.pdf",
                    mime="application/pdf"
                )

    with col_a2:
        if st.button("📝 Gerar Texto para Sistema"):
            lista_eq_txt = ""
            if st.session_state.equipamentos:
                def get_c_txt(eq): return "Central" if qtd_centrais == 1 else eq.get("central", "Central")
                cps = sorted(list(set([get_c_txt(eq) for eq in st.session_state.equipamentos])))
                for c_n in cps:
                    lista_eq_txt += f"Equipamentos {c_n}\n"
                    v_c = 0.0
                    for eq in st.session_state.equipamentos:
                        if get_c_txt(eq) == c_n:
                            lista_eq_txt += f"{eq['texto']}\n"
                            v_c += eq["vazao_total_item"]
                    lista_eq_txt += f"\nTotal Vazão {c_n}: {f'{v_c:.2f}'.replace('.', ',')} kg/h\n\n"
            else:
                lista_eq_txt = "Nenhum item cadastrado.\n\n"

            texto_final = f"""Contato: {contato}
Departamento: {departamento}
Telefone: {telefone}
Equipamento de acordo com o contrato: {eq_contrato} - {desc_eq_contrato}
Consumo Previsto: {consumo_previsto} kg | Consumo Real: {consumo_real} kg
Possui ART: {possui_art} - {desc_art}
Central dentro de norma: {central_norma}

{lista_eq_txt}
Observações: {observacoes}
"""
            st.success("✅ Texto gerado com sucesso!")
            st.text_area("Texto gerado:", value=texto_final, height=200)


# =====================================================================
# TELA 2: ELABORAÇÃO DE CONTRATO
# =====================================================================
elif menu == "📝 Elaboração de Contrato":
    rc = st.session_state.get('reset_counter', 0)

    col_logo, col_titulo = st.columns([1, 4])
    with col_logo:
        if os.path.exists(LOGO_PATH): st.image(LOGO_PATH, width=150)
    with col_titulo:
        st.title("Elaboração de Contrato")
        st.markdown("Formulário de preenchimento e geração do padrão de solicitação.")

    st.divider()
    tipo_fluxo = st.radio("Selecione o objetivo da solicitação:", ["Gerar Minuta", "Enviar para Assinatura"], horizontal=True)

    st.write("")
    st.subheader("1. Dados da Solicitação")

    col_c1, col_c2 = st.columns(2)
    with col_c1:
        motivo_solicitacao = st.text_input("Motivo da solicitação", key=f"motivo_{rc}")
        contato_contrato = st.text_input("Contato", key=f"cont_c_{rc}")
        telefone_contrato = st.text_input("Telefone", key=f"tel_c_{rc}")
        email_contrato = st.text_input("E-mail", key=f"email_c_{rc}")
        tipo_contrato = st.radio("Contrato / Aditamento / Distrato", ["Contrato", "Aditamento", "Distrato"], horizontal=True, key=f"tipo_c_{rc}")
        mesmo_prop = st.radio("Mesmo proprietário?", ["Sim", "Não"], horizontal=True, index=None, key=f"mesmo_p_{rc}")

        if mesmo_prop == "Sim":
            cnpj = st.text_input("CNPJ", key=f"cnpj_{rc}")
            ie = st.text_input("I.E.", key=f"ie_{rc}")
            novo_cnpj, nova_ie = "", ""
        elif mesmo_prop == "Não":
            novo_cnpj = st.text_input("Novo CNPJ", key=f"n_cnpj_{rc}")
            nova_ie = st.text_input("Nova I.E.", key=f"n_ie_{rc}")
            cnpj, ie = "", "", "", ""
        else:
            cnpj, ie, novo_cnpj, nova_ie = "", "", "", ""

        endereco_padrao = st.text_input("Endereço padrão ou entrega?", key=f"end_p_{rc}")

    with col_c2:
        cond_pagamento = st.text_input("Condição de pagamento", key=f"cond_p_{rc}")
        vigencia = st.text_input("Vigência", key=f"vig_{rc}")

    st.divider()
    st.subheader("2. Responsáveis & Assinaturas")
    resp_pendentes = st.text_input("Quem será o responsável pelas NF's pendentes?", key=f"resp_p_{rc}")
    email_novo_prop = st.text_input("E-mail do novo proprietário que receberá o novo contrato", key=f"email_np_{rc}")

    if tipo_fluxo == "Enviar para Assinatura":
        col_a1, col_a2 = st.columns(2)
        with col_a1:
            nome_testemunha = st.text_input("Nome da Testemunha", key=f"test_n_{rc}")
            email_testemunha = st.text_input("E-mail da Testemunha", key=f"test_e_{rc}")
        with col_a2:
            nome_responsavel = st.text_input("Nome do Responsável pela assinatura", key=f"resp_n_{rc}")
            email_responsavel = st.text_input("E-mail do Responsável pela assinatura", key=f"resp_e_{rc}")
    else:
        nome_testemunha, email_testemunha, nome_responsavel, email_responsavel = "", "", "", ""

    st.divider()
    st.subheader("3. Condomínio CONTA SIM?")
    conta_sim = st.radio("Condomínio CONTA SIM?", ["Sim", "Não"], horizontal=True, index=1, key=f"c_sim_{rc}")

    num_unidades, qtd_torres, qtd_blocos, preco_religue, preco_servico = "", "", "", "", ""
    if conta_sim == "Sim":
        col_cs1, col_cs2, col_cs3 = st.columns(3)
        with col_cs1:
            num_unidades = st.text_input("N° Unid autônomas (Aptos + áreas comuns/zeladoria)", key=f"unid_{rc}")
            qtd_torres = st.text_input("Qtd Torres", key=f"torres_{rc}")
        with col_cs2:
            qtd_blocos = st.text_input("Qtd Blocos", key=f"blocos_{rc}")
            preco_religue = st.text_input("Valor preço de religue", key=f"religue_{rc}")
        with col_cs3:
            preco_servico = st.text_input("Valor preço de serviço", key=f"servico_{rc}")

    st.divider()
    st.subheader("4. Dados do Contrato (Equipamentos & Endereços)")
    qtd_enderecos = st.number_input("Quantidade de endereços de entrega / centrais", min_value=1, value=1, step=1, key=f"qtd_end_cont_{rc}")
    equipamentos_contrato = ""
    if qtd_enderecos == 1:
        equipamentos_contrato = st.text_input("Equipamentos", key=f"eq_unico_{rc}")
    else:
        eq_lista_temp = []
        for i in range(1, qtd_enderecos + 1):
            eq_end = st.text_input(f"Equipamentos [Entrega {i}]", key=f"eq_end_{i}_{rc}")
            if eq_end.strip():
                eq_lista_temp.append(f"[Entrega {i}] {eq_end.strip()}")
        equipamentos_contrato = " ".join(eq_lista_temp)

    st.divider()
    st.subheader("5. Comodato / Fornecimento")
    tipo_fornecimento = st.multiselect("Selecione o tipo de fornecimento:", ["Granel", "Cilindro"], key=f"forn_{rc}")

    preco_granel, consumo_granel = "", ""
    p13_preco, p13_qtd, p20_preco, p20_qtd, p45_preco, p45_qtd = "", 0, "", 0, "", 0
    consumo_cilindro_total = 0

    if "Granel" in tipo_fornecimento:
        col_g1, col_g2 = st.columns(2)
        with col_g1: preco_granel = st.text_input("Preço Granel", key=f"p_gran_{rc}")
        with col_g2: consumo_granel = st.text_input("Consumo mensal previsto (kgs)", key=f"c_gran_{rc}")

    if "Cilindro" in tipo_fornecimento:
        st.markdown("**Preços e Quantidades por Modelo de Cilindro:**")
        cc1, cc2, cc3 = st.columns(3)
        with cc1:
            p13_preco = st.text_input("Preço P13", key=f"p13_p_{rc}")
            p13_qtd = st.number_input("Qtd P13", min_value=0, value=0, step=1, key=f"p13_q_{rc}")
        with cc2:
            p20_preco = st.text_input("Preço P20", key=f"p20_p_{rc}")
            p20_qtd = st.number_input("Qtd P20", min_value=0, value=0, step=1, key=f"p20_q_{rc}")
        with cc3:
            p45_preco = st.text_input("Preço P45", key=f"p45_p_{rc}")
            p45_qtd = st.number_input("Qtd P45", min_value=0, value=0, step=1, key=f"p45_q_{rc}")
        
        consumo_cilindro_total = (p13_qtd * 13) + (p20_qtd * 20) + (p45_qtd * 45)

    st.divider()
    observacoes_contrato = st.text_area("Obs.", key=f"obs_c_{rc}")

    st.divider()
    projeto_padrao = st.text_input("Projeto Padrão", key=f"proj_p_{rc}")
    cilindro_projeto = st.checkbox("Cilindros (N/A)", key=f"cil_proj_{rc}")

    st.divider()
    if st.button("📝 Gerar Texto Padrão do Contrato", type="primary", key=f"btn_gen_elab_{rc}"):
        proj_final = "N/A" if cilindro_projeto else projeto_padrao

        texto_padrao_contrato = f"""ELABORAÇÃO DE CONTRATO

Motivo da solicitação: {motivo_solicitacao}

Contato: {contato_contrato}
Telefone: {telefone_contrato}
E-mail: {email_contrato}
Contrato / Aditamento / Distrato: {tipo_contrato}
Mesmo proprietário?: {mesmo_prop}"""

        if mesmo_prop == "Sim":
            texto_padrao_contrato += f"""
CNPJ: {cnpj}
I.E.: {ie}"""
        elif mesmo_prop == "Não":
            texto_padrao_contrato += f"""
Novo CNPJ: {novo_cnpj}
Nova I.E.: {nova_ie}"""

        texto_padrao_contrato += f"""
Endereço padrão ou entrega?: {endereco_padrao}"""

        if "Granel" in tipo_fornecimento:
            texto_padrao_contrato += f"""
Preço Granel: {preco_granel}
Consumo mensal previsto (kgs): {consumo_granel}"""

        if "Cilindro" in tipo_fornecimento:
            cil_precos_str = []
            if p13_preco.strip(): cil_precos_str.append(f"[P13 = {p13_preco} / und]")
            if p20_preco.strip(): cil_precos_str.append(f"[P20 = {p20_preco} / und]")
            if p45_preco.strip(): cil_precos_str.append(f"[P45 = {p45_preco} / und]")
            
            if cil_precos_str:
                texto_padrao_contrato += f"\nPreço Cilindro: " + ", ".join(cil_precos_str)
            else:
                texto_padrao_contrato += f"\nPreço Cilindro: "

            cil_desc_arr = []
            if p13_qtd > 0: cil_desc_arr.append(f"{p13_qtd} und P13")
            if p20_qtd > 0: cil_desc_arr.append(f"{p20_qtd} und P20")
            if p45_qtd > 0: cil_desc_arr.append(f"{p45_qtd} und P45")
            
            desc_str_final = ", ".join(cil_desc_arr) if cil_desc_arr else "0"
            texto_padrao_contrato += f"\nQual consumo mensal previsto (qntd): {desc_str_final}"
            texto_padrao_contrato += f"\nConsumo Previsto (Cilindro): {consumo_cilindro_total} KGs"

        texto_padrao_contrato += f"""
Condição de pagamento: {cond_pagamento}
Vigência: {vigencia}
Equipamentos: {equipamentos_contrato}
Projeto Padrão: {proj_final}

Quem será o responsável pelas NF's pendentes?: {resp_pendentes}
E-mail do novo proprietário que receberá o novo contrato: {email_novo_prop}"""

        if tipo_fluxo == "Enviar para Assinatura":
            texto_padrao_contrato += f"""
Nome da Testemunha: {nome_testemunha}
E-mail da Testemunha: {email_testemunha}
Nome do Responsável pela assinatura: {nome_responsavel}
E-mail do Responsável pela assinatura: {email_responsavel}"""

        texto_padrao_contrato += f"""
Condomínio CONTA SIM?: {conta_sim}"""

        if conta_sim == "Sim":
            texto_padrao_contrato += f"""
N° Unid autônomas (Aptos + áreas comuns/zeladoria): {num_unidades}
Qtd Torres: {qtd_torres}
Qtd Blocos: {qtd_blocos}
Valor preço de religue: {preco_religue}
Valor preço de serviço: {preco_servico}"""

        texto_padrao_contrato += f"""

Obs.: {observacoes_contrato}"""

        st.success("✅ Texto padrão gerado com sucesso!")
        st.text_area("Texto gerado:", value=texto_padrao_contrato, height=200)


# =====================================================================
# TELA 3: GERADOR DE APRESENTAÇÃO DE RESULTADOS
# =====================================================================
elif menu == "📊 Gerador de Apresentação de Resultados":
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

    def criar_apresentacao_pptx(tipo, consultor, periodo, v_atual, f_atual, v_ant, f_ant, clientes):
        if pptx is None:
            raise RuntimeError("A biblioteca python-pptx não está instalada no ambiente.")
        
        prs = pptx.Presentation()
        
        slide_layout_title = prs.slide_layouts[0]
        slide1 = prs.slides.add_slide(slide_layout_title)
        slide1.shapes.title.text = f"Resultados - {tipo}"
        slide1.placeholders[1].text = f"Consultor: {consultor}\nPeríodo: {periodo}"
        
        slide_layout_content = prs.slide_layouts[1]
        slide2 = prs.slides.add_slide(slide_layout_content)
        slide2.shapes.title.text = "Indicadores de Desempenho & Comparativo Anual"
        
        tf = slide2.placeholders[1].text_frame
        tf.text = f"• Total de Clientes Atendidos: {clientes}"
        tf.add_paragraph().text = f"• Volume Atual: {v_atual:.1f} TON (Ano Anterior: {v_ant:.1f} TON)"
        if v_ant > 0:
            cresc_vol = ((v_atual - v_ant) / v_ant) * 100
            tf.add_paragraph().text = f"  -> Crescimento de Volume: {cresc_vol:+.1f}%"
        
        tf.add_paragraph().text = f"• Faturamento Atual: R$ {f_atual:,.2f} (Ano Anterior: R$ {f_ant:,.2f})"
        if f_ant > 0:
            cresc_fat = ((f_atual - f_ant) / f_ant) * 100
            tf.add_paragraph().text = f"  -> Crescimento de Faturamento: {cresc_fat:+.1f}%"

        buffer = BytesIO()
        prs.save(buffer)
        buffer.seek(0)
        return buffer.getvalue()

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
                if pptx is None:
                    st.error("⚠️ A biblioteca `python-pptx` não está instalada no ambiente. Adicione-a ao `requirements.txt` ou instale via pip.")
                else:
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
