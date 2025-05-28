import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
import time
import os
import plotly.graph_objects as go

st.set_page_config(page_title="Go MED SAÚDE - Análise de Estoque", page_icon=":bar_chart:", layout="wide")

CAMINHO_ARQUIVO_ESTOQUE = 'df_estoque.csv'

MESES_ABREVIADOS = {
    1: 'Jan', 2: 'Fev', 3: 'Mar', 4: 'Abr', 5: 'Mai', 6: 'Jun',
    7: 'Jul', 8: 'Ago', 9: 'Set', 10: 'Out', 11: 'Nov', 12: 'Dez'
}

def carregar_dados(caminho_arquivo):
    try:
        df = pd.read_csv(caminho_arquivo)

        df['data ultima compra'] = pd.to_datetime(df['data ultima compra'], errors='coerce')

        df.dropna(subset=['data ultima compra'], inplace=True)

        if df.empty:
            st.warning('O arquivo está vazio ou não contém dados válidos após o pré-processamento.')
            return None
        return df
    except FileNotFoundError:
        st.error('Arquivo não encontrado! Certifique-se de que "df_estoque.csv" está no mesmo diretório.')
        return None
    except Exception as e:
        st.error(f'Ocorreu um erro ao carregar ou processar o arquivo: {e}')
        return None

def formatar_moeda(valor, simbolo_moeda='R$'):
    if pd.isna(valor):
        return ''
    try:
        return f'{simbolo_moeda} {valor:,.2f}'.replace(',', 'x').replace('.', ',').replace('x', '.')
    except (TypeError, ValueError):
        return 'Valor inválido'

# --- Título da Aplicação ---
st.title('📊 Análise de Estoque')

# --- Carregar Dados ---
df_estoque = carregar_dados(CAMINHO_ARQUIVO_ESTOQUE)

if df_estoque is None:
    st.info("Carregue um arquivo 'df_estoque.csv' para visualizar as análises.")
    st.stop()

# --- Filtros Globais (agora no corpo principal, no topo) ---
st.header("Filtros Globais")

# Certifique-se de que a coluna 'data ultima compra' está em formato datetime
# Isso já é feito na função carregar_dados, mas é bom garantir antes de extrair o ano/mês
df_estoque['data ultima compra'] = pd.to_datetime(df_estoque['data ultima compra'], errors='coerce')
df_estoque.dropna(subset=['data ultima compra'], inplace=True) # Remover linhas com datas inválidas

# Extrair Ano e Mês para os filtros
df_estoque['ano_compra'] = df_estoque['data ultima compra'].dt.year
df_estoque['mes_compra'] = df_estoque['data ultima compra'].dt.month

col_filtros_1, col_filtros_2 = st.columns(2)

with col_filtros_1:
    # Seletor de Ano
    todos_anos = ['Todos'] + sorted(df_estoque['ano_compra'].unique().tolist(), reverse=True)
    ano_filtro = st.selectbox("Filtrar por Ano da Última Compra:", todos_anos)

with col_filtros_2:
    # Seletor de Mês (dependente do ano selecionado)
    meses_disponiveis = []
    if ano_filtro != 'Todos':
        meses_disponiveis_no_ano = df_estoque[df_estoque['ano_compra'] == ano_filtro]['mes_compra'].unique().tolist()
        # Mapeia os números dos meses para as abreviações, ordenando pelos números
        meses_disponiveis = sorted([MESES_ABREVIADOS[m] for m in meses_disponiveis_no_ano], 
                                    key=lambda x: list(MESES_ABREVIADOS.values()).index(x))
    
    todos_meses = ['Todos'] + meses_disponiveis
    mes_filtro = st.selectbox("Filtrar por Mês da Última Compra:", todos_meses)

# Aplicar filtros
df_filtrado = df_estoque.copy()

if ano_filtro != 'Todos':
    df_filtrado = df_filtrado[df_filtrado['ano_compra'] == ano_filtro]

if mes_filtro != 'Todos':
    # Converter o mês abreviado de volta para número para filtrar
    num_mes_selecionado = None
    for num, abbrev in MESES_ABREVIADOS.items():
        if abbrev == mes_filtro:
            num_mes_selecionado = num
            break
    if num_mes_selecionado is not None:
        df_filtrado = df_filtrado[df_filtrado['mes_compra'] == num_mes_selecionado]


st.markdown("---") 


## Visão Geral do Estoque
st.header("Visão Geral do Estoque")
col1, col2, col3 = st.columns(3)

total_produtos = df_filtrado['produto'].nunique()
total_itens_fisicos = df_filtrado['quantidade fisica'].sum()
valor_total_estoque = (df_filtrado['quantidade fisica'] * df_filtrado['custo liquido entrada']).sum()

col1.metric("Total de Produtos Únicos", total_produtos)
col2.metric("Total de Itens Físicos", f"{total_itens_fisicos:,.0f}".replace(",", "X").replace(".", ",").replace("X", "."))
col3.metric("Valor Total do Estoque", formatar_moeda(valor_total_estoque))


if not df_filtrado.empty:
    df_agrupado_fabricante = df_filtrado.groupby('fabricante')['quantidade fisica'].sum().reset_index()
    
    # Ordena os fabricantes pela quantidade física em ordem decrescente e pega os 10 maiores
    df_top_10_fabricantes = df_agrupado_fabricante.sort_values(by='quantidade fisica', ascending=False).head(10)
    
    fig = px.bar(df_top_10_fabricantes, x='fabricante', y='quantidade fisica',
                 title='Top 10 Fabricantes por Quantidade Física', # Mudei o título do gráfico
                 labels={'quantidade fisica': 'Quantidade Física Total', 'fabricante': 'Fabricante'})
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Nenhum dado para exibir com os filtros selecionados.")

st.markdown("---")


## 1. Disponibilidade Real vs. Demanda
st.header("1. Disponibilidade Real vs. Solicitada/Reservada")
st.markdown("Compare o que você tem em estoque com o que está sendo solicitado e reservado para entender sua capacidade de atender à demanda.")

if not df_filtrado.empty:
    
    df_resumo_quantidades = df_filtrado.groupby('produto').agg(
        quantidade_fisica=('quantidade fisica', 'sum'),
        quantidade_solicitada=('quantidade solicitada', 'sum'),
        quantidade_reservada=('quantidade reservada', 'sum'),
        quantidade_disponivel=('quantidade disponivel', 'sum')
    ).reset_index()

    if not df_resumo_quantidades.empty:
        st.dataframe(df_resumo_quantidades)
    else:
        st.info("Nenhum dado para exibir com os filtros selecionados para o comparativo de quantidades.")

    st.subheader("Produtos com Baixa Disponibilidade")
    # Troca st.slider por st.number_input para permitir digitação
    limite_disponibilidade = st.number_input(
        "Mostrar produtos com 'quantidade disponivel' abaixo de:",
        min_value=0, # Valor mínimo que pode ser digitado
        # max_value pode ser um valor alto fixo ou baseado nos seus dados.
        # Se df_filtrado estiver vazio, int() dará erro se não houver um fallback.
        max_value=int(df_filtrado['quantidade disponivel'].max() if not df_filtrado.empty and 'quantidade disponivel' in df_filtrado.columns else 1000), 
        value=10, # Valor inicial
        step=1, # Passo de incremento/decremento
        key="disp_input_filter" # Chave única para o widget
    )

    produtos_baixa_disponibilidade = df_filtrado[
        (df_filtrado['quantidade disponivel'] < limite_disponibilidade) &
        (df_filtrado['quantidade disponivel'] >= 0) # Adicionado para garantir que só pega valores não negativos, se aplicável
    ].sort_values(by='quantidade solicitada', ascending=False)

    if not produtos_baixa_disponibilidade.empty:
        st.dataframe(produtos_baixa_disponibilidade[['produto', 'fabricante', 'quantidade fisica', 'quantidade solicitada', 'quantidade reservada', 'quantidade disponivel']])
    else:
        st.info("Nenhum produto com disponibilidade abaixo do limite selecionado.")
else:
    st.info("Nenhum dado para exibir com os filtros selecionados.")

st.markdown("---")


## 2. Análise de Avarias
st.header("2. Análise de Avarias")

if not df_filtrado.empty:
    df_avariado = df_filtrado[df_filtrado['quantidade avariada'] > 0].copy()

    if not df_avariado.empty:
        df_avariado['porcentagem_avaria'] = (df_avariado['quantidade avariada'] / df_avariado['quantidade fisica']) * 100
        df_avariado.fillna(0, inplace=True)

        st.dataframe(df_avariado[['produto', 'fabricante', 'quantidade fisica', 'quantidade avariada', 'porcentagem_avaria']].sort_values(by='quantidade avariada', ascending=False))
    else:
        st.info("Nenhum item avariado encontrado com os filtros selecionados.")
else:
    st.info("Nenhum dado para exibir com os filtros selecionados.")

st.markdown("---")


## 3. Análise de Estoque Parado/Baixo Giro
st.header("3. Análise de Estoque Parado/Baixo Giro")

if not df_filtrado.empty:
    hoje = pd.to_datetime(datetime.date.today())
    df_filtrado['dias_desde_ultima_compra'] = (hoje - df_filtrado['data ultima compra']).dt.days

    st.subheader("Estoque com Última Compra Antiga e Quantidade Física Alta")
    limite_dias_compra = st.slider("Considerar estoque parado se a última compra foi há mais de (dias):",
                                     min_value=30, max_value=730, value=180, key="dias_compra_slider") 
    
    estoque_parado = df_filtrado[
        (df_filtrado['dias_desde_ultima_compra'] > limite_dias_compra) &
        (df_filtrado['quantidade fisica'] > 0)
    ].sort_values(by='dias_desde_ultima_compra', ascending=False)

    if not estoque_parado.empty:
        st.dataframe(estoque_parado[['produto', 'fabricante', 'quantidade fisica', 'data ultima compra', 'dias_desde_ultima_compra']])
        
    else:
        st.info("Nenhum estoque parado encontrado com os critérios selecionados.")
else:
    st.info("Nenhum dado para exibir com os filtros selecionados.")

st.markdown("---")


## 4. Identificação de Produtos Críticos
st.header("4. Identificação de Produtos Críticos")
st.markdown("Destaque produtos que exigem atenção imediata devido à alta demanda e baixa disponibilidade.")

if not df_filtrado.empty:
    min_disponivel = st.slider("Limite máximo para 'quantidade disponivel' para ser considerado crítico:",
                                 min_value=0, max_value=int(df_filtrado['quantidade disponivel'].max() if not df_filtrado.empty else 50),
                                 value=5, key="critico_slider") # Adicionado key
    
    produtos_criticos = df_filtrado[
        (df_filtrado['quantidade disponivel'] < min_disponivel) &
        (df_filtrado['quantidade solicitada'] > 0)
    ].sort_values(by='quantidade solicitada', ascending=False)

    if not produtos_criticos.empty:
        st.subheader("Produtos Críticos (Baixa Disponibilidade e Alta Demanda)")
        st.dataframe(produtos_criticos[['produto', 'fabricante', 'quantidade fisica', 'quantidade solicitada', 'quantidade disponivel']])

        fig_criticos = px.bar(
            produtos_criticos,
            x='produto',
            y=['quantidade disponivel', 'quantidade solicitada'],
            barmode='group',
            title='Produtos Críticos: Disponibilidade vs. Solicitação',
            labels={'value': 'Quantidade', 'variable': 'Tipo de Estoque'}
        )
        st.plotly_chart(fig_criticos, use_container_width=True)
    else:
        st.info("Nenhum produto crítico encontrado com os critérios selecionados.")
else:
    st.info("Nenhum dado para exibir com os filtros selecionados.")

st.markdown("---")


## 5. Desempenho por Fabricante
st.header("5. Desempenho por Fabricante")

if not df_filtrado.empty:
    df_desempenho_fabricante = df_filtrado.groupby('fabricante').agg(
        total_quantidade_fisica=('quantidade fisica', 'sum'),
        total_quantidade_avariada=('quantidade avariada', 'sum'),
        total_quantidade_disponivel=('quantidade disponivel', 'sum'),
        total_quantidade_solicitada=('quantidade solicitada', 'sum'),
        contagem_produtos=('produto', 'nunique')
    ).reset_index()

    st.subheader("Métricas Agregadas por Fabricante")
    st.dataframe(df_desempenho_fabricante.sort_values(by='total_quantidade_fisica', ascending=False))


else:
    st.info("Nenhum dado para exibir com os filtros selecionados.")