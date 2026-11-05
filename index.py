
import csv
import re
import unicodedata
import html
from pathlib import Path
from difflib import SequenceMatcher
from datetime import datetime

import streamlit as st
import pandas as pd
import numpy as np
from PIL import Image

try:
    import zxingcpp
except ImportError:
    zxingcpp = None


# ==================================================
# CONFIGURAÇÕES
# ==================================================

st.set_page_config(
    page_title="PriceVision",
    page_icon="🛒",
    layout="wide"
)

ARQUIVO_CSV = Path(__file__).with_name("produtos.csv")

st.markdown("""
<style>

/* SITE */

.stApp {
    background: #FFF9F1;
    color: #38251C;
}

[data-testid="stMainBlockContainer"] {
    max-width: 1200px;
    padding-top: 2rem;
    padding-bottom: 100px;
}

.topo {
    background: linear-gradient(120deg, #57270F, #8B451C);
    padding: 30px;
    border-radius: 18px;
    margin-bottom: 25px;
}

.topo h1 {
    color: white !important;
    font-size: 38px;
}

.topo p {
    color: #FFD18B;
}

h1, h2, h3 {
    color: #57270F;
}

.stButton button,
.stFormSubmitButton button {
    background: #F28C16;
    color: #57270F;
    border-radius: 10px;
    font-weight: bold;
    border: none;
    min-height: 42px;
}

/* BOTÃO FLUTUANTE */

.st-key-botao_chat {
    position: fixed !important;
    right: 25px !important;
    bottom: 20px !important;
    width: 68px !important;
    z-index: 999999 !important;
}

.st-key-botao_chat button {
    width: 65px !important;
    height: 65px !important;
    border-radius: 50% !important;
    background: #57270F !important;
    color: white !important;
    font-size: 26px !important;
    border: 3px solid white !important;
    box-shadow: 0 5px 20px #0004 !important;
}

/* BALÃO DO CHAT */

.st-key-balao_chat {
    position: fixed !important;
    right: 25px !important;
    bottom: 100px !important;
    width: 390px !important;
    max-width: calc(100vw - 30px) !important;
    height: 610px !important;
    max-height: calc(100vh - 125px) !important;
    overflow-y: auto !important;
    background: #FFF9F1 !important;
    border: 2px solid #57270F !important;
    border-radius: 18px !important;
    padding: 14px !important;
    z-index: 999998 !important;
    box-shadow: 0 8px 35px #0004 !important;
}

/* CABEÇALHO */

.cabecalho-chat {
    background: linear-gradient(120deg, #57270F, #8B451C);
    color: white;
    padding: 16px;
    border-radius: 12px;
    margin-bottom: 12px;
}

.cabecalho-chat h3 {
    color: white !important;
    margin: 0;
}

.cabecalho-chat p {
    color: #FFD18B;
    font-size: 12px;
    margin: 5px 0 0 0;
}

/* PRODUTOS */

.produto-card {
    background: white;
    border: 1px solid #EAD8C5;
    border-radius: 12px;
    padding: 12px;
    margin-bottom: 10px;
}

.produto-card h4 {
    color: #57270F;
    margin-top: 0;
}

/* CELULAR */

@media(max-width: 600px) {

    .st-key-balao_chat {
        right: 10px !important;
        bottom: 85px !important;
        width: calc(100vw - 20px) !important;
        height: 75vh !important;
        max-height: 75vh !important;
    }

    .st-key-botao_chat {
        right: 15px !important;
        bottom: 12px !important;
    }

}

</style>
""", unsafe_allow_html=True)


# ==================================================
# NORMALIZAÇÃO
# ==================================================

def normalizar(texto):

    texto = str(texto or "").lower().strip()

    texto = unicodedata.normalize("NFD", texto)

    texto = "".join(
        c for c in texto
        if unicodedata.category(c) != "Mn"
    )

    texto = re.sub(r"[^a-z0-9\s]", " ", texto)

    texto = re.sub(r"\s+", " ", texto)

    return texto.strip()


def parecido(a, b):

    a = normalizar(a)
    b = normalizar(b)

    if not a or not b:
        return False

    if a == b:
        return True

    if min(len(a), len(b)) < 4:
        return False

    return SequenceMatcher(None, a, b).ratio() >= 0.82


def contem_algum(texto, lista):

    texto = normalizar(texto)
    palavras = texto.split()

    for termo in lista:

        termo = normalizar(termo)

        if not termo:
            continue

        if termo in texto:
            return True

        if any(parecido(p, termo) for p in palavras):
            return True

    return False


# ==================================================
# CARREGAR CSV
# ==================================================

def carregar_produtos():

    if not ARQUIVO_CSV.exists():
        return []

    codificacoes = ["utf-8-sig", "cp1252", "latin-1"]

    for codificacao in codificacoes:

        try:

            with open(
                ARQUIVO_CSV,
                "r",
                encoding=codificacao,
                newline=""
            ) as arquivo:

                amostra = arquivo.read(4096)
                arquivo.seek(0)

                try:
                    delimitador = csv.Sniffer().sniff(
                        amostra,
                        delimiters=",;\t"
                    ).delimiter
                except csv.Error:
                    delimitador = ","

                leitor = csv.DictReader(
                    arquivo,
                    delimiter=delimitador
                )

                if not leitor.fieldnames:
                    return []

                colunas = {
                    normalizar(nome).replace(" ", "_"): nome
                    for nome in leitor.fieldnames
                    if nome
                }

                coluna_produto = (
                    colunas.get("produtos")
                    or colunas.get("produto")
                )

                coluna_mercado = (
                    colunas.get("empresas")
                    or colunas.get("empresa")
                    or colunas.get("mercado")
                )

                coluna_preco = (
                    colunas.get("preco_normal")
                    or colunas.get("preco")
                )

                coluna_desconto = colunas.get(
                    "preco_com_desconto"
                )

                coluna_categoria = colunas.get("categoria")
                coluna_promocao = colunas.get("promocao")
                coluna_desconto_percentual = colunas.get("desconto")
                coluna_inicio = colunas.get("inicio_da_promocao")
                coluna_validade = colunas.get("validade")

                coluna_codigo = (
                    colunas.get("codigo_barras")
                    or colunas.get("codigo_de_barras")
                    or colunas.get("codigo")
                )

                if not coluna_produto or not coluna_preco:
                    st.error(
                        "O CSV precisa ter as colunas "
                        "'produtos' e 'preco_normal' ou "
                        "'produto' e 'preco'."
                    )
                    return []

                produtos = []

                for linha in leitor:

                    nome = (
                        linha.get(coluna_produto) or ""
                    ).strip()

                    if not nome:
                        continue

                    def pegar(coluna):

                        if not coluna:
                            return ""

                        return (
                            linha.get(coluna) or ""
                        ).strip()

                    produtos.append({

                        "nome": nome,

                        "mercado": pegar(coluna_mercado),

                        "preco": pegar(coluna_preco),

                        "preco_desconto": pegar(coluna_desconto),

                        "categoria": pegar(coluna_categoria),

                        "promocao": pegar(coluna_promocao),

                        "desconto": pegar(coluna_desconto_percentual),

                        "inicio": pegar(coluna_inicio),

                        "validade": pegar(coluna_validade),

                        "codigo": pegar(coluna_codigo)

                    })

                return produtos

        except UnicodeDecodeError:
            continue

        except Exception as erro:

            st.error(f"Erro ao carregar CSV: {erro}")

            return []

    return []


# ==================================================
# PREÇOS
# ==================================================

def converter_preco(valor):

    if not valor:
        return None

    valor = str(valor).strip()

    valor = valor.replace("R$", "").replace(" ", "")

    if "," in valor:
        valor = valor.replace(".", "")
        valor = valor.replace(",", ".")

    try:
        return float(valor)
    except ValueError:
        return None


def formatar_preco(valor):

    numero = converter_preco(valor)

    if numero is None:
        return "Preço não informado"

    texto = f"{numero:,.2f}"

    texto = (
        texto.replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )

    return f"R$ {texto}"


# ==================================================
# PESQUISA INTELIGENTE
# ==================================================

def produto_corresponde(nome_produto, mensagem):

    nome = normalizar(nome_produto)
    texto = normalizar(mensagem)

    if not nome or not texto:
        return False

    if nome in texto:
        return True

    palavras_nome = [
        p for p in nome.split()
        if len(p) >= 4 and p not in ["para", "com"]
    ]

    palavras_texto = [
        p for p in texto.split()
        if len(p) >= 4
    ]

    if not palavras_nome:
        return False

    correspondencias = 0

    for palavra_nome in palavras_nome:

        if any(
            parecido(palavra_nome, palavra_texto)
            for palavra_texto in palavras_texto
        ):
            correspondencias += 1

    minimo = 1 if len(palavras_nome) == 1 else 2

    return correspondencias >= min(
        minimo,
        len(palavras_nome)
    )


def consultar_produtos(mensagem, produtos):

    encontrados = [
        p for p in produtos
        if produto_corresponde(p["nome"], mensagem)
    ]

    return encontrados[:10]


def consultar_codigo(codigo, produtos):

    codigo = str(codigo).strip()

    return [
        p for p in produtos
        if str(p["codigo"]).strip() == codigo
    ]


# ==================================================
# PROMOÇÕES
# ==================================================

def promocao_ativa(produto):

    return normalizar(produto["promocao"]) in [
        "ativada", "ativa", "sim", "true"
    ]


# ==================================================
# RESPOSTAS DO CHATBOT
# ==================================================

SAUDACOES = [
    "oi", "ola", "eai", "e ai",
    "bom dia", "boa tarde", "boa noite",
    "opa", "salve"
]

AGRADECIMENTOS = [
    "obrigado", "obrigada", "valeu",
    "agradeco", "brigado", "brigada"
]

DESPEDIDAS = [
    "tchau", "ate mais", "falou",
    "fui", "adeus", "ate logo"
]

GIRIAS = [
    "mano", "cara", "parceiro", "bro",
    "top", "massa", "daora", "legal",
    "show", "suave", "tranquilo", "blz",
    "beleza", "vlw", "tmj", "kkk",
    "kkkk", "mds", "nossa", "brabo",
    "sinistro", "zoeira", "tlg", "tendeu",
    "vdd", "tbm", "tb", "vc", "vcs"
]

ATENDIMENTO = [
    "atendente", "humano", "falar com alguem",
    "suporte", "atendimento humano"
]


def responder(mensagem, produtos):

    texto = normalizar(mensagem)

    if not texto:
        return "Digite uma mensagem para conversarmos."

    if texto in ["sair", "encerrar", "fechar", "parar"]:
        return "Se precisar de ajuda, estarei por aqui!"

    if contem_algum(texto, SAUDACOES):

        return (
            "Olá! Tudo bem? 🛒\n\n"
            "Sou o assistente PriceVision!\n\n"
            "Posso consultar produtos, preços e promoções "
            "da nossa planilha."
        )

    if contem_algum(texto, AGRADECIMENTOS):
        return "De nada! Estou aqui para ajudar! 😊"

    if contem_algum(texto, DESPEDIDAS):
        return "Até mais! Volte sempre! 👋"

    if contem_algum(texto, ATENDIMENTO):

        return (
            "Sou um chatbot automático do PriceVision. "
            "No momento não consigo chamar um atendente real."
        )

    if any(t in texto for t in [
        "ajuda", "comandos", "como funciona",
        "o que voce faz", "o que pode fazer"
    ]):

        return (
            "Veja o que você pode perguntar:\n\n"
            "• Qual o preço do arroz?\n"
            "• Preciso de molho de tomate.\n"
            "• Onde encontro café?\n"
            "• Quais são as promoções?\n"
            "• Quantos produtos estão cadastrados?\n\n"
            "Você também pode enviar uma foto do código de barras!"
        )

    if "quantos produtos" in texto:

        return f"Temos {len(produtos)} produtos cadastrados! 🛒"

    if any(t in texto for t in [
        "promocao", "promocoes", "oferta", "ofertas"
    ]):

        promocionais = [
            p for p in produtos if promocao_ativa(p)
        ]

        if not promocionais:
            return "Não encontrei promoções ativas."

        return (
            f"Encontrei {len(promocionais)} produtos "
            "com promoção ativa! Confira os resultados abaixo."
        )

    encontrados = consultar_produtos(mensagem, produtos)

    if encontrados:

        return (
            f"Encontrei {len(encontrados)} produto(s) "
            "que podem corresponder à sua pesquisa! 🛒"
        )

    if contem_algum(texto, GIRIAS):

        return (
            "Suave! 😎 Ainda não entendi exatamente "
            "o que você procura. Me fale o nome do produto."
        )

    return (
        "Não encontrei esse produto na planilha. 😕\n\n"
        "Tente escrever outro nome ou enviar uma foto "
        "do código de barras."
    )


# ==================================================
# CADASTRAR PRODUTO ESCANEADO
# ==================================================

def cadastrar_produto(codigo, nome, preco, mercado):

    codigo = str(codigo).strip()
    nome = str(nome).strip()
    mercado = str(mercado).strip()

    if not codigo or not nome or not mercado:
        raise ValueError("Preencha todos os campos.")

    valor = converter_preco(preco)

    if valor is None or valor <= 0:
        raise ValueError("Informe um preço válido.")

    produtos = carregar_produtos()

    if any(p["codigo"] == codigo for p in produtos):
        return False

    novo = {
        "codigo_barras": codigo,
        "produto": nome,
        "preco": f"{valor:.2f}",
        "mercado": mercado,
        "data_cadastro": datetime.now().strftime(
            "%d/%m/%Y %H:%M"
        )
    }

    existe = ARQUIVO_CSV.exists()

    with open(
        ARQUIVO_CSV,
        "a",
        encoding="utf-8-sig",
        newline=""
    ) as arquivo:

        campos = [
            "codigo_barras",
            "produto",
            "preco",
            "mercado",
            "data_cadastro"
        ]

        escritor = csv.DictWriter(
            arquivo,
            fieldnames=campos
        )

        if not existe or ARQUIVO_CSV.stat().st_size == 0:
            escritor.writeheader()

        escritor.writerow(novo)

    return True


# ==================================================
# LEITOR DE CÓDIGO DE BARRAS
# ==================================================

def ler_codigo(imagem):

    if zxingcpp is None:

        raise RuntimeError(
            "Biblioteca não instalada. "
            "Execute: pip install zxing-cpp"
        )

    imagem_pil = Image.open(imagem).convert("RGB")

    imagem_array = np.array(imagem_pil)

    resultados = zxingcpp.read_barcodes(imagem_array)

    if not resultados:
        return None

    return resultados[0].text


# ==================================================
# ESTADOS
# ==================================================

if "chat_aberto" not in st.session_state:
    st.session_state.chat_aberto = False

if "historico" not in st.session_state:

    st.session_state.historico = [
        {
            "role": "assistant",
            "content": (
                "Olá! 👋 Seja bem-vindo ao PriceVision!\n\n"
                "Como posso ajudar você a encontrar um produto?"
            )
        }
    ]

if "resultados" not in st.session_state:
    st.session_state.resultados = []

if "codigo_lido" not in st.session_state:
    st.session_state.codigo_lido = None


# ==================================================
# SITE
# ==================================================

st.markdown("""
<div class="topo">
    <h1>🛒 PriceVision</h1>
    <p>Seu assistente inteligente de produtos e preços.</p>
</div>
""", unsafe_allow_html=True)

st.title("Encontre seus produtos")

st.write(
    "Consulte produtos, preços e promoções "
    "cadastrados no PriceVision."
)

produtos = carregar_produtos()

st.metric("Produtos disponíveis", len(produtos))

if produtos:

    tabela = pd.DataFrame(produtos)

    st.dataframe(
        tabela[[
            "nome",
            "mercado",
            "preco",
            "preco_desconto",
            "categoria"
        ]],
        use_container_width=True,
        hide_index=True
    )

else:

    st.info("Nenhum produto encontrado na planilha.")


# ==================================================
# BOTÃO FLUTUANTE
# ==================================================

st.button(
    "💬",
    key="botao_chat",
    help="Abrir atendimento PriceVision",
    on_click=lambda: st.session_state.update(
        chat_aberto=not st.session_state.chat_aberto
    )
)


# ==================================================
# BALÃO DO CHATBOT
# ==================================================

if st.session_state.chat_aberto:

    with st.container(key="balao_chat"):

        st.markdown("""
        <div class="cabecalho-chat">
            <h3>🛒 PriceVision</h3>
            <p>● Assistente online</p>
        </div>
        """, unsafe_allow_html=True)

        col1, col2 = st.columns([4, 1])

        with col1:
            st.caption("Atendimento de produtos e preços")

        with col2:

            if st.button("✖", key="fechar_balao"):
                st.session_state.chat_aberto = False
                st.rerun()

        st.divider()

        # CONVERSA

        for mensagem in st.session_state.historico:

            with st.chat_message(mensagem["role"]):
                st.markdown(mensagem["content"])

        # RESULTADOS

        for produto in st.session_state.resultados:

            nome = html.escape(produto["nome"])
            mercado = html.escape(produto["mercado"])
            codigo = html.escape(produto["codigo"])

            st.markdown(
                f"""
                <div class="produto-card">
                    <h4>🛒 {nome}</h4>
                    <p><b>Preço normal:</b> {html.escape(formatar_preco(produto["preco"]))}</p>
                    <p><b>Mercado:</b> {mercado or "Não informado"}</p>
                    <p><b>Categoria:</b> {html.escape(produto["categoria"] or "Não informada")}</p>
                    <p><b>Código:</b> {codigo or "Não informado"}</p>
                </div>
                """,
                unsafe_allow_html=True
            )

            normal = converter_preco(produto["preco"])
            desconto = converter_preco(produto["preco_desconto"])

            if (
                desconto is not None
                and normal is not None
                and desconto < normal
            ):

                st.success(
                    f"Preço promocional: {formatar_preco(produto['preco_desconto'])}"
                )

            if promocao_ativa(produto):

                st.caption(
                    f"🔥 Promoção ativa | Desconto: "
                    f"{produto['desconto'] or 'Não informado'}"
                )

                if produto["inicio"]:
                    st.caption(f"Início: {produto['inicio']}")

                if produto["validade"]:
                    st.caption(f"Validade: {produto['validade']}")

        # MENSAGEM

        with st.form("formulario_chat", clear_on_submit=True):

            pergunta = st.text_input(
                "Mensagem",
                placeholder="Ex: Quanto custa o arroz?"
            )

            enviar = st.form_submit_button(
                "Enviar ➤",
                use_container_width=True
            )

        if enviar and pergunta.strip():

            st.session_state.historico.append({
                "role": "user",
                "content": pergunta
            })

            st.session_state.resultados = []

            if any(t in normalizar(pergunta) for t in [
                "promocao", "promocoes", "oferta", "ofertas"
            ]):

                encontrados = [
                    p for p in produtos if promocao_ativa(p)
                ]

                st.session_state.resultados = encontrados[:10]

            else:

                st.session_state.resultados = consultar_produtos(
                    pergunta,
                    produtos
                )

            resposta = responder(pergunta, produtos)

            st.session_state.historico.append({
                "role": "assistant",
                "content": resposta
            })

            st.rerun()

        st.divider()

        # ESCANER DENTRO DO BALÃO

        st.markdown("### 📷 Escanear produto")

        st.caption(
            "Tire uma foto ou envie uma imagem "
            "do código de barras."
        )

        tipo = st.radio(
            "Como deseja enviar?",
            ["Tirar foto", "Anexar imagem"],
            horizontal=True,
            key="tipo_imagem"
        )

        imagem = None

        if tipo == "Tirar foto":

            imagem = st.camera_input(
                "Fotografar código de barras",
                key="camera_pricevision"
            )

        else:

            imagem = st.file_uploader(
                "Selecionar imagem",
                type=["png", "jpg", "jpeg", "webp"],
                key="arquivo_pricevision"
            )

        if imagem is not None:

            st.image(imagem, width=200)

            if st.button(
                "🔎 Identificar produto",
                key="identificar_produto",
                use_container_width=True
            ):

                try:

                    codigo = ler_codigo(imagem)

                    if codigo:

                        encontrados = consultar_codigo(
                            codigo,
                            produtos
                        )

                        st.session_state.codigo_lido = codigo

                        if encontrados:

                            st.session_state.resultados = encontrados

                            st.session_state.historico.append({
                                "role": "assistant",
                                "content": (
                                    f"Encontrei o produto correspondente "
                                    f"ao código **{codigo}**! 🛒"
                                )
                            })

                        else:

                            st.session_state.resultados = []

                            st.session_state.historico.append({
                                "role": "assistant",
                                "content": (
                                    f"Identifiquei o código **{codigo}**, "
                                    "mas ele ainda não está cadastrado. "
                                    "Você pode cadastrá-lo abaixo."
                                )
                            })

                        st.rerun()

                    else:

                        st.error(
                            "Não consegui ler o código. "
                            "Tente outra foto com boa iluminação."
                        )

                except Exception as erro:

                    st.error(str(erro))

        # CADASTRAR PRODUTO

        codigo = st.session_state.codigo_lido

        if codigo:

            encontrados = consultar_codigo(codigo, produtos)

            if encontrados:

                st.success("Produto já cadastrado!")

            else:

                st.divider()

                st.markdown("### ➕ Cadastrar produto")

                with st.form("form_cadastro"):

                    st.text_input(
                        "Código identificado",
                        value=codigo,
                        disabled=True
                    )

                    nome = st.text_input("Nome do produto")

                    preco = st.text_input(
                        "Preço",
                        placeholder="Ex: 19,90"
                    )

                    mercado = st.text_input("Mercado")

                    salvar = st.form_submit_button(
                        "Salvar produto",
                        use_container_width=True
                    )

                if salvar:

                    try:

                        sucesso = cadastrar_produto(
                            codigo,
                            nome,
                            preco,
                            mercado
                        )

                        if sucesso:

                            st.session_state.historico.append({
                                "role": "assistant",
                                "content": (
                                    "Produto cadastrado com sucesso! 🎉"
                                )
                            })

                            st.session_state.codigo_lido = None

                            st.rerun()

                        else:

                            st.warning(
                                "Esse código já está cadastrado."
                            )

                    except Exception as erro:

                        st.error(str(erro))

        # LIMPAR CONVERSA

        if st.button(
            "🧹 Limpar conversa",
            key="limpar_conversa",
            use_container_width=True
        ):

            st.session_state.historico = [
                {
                    "role": "assistant",
                    "content": (
                        "Olá! 👋 Como posso ajudar você?"
                    )
                }
            ]

            st.session_state.resultados = []
            st.session_state.codigo_lido = None

            st.rerun()


# ==================================================
# RODAPÉ
# ==================================================

st.divider()

st.caption(
    "PriceVision © - Assistente inteligente de produtos e mercados."
)
