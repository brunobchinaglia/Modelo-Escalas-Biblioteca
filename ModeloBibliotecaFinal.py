from gspread_dataframe import get_as_dataframe
from pyscipopt import Model, quicksum
from datetime import date, datetime
from collections import defaultdict
import matplotlib.pyplot as plt
from PIL import Image
import pandas as pd
import numpy as np
import webbrowser
import traceback
import calendar
import gspread
import bisect
import math
import sys
import csv
import os
import io

def atualizar_funcionarias(caminho_arquivo, FUNCIONARIAS):
    # Posições fixas conforme os dias
    posicoes_fixas = {
        "quartas e quintas": 1,
        "segundas e tercas": 2,
        "tercas e quartas": 3
    }

    # Lê as 3 primeiras linhas e associa os nomes às posições corretas
    novas_posicoes = {}
    with open(caminho_arquivo, newline='', encoding='utf-8') as csvfile:
        leitor = csv.reader(csvfile)
        for _ in range(3):
            linha = next(leitor)
            dias = linha[0].strip().lower()
            nome = linha[1].strip().upper()
            if dias in posicoes_fixas:
                pos = posicoes_fixas[dias]
                novas_posicoes[pos] = nome

    # Remove as antigas entradas rotativas (SANDRA, BIA, GISLENE)
    for nome in ["SANDRA", "BIA", "GISLENE"]:
        FUNCIONARIAS.pop(nome, None)

    # Adiciona os nomes atualizados nas posições certas
    for posicao, nome in novas_posicoes.items():
        FUNCIONARIAS[nome] = posicao

def resource_path(relative_path):
    """
    Retorna o caminho absoluto do recurso, funcionando tanto em .py quanto em .exe (PyInstaller).
    """
    try:
        # PyInstaller cria a pasta temporária e armazena em _MEIPASS
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

# Caminho para seu arquivo de credenciais no Google Drive
arquivo_credencial = resource_path("direct-plasma-459913-t4-d69064b9f4bc.json")

# Autenticação
gc = gspread.service_account(filename=arquivo_credencial)

# ---- Exporta respostas do forms ----
nome_planilha_forms = "Escala de Horário - Consulta (respostas)"
sh_forms = gc.open(nome_planilha_forms)
aba_forms = sh_forms.get_worksheet(0)

df_forms = get_as_dataframe(aba_forms, evaluate_formulas=True)
df_forms.dropna(how='all', inplace=True)
df_forms.to_csv("respostas_forms.csv", index=False)

# 1. Cria o novo nome para a planilha
data_hora_processamento = datetime.now().strftime("%Y-%m-%d %H:%M")
novo_nome = f"Respostas Escala ({data_hora_processamento})"

# 2. Usa o método .update_title() para renomear o arquivo no Google Drive
print(f"Renomeando a planilha para: '{novo_nome}'...")
sh_forms.update_title(novo_nome)

print("✔️ 'respostas_forms.csv' exportado com sucesso!")

# ---- Exporta dados da planilha de feriados ----
nome_planilha_feriados = "Restrições Semestre"
gc = gspread.service_account(filename=arquivo_credencial) # Use a variável 'arquivo_credencial' aqui
sh = gc.open(nome_planilha_feriados)
aba_feriados = sh.get_worksheet(0)

# Pega todos os valores como lista de listas
valores = aba_feriados.get_all_values()

# Constrói DataFrame sem definir header
df_feriados = pd.DataFrame(valores)

# Remove linhas totalmente vazias
df_feriados.replace("", pd.NA, inplace=True)
df_feriados.dropna(how='all', inplace=True)

# Exporta para CSV
df_feriados.to_csv("TabelaRestricao.csv", index=False, header=False)

print("✔️ 'TabelaRestricao.csv' exportado com sucesso sem cabeçalhos!")

# Carrega o CSV
df = pd.read_csv("respostas_forms.csv")

# Dicionário de funcionárias
FUNCIONARIAS = {
    # STI            Escala Noturna
    "JULIANA": 0,   # ---
    "SANDRA": 1,    # Quarta e Quinta
    "BIA": 2,       # Segunda e Terça
    "GISLENE": 3,   # Terça e Quarta
    # SAU
    "ANA": 4,       # ---
    "IRENE": 5,     # Segunda e Terça
    "REGINA": 6     # Quarta e Quinta
}
atualizar_funcionarias("TabelaRestricao.csv", FUNCIONARIAS)
print(FUNCIONARIAS)
n_funcionarios = len(FUNCIONARIAS)

# Normaliza nomes (tira espaços e põe maiúsculo)
df['NOME'] = df['Nome'].astype(str).str.strip().str.upper()

# Filtra apenas quem está no dicionário
df_filtrado = df[df['NOME'].isin(FUNCIONARIAS)]
df_filtrado.loc[:, 'IDX'] = df_filtrado['NOME'].map(FUNCIONARIAS)

# Seleciona colunas de sexta e sábado
colunas_sexta = [col for col in df.columns if 'SEXTA' in col.upper()]
colunas_sabado = [col for col in df.columns if 'SÁBADO' in col.upper()]

# Função que normaliza E mapeia, com um valor padrão
def normaliza_e_mapeia(valor):
    """
    Limpa a string de entrada, converte para maiúsculas e mapeia para um valor numérico.
    Retorna 0 para qualquer valor não mapeado.
    """
    # 1. Mapeamento principal
    resposta_para_valor = {
        "GOSTARIA": 3,
        "INDIFERENTE": 2,
        "NÃO GOSTARIA": 1,
    }

    # 2. Normalização do valor de entrada
    valor_normalizado = valor
    if isinstance(valor, str):
        valor_normalizado = valor.strip().upper()

    # 3. Mapeamento com valor padrão 0 usando .get()
    return resposta_para_valor.get(valor_normalizado, 0)

# Aplica a nova função a todas as células dos dataframes selecionados
asex_df = df_filtrado[colunas_sexta].applymap(normaliza_e_mapeia)
asab_df = df_filtrado[colunas_sabado].applymap(normaliza_e_mapeia)

# asex_df = df_filtrado[colunas_sexta].apply(lambda col: col.map(normaliza_e_mapeia))
# asab_df = df_filtrado[colunas_sabado].apply(lambda col: col.map(normaliza_e_mapeia))

print("--- DataFrame de Sexta-feira ---")
print(asex_df)
print("\n--- DataFrame de Sábado ---")
print(asab_df)

# Inicializa matrizes
asex = [[0] * len(colunas_sexta) for _ in range(n_funcionarios)]
asab = [[0] * len(colunas_sabado) for _ in range(n_funcionarios)]

# Preenche as matrizes
for _, row in df_filtrado.iterrows():
    idx = row['IDX']
    asex[idx] = asex_df.loc[row.name].tolist()
    asab[idx] = asab_df.loc[row.name].tolist()

# Retorna as matrizes
(asex, asab)

# 0 = Segunda, 1 = Terça, ..., 6 = Domingo

MESES_PORTUGUES = {
    1: "JANEIRO", 2: "FEVEREIRO", 3: "MARÇO", 4: "ABRIL", 5: "MAIO", 6: "JUNHO",
    7: "JULHO", 8: "AGOSTO", 9: "SETEMBRO", 10: "OUTUBRO", 11: "NOVEMBRO", 12: "DEZEMBRO"
}

DIAS_FUNCIONARIAS = {
    0: [-1],
    1: [2, 3],
    2: [0, 1],
    3: [1, 2],
    4: [-1],
    5: [0, 1],
    6: [2, 3]
}

# Terça
# 2, 3 e 5
# Quarta
# 1, 3, 6
# Para fácil realocação, consideraremos a Funcionária 3 CORINGA, pois trabalha em ambos os dias mais frequentes
# Ação Coringa: tiramos o outro funcionário do seu dia mais frequente e fazemos o CORINGA tirar o outro dia mais frequente dele
# As duplas 2 e 5; 1 e 6 precisam de atenção especial pois ambas têm a mesma escala de dias da semana então NÃO podem trabalhar na mesma sexta

global MSb_sti, MSb_sau, MSx

# Nome do arquivo (na mesma pasta do script)
file_name = "TabelaRestricao.csv"

# Função para contar o número de sábados, retirando os feriados
# Caso queira o mês todo: dia_inicial = 1 e dia_final = 31
def contar_dias_semanas(ano, mes, dia_inicial, dia_final, feriados, dia):
    print("ANO:", ano, " MES:", mes, " INI:", dia_inicial, " FIM:", dia_final)
    # Obter o calendário do mês específico
    semanas = calendar.monthcalendar(ano, mes)
    print(semanas)

    # Inicializar lista de sábados dentro do intervalo
    lista_dias = []

    # Iterar pelas semanas e verificar o sábado de cada uma
    for semana in semanas:
        dia_atual = semana[dia]  # Obtém o sábado da semana
        print("SÁBADO ATUAL:", dia_atual)

        # Verificar se o sábado está dentro do intervalo e não é feriado
        if dia_atual != 0 and dia_inicial <= dia_atual <= dia_final:
            if (dia_atual, mes) not in [(f[0], f[1]) for f in feriados]:  # Verifica se o sábado não é um feriado
                lista_dias.append(dia_atual)
                print(f"SÁBADO VÁLIDO: {dia_atual}, contagem de sábados: {len(lista_dias)}")

    return lista_dias

def remove_zeros_finais(vetor):
    while vetor and vetor[-1] == 0:  # Verifica se o vetor não está vazio e o último elemento é 0
        vetor.pop()  # Remove o último elemento
    return vetor

def remove_linhas_zeradas(matriz):
    """
    Remove linhas (vetores) da matriz que têm todos os elementos iguais a zero.
    """
    return [linha for linha in matriz if not all(elem == 0 for elem in linha)]

def cria_matriz_indice(vector):
    matrix = []  # Matriz resultante
    count = 0  # Contador para preencher os elementos sequenciais

    for length in vector:
        row = []  # Cria uma nova linha
        for _ in range(length):
            row.append(count)
            count += 1
        matrix.append(row)  # Adiciona a linha à matriz

    return matrix

# Função para alocar e ajustar todas as variáveis do modelo (utilizada para as sextas e sábados)
def aloca_tudo(ano, primeiro_dia, dias_sem_trabalho, dia):
    # alocando variáveis
    quant_dias_mes = [0] * 6
    num_meses = 6  # Número de linhas -> representa o número máximo de meses
    num_dias = 5   # Número de colunas -> representa a quantidade máxima de sábados
    dias_semestre = [[0] * num_dias for _ in range(num_meses)]

    # Calcular a quantidade de sábados por mes e total
    _, ultimo_dia_mes = calendar.monthrange(ano, primeiro_dia[1])
    dias_semestre[0] = contar_dias_semanas(ano, primeiro_dia[1], primeiro_dia[0], ultimo_dia_mes, dias_sem_trabalho, dia)
    quant_dias_mes[0] = len(dias_semestre[0])
    n_dias = quant_dias_mes[0]
    print("dia INICIAL", quant_dias_mes[0])
    print(dias_semestre[0])

    # mes_i é a condição de parada, com o objetivo de parar no penúltimo mês
    # indice é o local do vetor que vamos ocupar
    mes_i = primeiro_dia[1] + 1 # mes_i recebe o primeiro mês mais um para alocar os próximos meses
    indice = 1
    while mes_i < ultimo_dia[1]:
        print("MES", mes_i)
        print("INDICE", indice)
        _, ultimo_dia_mes = calendar.monthrange(ano, mes_i)
        dias_semestre[indice] = contar_dias_semanas(ano, mes_i, 1, ultimo_dia_mes, dias_sem_trabalho, dia)
        quant_dias_mes[indice] = len(dias_semestre[indice])
        n_dias += quant_dias_mes[indice]
        indice += 1
        mes_i += 1

    print("INDICE: ", indice)
    dias_semestre[indice] = contar_dias_semanas(ano, ultimo_dia[1], 1, ultimo_dia[0], dias_sem_trabalho, dia)
    quant_dias_mes[indice] = len(dias_semestre[indice])
    n_dias += quant_dias_mes[indice]

    quant_dias_mes = remove_zeros_finais(quant_dias_mes)
    dias_semestre = remove_linhas_zeradas(dias_semestre)
    matriz_indice = cria_matriz_indice(quant_dias_mes)
    num_meses = len(quant_dias_mes)

    return quant_dias_mes, dias_semestre, n_dias, matriz_indice, num_meses

# Função responsável por retornar a outra funcionária que trabalha com a Sandra
def quem_trabalha_sandra(dias_trabalhados_sextas, pivo, n_funcionarias):
    # Normaliza: garante que cada elemento seja uma lista
    escalas = []
    for i in range(n_funcionarias):
        escala = dias_trabalhados_sextas[i]
        if not isinstance(escala, list):
            escala = [escala]
        escalas.append(sorted(escala))

    # Verifica se a Sandra (índice 3) trabalha na sexta 'pivo'
    if pivo not in escalas[3]:
        return None

    # Procura pela outra funcionária usando busca binária
    for i in range(n_funcionarias):
        if i == 3:
            continue
        dias = escalas[i]
        index = bisect.bisect_left(dias, pivo)
        if index != len(dias) and dias[index] == pivo:
            return i
    return None

def proxima_sexta(dia, mes, dia_semana, ano):
    """
    Retorna a data (dia, mês e ano) da próxima sexta-feira.

    Parâmetros:
      dia: dia atual (int)
      mes: mês atual (int)
      dia_semana: dia da semana do dia atual (int) usando a convenção Python:
                  0 = segunda, 1 = terça, ..., 4 = sexta, 5 = sábado, 6 = domingo
      ano: ano atual (int)

    Retorna:
      Uma tupla (novo_dia, novo_mes, novo_ano) representando a próxima sexta-feira.
    """
    sexta_target = 4  # Em Python, sexta-feira é representada pelo número 4
    diff = (sexta_target - dia_semana) % 7
    # Se diff for 0, significa que hoje é sexta; portanto, a próxima sexta é daqui a 7 dias
    if diff == 0:
        diff = 7

    novo_dia = dia + diff
    # Obtém o último dia do mês atual
    _, ultimo_dia = calendar.monthrange(ano, mes)
    if novo_dia > ultimo_dia:
        # Se ultrapassar o mês, ajusta para o próximo mês
        novo_dia -= ultimo_dia
        mes += 1
        if mes > 12:
            mes = 1
            ano += 1

    return novo_dia, mes

def contar_feriados(feriados, ano):
    """
    Processa uma matriz de feriados e retorna:
    - Matriz de indexação dos dias da semana com feriado (sem semanas só com sábados)
    - Matriz atualizada de feriados válidos
    - Quantidade de semanas válidas
    - Quantidade de feriados válidos
    """
    # Agrupar os feriados por semana ISO
    semanas = defaultdict(list)
    feriados_por_data = defaultdict(list)

    for feriado in feriados:
        dia, mes = feriado[0], feriado[1]
        d = date(ano, mes, dia)
        dia_semana = d.weekday()
        iso_ano, iso_semana, _ = d.isocalendar()
        chave_semana = (iso_ano, iso_semana)

        semanas[chave_semana].append(dia_semana)
        feriados_por_data[chave_semana].append(feriado)

    matriz_indexacao = []
    novos_feriados = []

    for chave in sorted(semanas.keys()):
        dias_semana = semanas[chave]
        if all(d == 5 for d in dias_semana):  # Só sábados
            continue
        matriz_indexacao.append(sorted(dias_semana))
        novos_feriados.extend(feriados_por_data[chave])

    quantidade_semanas = len(matriz_indexacao)
    quantidade_feriados = len(novos_feriados)

    return matriz_indexacao, novos_feriados, quantidade_semanas, quantidade_feriados


def quem_trabalha_sexta(primeiro_mes, ultimo_mes, dia, mes, ano, dias_trabalhados_sextas, sextas_semestre):
    dia_semana = calendar.weekday(ano, mes, dia)  # Segunda=0, ..., Domingo=6
    if dia_semana != 4:
        dia_sexta, mes_sexta = proxima_sexta(dia, mes, dia_semana, ano)
        print(dia_sexta, mes_sexta)
    else:
        dia_sexta = dia
        mes_sexta = mes

    indice = -1
    count = 1
    mes_i = 0
    while mes_i <= ultimo_mes - primeiro_mes and indice == -1:
        for dia_mes in sextas_semestre[mes_i]:
            if dia_mes == dia_sexta and mes_i == mes_sexta - primeiro_mes:
                indice = count
                break
            count += 1
        mes_i += 1

    quem_trabalha = [0] * 2
    count = 0
    for funcionario in range(n_funcionarios):
        if indice in dias_trabalhados_sextas[funcionario]:
            quem_trabalha[count] = funcionario
            count += 1

    return quem_trabalha[0], quem_trabalha[1]

def bool_esta_sexta(sextas_em_feriados, semana, indice):
    if semana in sextas_em_feriados[indice]:
        return 1
    else:
        return 0

def dias_para_feriado(dia, mes, ano, feriados):
    """
    Dada uma data (dia, mes, ano) e uma lista de feriados,
    retorna quantos dias faltam para o próximo feriado que
    ocorra na mesma semana ISO, DESCONSIDERANDO feriados que sejam somente no sábado.
    Se não houver feriado na mesma semana (ou se o único feriado for um sábado),
    retorna -1.

    Parâmetros:
      dia (int): dia da data de referência.
      mes (int): mês da data de referência.
      ano (int): ano da data de referência.
      feriados (list): lista de listas, onde cada sublista representa um feriado
                       e tem o dia na posição 0 e o mês na posição 1.

    Retorna:
      int: o menor número de dias até o feriado (que não seja sábado) na mesma semana,
           considerando somente feriados com data >= data de referência. Se não houver,
           retorna -1.
    """
    # Cria a data de referência
    data_ref = date(ano, mes, dia)
    # Obtém o número da semana ISO da data de referência
    semana_ref = data_ref.isocalendar()[1]

    dias_restantes = []

    for f in feriados:
        f_dia, f_mes = f[0], f[1]
        try:
            data_feriado = date(ano, f_mes, f_dia)
        except ValueError:
            continue  # ignora datas inválidas

        # Se o feriado for no sábado (weekday() == 5), ignora-o
        if data_feriado.weekday() == 5:
            continue

        # Verifica se o feriado está na mesma semana e não ocorreu antes da data_ref
        if data_feriado.isocalendar()[1] == semana_ref and data_feriado >= data_ref:
            diff = (data_feriado - data_ref).days
            dias_restantes.append(diff)

    if dias_restantes:
        return min(dias_restantes)
    else:
        return -1


def printa_escala(dia_inicial, mes_inicial, dia_final, mes_final, n_funcionarios,
                   dias_trabalhados_sabados, dias_trabalhados_sextas, feriados,
                   xt_val, xq_val, ano, arquivo_csv):
    # Variáveis de controle para os meses (serão atualizadas a cada iteração)
    sabados_passados = 0
    sextas_passadas = 0
    feriados_passados = 0

    # Abre o arquivo CSV para escrita (UTF-8 para suportar acentuação)
    with open(arquivo_csv, 'w', encoding='utf-8') as csv_file:

        def dual_print(texto="", end="\n"):
            """Imprime no terminal com formatação original."""
            print(texto, end=end)

        # Para cada mês no intervalo definido:
        for mes in range(mes_inicial, mes_final + 1):
            # Define os limites de dias para o mês corrente
            primeiro_dia = dia_inicial if mes == mes_inicial else 1
            ultimo_dia = dia_final if mes == mes_final else calendar.monthrange(ano, mes)[1]

            # ---------------------------
            # Saída no terminal (formatação original)
            # ---------------------------
            dual_print(MESES_PORTUGUES[mes])
            # Linha dos números dos dias
            dual_print(" " * 10, end="")
            for dia in range(primeiro_dia, ultimo_dia + 1):
                dual_print(f"{dia:3}", end=" ")
            dual_print("")
            # Linha com a inicial dos dias da semana
            dual_print(" " * 10, end="")
            for dia in range(primeiro_dia, ultimo_dia + 1):
                inicial_dia = calendar.day_abbr[calendar.weekday(ano, mes, dia)][0]
                dual_print(f"  {inicial_dia:2}", end="")
            dual_print("")
            dual_print("")

            # ---------------------------
            # Saída no CSV
            # ---------------------------
            # Linha com o nome do mês (ex.: "FEVEREIRO;")
            csv_file.write(f"{MESES_PORTUGUES[mes]};\n")
            # Linha com "DIA_DA_SEMANA" e os números (segunda = 1, terça = 2, …, domingo = 7)
            linha_dias = "DIA_DA_SEMANA;"
            linha_dias_mes = ";"
            for dia in range(primeiro_dia, ultimo_dia + 1):
                # Usa calendar.weekday (segunda=0) e soma 1 para que segunda seja 1
                linha_dias_mes += f" {dia} ;"
                dia_semana_num = calendar.weekday(ano, mes, dia) + 1
                linha_dias += f" {dia_semana_num} ;"
            csv_file.write(linha_dias + "\n")
            csv_file.write(linha_dias_mes + "\n")

            # ---------------------------
            # Processa a escala de cada funcionária
            # ---------------------------
            for funcionario in range(n_funcionarios):
                # Para cada funcionária, reinicia os contadores internos
                semanas_feriados = feriados_passados
                # Recupera o nome (ou "Desconhecido" se não encontrar)
                nome_func = next((k for k, v in FUNCIONARIAS.items() if v == funcionario), 'Desconhecido')

                # No terminal, mantém a formatação com 10 espaços
                dual_print(f"{nome_func:<10}", end="")
                # No CSV, inicia a linha com "Funcionária_X;"
                linha_csv = f"{nome_func};"

                # Reinicia os contadores para sábado e sexta para cada funcionária
                conta_sabados = 1 + sabados_passados
                conta_sextas = 1 + sextas_passadas

                # Para cada dia do mês
                for dia in range(primeiro_dia, ultimo_dia + 1):
                    # Se o dia for feriado (conforme lista feriados com (dia, mes))
                    if any(f[0] == dia and f[1] == mes for f in feriados):
                        # Valor definido como "*"
                        valor = "*"
                        dual_print("  * ", end="")
                    else:
                        dia_semana = calendar.weekday(ano, mes, dia)  # 0=segunda, ..., 6=domingo

                        if dia_semana == 6:  # Domingo – sem expediente
                            valor = "*"
                            dual_print("  * ", end="")

                        elif dia_semana == 5:  # Sábado – somente primeiro turno
                            if conta_sabados in dias_trabalhados_sabados[funcionario]:
                                valor = "D"
                                dual_print("  D ", end="")
                            else:
                                valor = "*"
                                dual_print("  * ", end="")
                            conta_sabados += 1

                        elif dia_semana == 4:  # Sexta-feira
                            if conta_sextas in dias_trabalhados_sextas[funcionario]:
                                valor = "N"
                                dual_print("  N ", end="")
                            else:
                                valor = "D"
                                dual_print("  D ", end="")
                            conta_sextas += 1

                        else:  # Para os demais dias (segunda, terça, quarta ou quinta)
                            if dia_semana in DIAS_FUNCIONARIAS[funcionario]:
                                dias_feriado = dias_para_feriado(dia, mes, ano, feriados)
                                if dias_feriado > 0:
                                    if dia_semana == 1:  # Terça-feira – utiliza vetor xt
                                        valor = "N" if xt_val[funcionario][semanas_feriados] > 0.5 else "D"
                                        dual_print(f"  {valor} ", end="")
                                    elif dia_semana == 2:  # Quarta-feira – utiliza vetor xq
                                        valor = "N" if xq_val[funcionario][semanas_feriados] > 0.5 else "D"
                                        dual_print(f"  {valor} ", end="")
                                    else:  # Segunda ou quinta – comportamento normal
                                        valor = "N"
                                        dual_print("  N ", end="")

                                    if dias_feriado == 1:
                                        semanas_feriados += 1
                                else:
                                    if conta_sextas in dias_trabalhados_sextas[funcionario]:
                                        if funcionario == 3:  # Caso específico da Sandra (Coringa)
                                            funcionario2 = quem_trabalha_sandra(dias_trabalhados_sextas, conta_sextas, n_funcionarios)
                                            if funcionario2 == 2 or funcionario2 == 5:
                                                valor = "D" if dia_semana == 2 else "N"
                                                dual_print(f"  {valor} ", end="")
                                            elif funcionario2 == 1 or funcionario2 == 6:
                                                valor = "D" if dia_semana == 1 else "N"
                                                dual_print(f"  {valor} ", end="")
                                            else:
                                                valor = "?"
                                                dual_print("  AAAAAAAAAAAAAA ", end="")
                                        else:
                                            if dia_semana == 1 or dia_semana == 2:
                                                valor = "D"
                                                dual_print("  D ", end="")
                                            else:
                                                valor = "N"
                                                dual_print("  N ", end="")
                                    else:
                                        valor = "N"
                                        dual_print("  N ", end="")
                            else:
                                valor = "D"
                                dual_print("  D ", end="")

                    # Acrescenta o valor (já sem espaços extras) na linha CSV
                    linha_csv += f" {valor} ;"
                # Finaliza a linha da funcionária
                dual_print("")
                csv_file.write(linha_csv + "\n")
            # Atualiza os contadores para o próximo mês (os valores do último funcionário do mês são considerados)
            feriados_passados = semanas_feriados
            sabados_passados = conta_sabados - 1
            sextas_passadas = conta_sextas - 1
            csv_file.write("\n")
            dual_print("")


def gerar_escala_final_com_nomes_dias():
    """
    Versão final que lê o CSV, traduz os números dos dias da semana para texto (Seg, Ter, etc.)
    e gera uma única imagem vertical com a escala completa.
    """
    caminho_arquivo = "SolucaoSemestre.csv"
    print("--- Iniciando a geração da escala final com nomes dos dias ---")

    # --- NOVO: Dicionário para mapear os números dos dias da semana ---
    dias_semana_map = {
        1: "Seg", 2: "Ter", 3: "Qua", 4: "Qui", 5: "Sex", 6: "Sab", 7: "Dom"
    }

    if not os.path.exists(caminho_arquivo):
        print(f"\nERRO CRÍTICO: Arquivo não encontrado!")
        print(f"Verifique se o arquivo '{caminho_arquivo}' está na mesma pasta.")
        input("Pressione Enter para fechar...")
        return

    # --- 1. Leitura e Processamento do Arquivo CSV (sem alterações) ---
    dfs_por_mes = {}
    try:
        print(f"Lendo e processando o arquivo '{caminho_arquivo}'...")
        with open(caminho_arquivo, 'r', encoding='utf-8') as f:
            bloco_de_linhas_atual = None
            nome_mes_atual = None
            meses = ["JANEIRO", "FEVEREIRO", "MARÇO", "ABRIL", "MAIO", "JUNHO", "JULHO", "AGOSTO", "SETEMBRO", "OUTUBRO", "NOVEMBRO", "DEZEMBRO"]

            for linha in f:
                linha_limpa = linha.strip()
                if not linha_limpa: continue
                partes = linha_limpa.split(';')
                primeira_parte = partes[0].strip().upper()

                if primeira_parte in meses and len(partes) <= 2:
                    if nome_mes_atual and bloco_de_linhas_atual:
                        texto_do_bloco = "\n".join(bloco_de_linhas_atual)
                        df = pd.read_csv(io.StringIO(texto_do_bloco), sep=';', header=[0, 1], skipinitialspace=True)
                        dfs_por_mes[nome_mes_atual] = df
                    nome_mes_atual = primeira_parte
                    bloco_de_linhas_atual = []
                elif nome_mes_atual:
                    bloco_de_linhas_atual.append(linha_limpa)
            
            if nome_mes_atual and bloco_de_linhas_atual:
                texto_do_bloco = "\n".join(bloco_de_linhas_atual)
                df = pd.read_csv(io.StringIO(texto_do_bloco), sep=';', header=[0, 1], skipinitialspace=True)
                dfs_por_mes[nome_mes_atual] = df
    except Exception as e:
        print(f"\nERRO CRÍTICO ao ler o arquivo: {e}")
        traceback.print_exc()
        input("Pressione Enter para fechar...")
        return

    print(f"\nMeses processados em memória: {list(dfs_por_mes.keys())}")

    # --- 2. Geração das Imagens de cada Mês (em memória) ---
    imagens_geradas = []
    print("\n--- Renderizando as tabelas de cada mês ---")
    
    def mapear_cor(valor):
        if pd.isna(valor) or not isinstance(valor, str): return 'white'
        valor = valor.strip()
        if valor == '*': return '#f0f0f0'
        cores = {'D': '#fff7bc', 'N': '#9ecae1'}
        return cores.get(valor, 'white')

    for mes, df in dfs_por_mes.items():
        try:
            df.set_index(df.columns[0], inplace=True)
            df.rename_axis(None, inplace=True)
            df = df.loc[:, ~df.columns.get_level_values(0).str.contains('^Unnamed')]
            df.fillna('', inplace=True)
            if df.empty or len(df.columns) == 0: continue

            # --- LÓGICA ATUALIZADA PARA FORMATAR O CABEÇALHO ---
            cabecalhos_formatados = []
            for col_dia_semana, col_dia_mes in df.columns:
                dia_semana_str = str(col_dia_semana).strip()
                dia_mes_str = str(col_dia_mes).strip()
                
                # Tenta converter o número do dia da semana para texto usando o dicionário
                try:
                    dia_semana_num = int(dia_semana_str)
                    # Usa o nome do dia (ex: "Seg") ou o número original se não estiver no dicionário
                    dia_semana_final = dias_semana_map.get(dia_semana_num, dia_semana_str)
                except ValueError:
                    # Se não for um número (ex: '*'), usa o texto original
                    dia_semana_final = dia_semana_str

                # Une o nome do dia da semana e o dia do mês com uma quebra de linha
                label_final = f"{dia_semana_final}\n{dia_mes_str}"
                cabecalhos_formatados.append(label_final)

            figsize_width = max(10, len(df.columns) * 0.7)
            figsize_height = max(4, len(df.index) * 0.6)
            fig, ax = plt.subplots(figsize=(figsize_width, figsize_height))
            ax.set_title(mes, fontsize=16, weight='bold', pad=20)
            ax.axis('off')
            
            tabela = ax.table(cellText=df.values, rowLabels=df.index, colLabels=cabecalhos_formatados,
                              cellColours=df.map(mapear_cor).values, cellLoc='center', loc='center')
            
            tabela.auto_set_font_size(False)
            tabela.set_fontsize(9)
            tabela.scale(1, 2.5)
            
            for key, cell in tabela.get_celld().items():
                cell.set_edgecolor('gray')
                if key[0] == 0 or key[1] == -1:
                    cell.set_text_props(weight='bold')
                    cell.set_facecolor('#DDDDDD')
                if key[0] == 0:
                    cell.set_height(cell.get_height() * 1.5)

            buffer_memoria = io.BytesIO()
            fig.savefig(buffer_memoria, format='png', dpi=200, bbox_inches='tight', pad_inches=0.4)
            buffer_memoria.seek(0)
            imagem_pillow = Image.open(buffer_memoria)
            imagens_geradas.append(imagem_pillow)
            plt.close(fig)
            print(f"Tabela de '{mes}' renderizada.")

        except Exception as e:
            print(f"!!!!!!!! ERRO ao renderizar a imagem para o mês de {mes}: {e} !!!!!!!!")
            traceback.print_exc()

    # --- 3. Combinação das Imagens em um Arquivo Final (sem alterações) ---
    if not imagens_geradas:
        print("\nNenhuma imagem foi gerada. O processo será encerrado.")
        input("Pressione Enter para fechar...")
        return
        
    print("\n--- Combinando as imagens em um arquivo final ---")
    largura_maxima = max(img.width for img in imagens_geradas)
    altura_total = sum(img.height for img in imagens_geradas)
    imagem_final = Image.new('RGBA', (largura_maxima, altura_total), (255, 255, 255, 255))
    posicao_y_atual = 0
    for img in imagens_geradas:
        posicao_x = (largura_maxima - img.width) // 2
        imagem_final.paste(img, (posicao_x, posicao_y_atual))
        posicao_y_atual += img.height
        img.close()

    nome_arquivo_final = "escala_semestre_final.png"
    imagem_final.save(nome_arquivo_final)
    
    print("\n--- Processo Concluído ---")
    print(f"Sucesso! A escala completa foi salva como '{nome_arquivo_final}'")
    webbrowser.open(os.path.realpath(nome_arquivo_final))
    input("Pressione Enter para fechar a janela do script...")


def building_model():
    model = Model("Distribuição de Sextas e Sábados")

    for i in range(n_funcionarios):
        for d in range(n_sextas):
            X[(i, d)] = model.addVar(vtype="BINARY", name="tp({},{})".format(i,d))

    for i in range(n_funcionarios):
        for d in range(n_sabados):
            Y[(i, d)] = model.addVar(vtype="BINARY", name="tp({},{})".format(i,d))

    for i in range(n_funcionarios):
      alegria[(i)] = model.addVar(vtype="CONTINUOUS", name="tp({})".format(i))

    MinAlegria = model.addVar(vtype="CONTINUOUS")

    #Definindo a funcao objetivo
    model.setObjective(MinAlegria,"maximize")

    # anexar a quantidade de sextas em cada vetor
    for mes_i in quant_sextas_mes:
        MSx.append((2 *mes_i) / n_noturnos)
    # adiciona o total de sextas ao final do vetor
    MSx.append((2 * n_sextas) / n_noturnos)

    # anexar a quantidade de sábados em cada vetor
    for i in quant_sabados_mes:
        MSb_sti.append(i / n_sti)
        MSb_sau.append(i / n_sau)
    # adiciona o total de sábados ao final do vetor
    MSb_sti.append(n_sabados / n_sti)
    MSb_sau.append(n_sabados / n_sau)
    print("STI: ", MSb_sti)  # Exibir a lista com os resultados
    print("SAU: ", MSb_sau)  # Exibir a lista com os resultados
    print("SEXTAS: ", MSx)

    #Ordenando as melhores notas de cada funcionária
    for i in range(n_funcionarios):
        a_sab.append([])
        for d in range(n_sabados):
            a_sab[i].append(asab[i][d])

        a_sab[i].sort(reverse=True)

        a_sex.append([])
        for d in range(n_sextas):
            a_sex[i].append(asex[i][d])

        a_sex[i].sort(reverse=True)

    print("ASAB: ", a_sab)
    print("ASEX: ", a_sex)

    for i in range(n_funcionarios):
        if i == 0:
            model.addCons(alegria[i] == quicksum((4*(1 - Y[i,d]) + asab[i][d] * Y[i,d]) for d in range(n_sabados)) / (4*(n_sabados-math.floor(MSb_sti[-1])) + quicksum(a_sab[i][j] for j in range(math.floor(MSb_sti[-1])))))
        else:
            if i == 4:
                model.addCons(alegria[i] == quicksum((4*(1 - Y[i,d]) + asab[i][d] * Y[i,d]) for d in range(n_sabados)) / (4*(n_sabados-math.floor(MSb_sau[-1])) + quicksum(a_sab[i][j] for j in range(math.floor(MSb_sau[-1])))))
            else:
                if i <= 3:
                    model.addCons(alegria[i] == (quicksum((4*(1 - X[i,d]) + asex[i][d]*X[i,d]) for d in range(n_sextas)) + quicksum((4*(1 - Y[i,d]) + asab[i][d]*Y[i,d]) for d in range(n_sabados))) / (4*(n_sextas-math.floor(MSx[-1])) + quicksum(a_sex[i][j] for j in range(math.floor(MSx[-1]))) + 4*(n_sabados-math.floor(MSb_sti[-1])) + quicksum(a_sab[i][j] for j in range(math.floor(MSb_sti[-1])))))
                else:
                    model.addCons(alegria[i] == (quicksum((4*(1 - X[i,d]) + asex[i][d]*X[i,d]) for d in range(n_sextas)) + quicksum((4*(1 - Y[i,d]) + asab[i][d]*Y[i,d]) for d in range(n_sabados))) / (4*(n_sextas-math.floor(MSx[-1])) + quicksum(a_sex[i][j] for j in range(math.floor(MSx[-1]))) + 4*(n_sabados-math.floor(MSb_sau[-1])) + quicksum(a_sab[i][j] for j in range(math.floor(MSb_sau[-1])))))

        model.addCons(alegria[i] >= MinAlegria)

    print("PASSOU")

    # Restrições

    # Sextas

    # Garante que Juliana e Ana não participem dos rodízios de sexta
    for d in range(n_sextas):
        model.addCons(X[0, d] == 0)
        model.addCons(X[4, d] == 0)

    # Garante que as funcionárias de mesmo turno não trabalhem juntas na sexta
    # Gislene (2) e Irene (5)
    for d in range(n_sextas):
        model.addCons(X[2,d] + X[5,d] <= 1)
    # Bia (1) e Regina (6)
    for d in range(n_sextas):
        model.addCons(X[1,d] + X[6,d] <= 1)

    # Garante dois funcionários por sexta
    for d in range(n_sextas):
            model.addCons(quicksum(X[i,d] for i in range(n_funcionarios)) == 2)

    # Garante que um funcionário não trabalhe três sextas consecutivas
    for i in range(n_funcionarios):
        for d in range(n_sextas - 2):
                model.addCons(X[i,d] + X[i, d + 1] + X[i, d + 2] <= 2)

    #garante número minimo e máximo de sextas trabalhadas por mes para os funcionários noturnos
    for mes in range(num_meses_sextas):  # Itera sobre os  meses
        for i in range(1, n_funcionarios):  # Itera sobre os funcionários noturnos
            # Restrições de mínimo e máximo
            if i != 4:
                model.addCons(math.floor(MSx[mes]) <= quicksum(X[i, matriz_indice_sextas[mes][j]] for j in range(quant_sextas_mes[mes])))
                model.addCons(quicksum(X[i, matriz_indice_sextas[mes][j]] for j in range(quant_sextas_mes[mes])) <= math.ceil(MSx[mes]))
        print("CEIL: ", math.ceil(MSx[mes]))
        print("FLOOR: ", math.floor(MSx[mes]))
        print("Normal: ", MSx[mes])

    print("2 MESES")
    #Encontrando um mínimo e máximo de sextas a cada dois meses para os funcionários do rodízio noturno
    for mes in range(num_meses_sextas - 1): # Evita `mes + 1` fora do limite
        for i in range(1, n_funcionarios):
            if i != 4:
                model.addCons(math.floor((quant_sextas_mes[mes]+quant_sextas_mes[mes+1])/(n_noturnos/2)) <= quicksum(X[i,matriz_indice_sextas[mes][j]] for j in range(quant_sextas_mes[mes])) + quicksum(X[i,matriz_indice_sextas[mes+1][j]] for j in range(quant_sextas_mes[mes+1])))
                model.addCons(quicksum(X[i,matriz_indice_sextas[mes][j]] for j in range(quant_sextas_mes[mes])) + quicksum(X[i,matriz_indice_sextas[mes+1][j]] for j in range(quant_sextas_mes[mes+1])) <= math.ceil((quant_sextas_mes[mes]+quant_sextas_mes[mes+1])/(n_noturnos/2)))
        print("CEIL: ", math.ceil((quant_sextas_mes[mes]+quant_sextas_mes[mes+1])/(n_noturnos/2)))
        print("FLOOR: ", math.floor((quant_sextas_mes[mes]+quant_sextas_mes[mes+1])/(n_noturnos/2)))
        print("Normal: ", (quant_sextas_mes[mes]+quant_sextas_mes[mes+1])/(n_noturnos/2))

    print("TUDO")
    # garante que nenhum funcionário trabalhe mais sextas que a média por funcionário em todo o semestre
    for i in range(1, n_funcionarios):
        if i != 4:
            limite_menor = math.floor(MSx[-1])
            model.addCons(quicksum(X[i, matriz_indice_sextas[mes][j]] for mes in range(num_meses_sextas) for j in range(quant_sextas_mes[mes])) <= math.ceil(MSx[-1]))
            model.addCons(limite_menor <= quicksum(X[i, matriz_indice_sextas[mes][j]] for mes in range(num_meses_sextas) for j in range(quant_sextas_mes[mes])))
    print("CEIL: ", math.ceil(MSx[-1]))
    print("FLOOR: ", limite_menor)
    print("Normal: ", MSx[-1])
    # Sábados

    # Garante que um funcionário não trabalhe três sábados consecutivos
    for i in range(n_funcionarios):
        for d in range(n_sabados - 2):
                model.addCons(Y[i,d] + Y[i, d + 1] + Y[i, d + 2] <= 2)

    # garante que nenhum funcionário trabalhe mais sábados que a média por funcionário em todo o semestre
    for i in range(n_sti):
        limite_menor = math.floor(MSb_sti[-1])
        model.addCons(quicksum(Y[i, matriz_indice_sabados[mes][j]] for mes in range(num_meses_sabados) for j in range(quant_sabados_mes[mes])) <= math.ceil(MSb_sti[-1]))
        model.addCons(limite_menor <= quicksum(Y[i, matriz_indice_sabados[mes][j]] for mes in range(num_meses_sabados) for j in range(quant_sabados_mes[mes])))
    for i in range(n_sti, n_funcionarios):
        limite_menor = math.floor(MSb_sau[-1])
        model.addCons(quicksum(Y[i, matriz_indice_sabados[mes][j]] for mes in range(num_meses_sabados) for j in range(quant_sabados_mes[mes])) <= math.ceil(MSb_sau[-1]))
        model.addCons(limite_menor <= quicksum(Y[i, matriz_indice_sabados[mes][j]] for mes in range(num_meses_sabados) for j in range(quant_sabados_mes[mes])))

    #garante número minimo e máximo sabados trabalhados por mes para o STI
    for mes in range(num_meses_sabados):  # Itera sobre os  meses
        for i in range(n_sti):  # Itera sobre os 4 funcionários do STI
            # Restrições de mínimo e máximo
            model.addCons(math.floor(MSb_sti[mes]) <= quicksum(Y[i, matriz_indice_sabados[mes][j]] for j in range(quant_sabados_mes[mes])))
            model.addCons(quicksum(Y[i, matriz_indice_sabados[mes][j]] for j in range(quant_sabados_mes[mes])) <= math.ceil(MSb_sti[mes]))

    print("AQUIII")
    #garante número minimo e máximo sabados trabalhados por mes para o SAU
    for mes in range(num_meses_sabados):  # Itera sobre os meses
        for i in range(n_sti,n_funcionarios):
            model.addCons(math.floor(MSb_sau[mes]) <= quicksum(Y[i,matriz_indice_sabados[mes][j]] for j in range(quant_sabados_mes[mes])))
            model.addCons(quicksum(Y[i,matriz_indice_sabados[mes][j]] for j in range(quant_sabados_mes[mes])) <= math.ceil(MSb_sau[mes]))

    print("OOOOOOEEEEEEE")
    #Encontrando um mínimo e máximo de sábados a cada dois meses para as funcionárias STI
    for mes in range(num_meses_sabados - 1): # Evita `mes + 1` fora do limite
        for i in range(n_sti):
            model.addCons(math.floor((quant_sabados_mes[mes]+quant_sabados_mes[mes+1])/n_sti) <= quicksum(Y[i,matriz_indice_sabados[mes][j]] for j in range(quant_sabados_mes[mes])) + quicksum(Y[i,matriz_indice_sabados[mes+1][j]] for j in range(quant_sabados_mes[mes+1])))
            model.addCons(quicksum(Y[i,matriz_indice_sabados[mes][j]] for j in range(quant_sabados_mes[mes])) + quicksum(Y[i,matriz_indice_sabados[mes+1][j]] for j in range(quant_sabados_mes[mes+1])) <= math.ceil((quant_sabados_mes[mes]+quant_sabados_mes[mes+1])/n_sti))

    print("SERA")
    #Encontrando um mínimo e máximo de sábados a cada dois meses para as funcionárias SAU
    for mes in range(num_meses_sabados - 1):  # Evita `mes + 1` fora do limite
        for i in range(n_sti, n_funcionarios):  # SAU
            model.addCons(
                math.floor((quant_sabados_mes[mes] + quant_sabados_mes[mes + 1]) / n_sau) <=
                quicksum(Y[i, matriz_indice_sabados[mes][j]] for j in range(len(matriz_indice_sabados[mes]))) +
                quicksum(Y[i, matriz_indice_sabados[mes + 1][j]] for j in range(len(matriz_indice_sabados[mes + 1])))
            )
            model.addCons(
                quicksum(Y[i, matriz_indice_sabados[mes][j]] for j in range(len(matriz_indice_sabados[mes]))) +
                quicksum(Y[i, matriz_indice_sabados[mes + 1][j]] for j in range(len(matriz_indice_sabados[mes + 1]))) <=
                math.ceil((quant_sabados_mes[mes] + quant_sabados_mes[mes + 1]) / n_sau)
            )

    print("AQUI?")

    #Garantindo os dois tipos de funcionário no sábado
    for d in range(n_sabados):
            model.addCons(quicksum(Y[i,d] for i in range(0,n_sti)) == 1)

    for d in range(n_sabados):
            model.addCons(quicksum(Y[i,d] for i in range(n_sti,n_funcionarios)) == 1)

    # Garante que a funcionária não trabalhe sábado, caso ela tenha trabalhado na sexta
    mes_inicial = primeiro_dia[1]
    print(mes_inicial)
    print("OOOOOOOOPAAAAAAAAAAA")
    dia_indice_sexta = -1
    mes_indice_sexta = 0
    dia_indice_sabado = 0
    mes_indice_sabado = 0
    indice_sabado = 0
    # Percorremos os vetores de sextas e sábados procurando os pares de dias consecutivos entre ambos
    for indice_sexta in range(n_sextas):
        dia_indice_sexta += 1
        # Ajusto a sexta para não acessar índice indevido
        print(dia_indice_sexta)
        print(mes_indice_sexta)
        print(len(sextas_semestre[mes_indice_sexta]))
        print(len(sextas_semestre))
        print("--------------------------------------------")
        if dia_indice_sexta >= len(sextas_semestre[mes_indice_sexta]):
            dia_indice_sexta = 0
            mes_indice_sexta += 1
        if mes_indice_sexta >= len(sextas_semestre):
            break
        print(dia_indice_sabado)
        print(mes_indice_sabado)
        print(len(sabados_semestre[mes_indice_sabado]))
        print(len(sabados_semestre))
        print("--------------------------------------------")
        # Ajusto o sábado para não acessar índice indevido
        if dia_indice_sabado >= len(sabados_semestre[mes_indice_sabado]):
            dia_indice_sabado = 0
            mes_indice_sabado += 1
        if mes_indice_sabado >= len(sabados_semestre):
            break

        # Checa se a sexta é o último dia do mês
        _, ultimo_dia_mes = calendar.monthrange(ano, mes_inicial + mes_indice_sexta)
        if sextas_semestre[mes_indice_sexta][dia_indice_sexta] == ultimo_dia_mes:
            # É? Então temos que ver se o sábado do mês seguinte é o dia 1 do próximo mês
            if sabados_semestre[mes_indice_sabado][dia_indice_sabado] == 1:
                # Criamos a restrição
                for f in range(n_funcionarios):
                    model.addCons(X[f, indice_sexta] + Y[f, indice_sabado] <= 1)
                print("ENTROU1")
                print(sextas_semestre[mes_indice_sexta][dia_indice_sexta])
                print(sabados_semestre[mes_indice_sabado][dia_indice_sabado])
                # Atualizamos o sábado
                indice_sabado += 1
                dia_indice_sabado += 1
            else:
                continue
        else:
            # Senão, comparação normal com dia e dia+1
            if sextas_semestre[mes_indice_sexta][dia_indice_sexta]+1 == sabados_semestre[mes_indice_sabado][dia_indice_sabado]:
                # Criamos a restrição
                for f in range(n_funcionarios):
                    model.addCons(X[f, indice_sexta] + Y[f, indice_sabado] <= 1)
                print("ENTROU2")
                print(sextas_semestre[mes_indice_sexta][dia_indice_sexta])
                print(sabados_semestre[mes_indice_sabado][dia_indice_sabado])
                # Atualizamos o sábado
                indice_sabado += 1
                dia_indice_sabado += 1

    return model

def feriados_model():
    model = Model("Distribuição de Feriados")

    for i in range(n_funcionarios):
        for s in range(quant_semanas_feriados):
            XT[(i, s)] = model.addVar(vtype="BINARY", name="XT({},{})".format(i,s))

    for i in range(n_funcionarios):
        for s in range(quant_semanas_feriados):
            XQ[(i, s)] = model.addVar(vtype="BINARY", name="XQ({},{})".format(i,s))

    Zmin = model.addVar(vtype="CONTINUOUS")
    Zmax = model.addVar(vtype="CONTINUOUS")
    Delta = Zmax - Zmin
    #Definindo a funcao objetivo
    model.setObjective(Delta,"minimize")

    # Conta quantas sextas cada funcionário trabalha em semanas com feriados
    sextas_em_feriados = [[] for _ in range(n_funcionarios)]
    feriados_tercas = []
    feriados_quartas = []

    # Inicializa todos os dias disponíveis dos dias fixos (segunda e quinta)
    for semana in range(quant_semanas_feriados):
        print(semana)
        # Verifica se naquela semana tem o índice da segunda (0) na matriz de feriados
        if 0 in feriados_matriz[semana]:
            Vet_Segundas[semana] = 0 # Significa que não tem expediente
        else:   # O dia não é feriado
            Vet_Segundas[semana] = 1

        if 1 in feriados_matriz[semana]:
            for funcionario in range(n_funcionarios):
                model.addCons(XT[funcionario, semana] == 0)
            feriados_tercas.append(semana)

        if 2 in feriados_matriz[semana]:
            for funcionario in range(n_funcionarios):
                model.addCons(XQ[funcionario, semana] == 0)
            feriados_quartas.append(semana)

        # Verifica se naquela semana tem o índice de quinta (3) na matriz de feriados
        if 3 in feriados_matriz[semana]:
            Vet_Quintas[semana] = 0
        else:
            Vet_Quintas[semana] = 1

        if 4 not in feriados_matriz[semana]:
            count_dias = 0
            count_semanas = 0
            for dias in novos_feriados:
                print("Feriado ", dias)
                dia_feriado, mes_feriado = dias[0], dias[1]

                if count_semanas == semana: # Chegamos na semana em que o feriado não é sexta
                    indice1, indice2 = quem_trabalha_sexta(primeiro_dia[1], ultimo_dia[1], dia_feriado, mes_feriado, ano, dias_trabalhados_sextas, sextas_semestre)
                    print("INDICE 1", indice1)
                    print("INDICE 2", indice2)
                    sextas_em_feriados[indice1].append(semana)
                    sextas_em_feriados[indice2].append(semana)
                    break

                if count_dias == len(feriados_matriz[count_semanas]) - 1:
                    count_semanas += 1
                    count_dias = 0
                else:
                    count_dias += 1

    print("SEXTAS", sextas_em_feriados)
    print("TERÇAS FERIADOS: ", feriados_tercas)
    print("QUARTAS FERIADOS: ", feriados_quartas)

    # Irene(5) e Gislene(2) - Segunda e Terça
    model.addCons(
        Zmin <= quicksum(Vet_Segundas[semana] for semana in range(quant_semanas_feriados)) +
                quicksum(XT[2, semana]  for semana in range(quant_semanas_feriados)) +
                len(sextas_em_feriados[2])
                )
    model.addCons(
        Zmin <= quicksum(Vet_Segundas[semana] for semana in range(quant_semanas_feriados)) +
                quicksum(XT[5, semana]  for semana in range(quant_semanas_feriados)) +
                len(sextas_em_feriados[5])
                )
    # Sandra(3) - Terça e Quarta
    model.addCons(
        Zmin <= quicksum(XT[3, semana]  for semana in range(quant_semanas_feriados)) +
                quicksum(XQ[3, semana]  for semana in range(quant_semanas_feriados)) +
                len(sextas_em_feriados[3])
                )
    # Bia(1) e Regina(6) - Quarta e Quinta
    model.addCons(
        Zmin <= quicksum(Vet_Quintas[semana] for semana in range(quant_semanas_feriados)) +
                quicksum(XQ[1, semana]  for semana in range(quant_semanas_feriados)) +
                len(sextas_em_feriados[1])
                )
    model.addCons(
        Zmin <= quicksum(Vet_Quintas[semana] for semana in range(quant_semanas_feriados)) +
                quicksum(XQ[6, semana]  for semana in range(quant_semanas_feriados)) +
                len(sextas_em_feriados[6])
                )

    # Irene(5) e Gislene(2) - Segunda e Terça
    model.addCons(
        Zmax >= quicksum(Vet_Segundas[semana] for semana in range(quant_semanas_feriados)) +
                quicksum(XT[2, semana]  for semana in range(quant_semanas_feriados)) +
                len(sextas_em_feriados[2])
                )
    model.addCons(
        Zmax >= quicksum(Vet_Segundas[semana] for semana in range(quant_semanas_feriados)) +
                quicksum(XT[5, semana]  for semana in range(quant_semanas_feriados)) +
                len(sextas_em_feriados[5])
                )
    # Sandra(3) - Terça e Quarta
    model.addCons(
        Zmax >= quicksum(XT[3, semana]  for semana in range(quant_semanas_feriados)) +
                quicksum(XQ[3, semana]  for semana in range(quant_semanas_feriados)) +
                len(sextas_em_feriados[3])
                )
    # Bia(1) e Regina(6) - Quarta e Quinta
    model.addCons(
        Zmax >= quicksum(Vet_Quintas[semana] for semana in range(quant_semanas_feriados)) +
                quicksum(XQ[1, semana]  for semana in range(quant_semanas_feriados)) +
                len(sextas_em_feriados[1])
                )
    model.addCons(
        Zmax >= quicksum(Vet_Quintas[semana] for semana in range(quant_semanas_feriados)) +
                quicksum(XQ[6, semana]  for semana in range(quant_semanas_feriados)) +
                len(sextas_em_feriados[6])
                )

    # Faz apenas dois funcionários trabalharem por dia
    for semana_atual in range(quant_semanas_feriados):
        if semana_atual not in feriados_tercas:
            model.addCons(XT[2, semana_atual] + XT[3, semana_atual] + XT[5, semana_atual] == 2)
        if semana_atual not in feriados_quartas:
            model.addCons(XQ[1, semana_atual] + XQ[3, semana_atual] + XQ[6, semana_atual] == 2)

    # Faz o funcionário trabalhar apenas dois dias a noite por semana
    for semana in range(quant_semanas_feriados):
        # Irene(5) e Gislene(2) - Segunda e Terça
        model.addCons(Vet_Segundas[semana] + XT[2, semana] + bool_esta_sexta(sextas_em_feriados, semana, 2) <= 2)
        model.addCons(Vet_Segundas[semana] + XT[5, semana] + bool_esta_sexta(sextas_em_feriados, semana, 5) <= 2)
        # Sandra(3) - Terça e Quarta
        model.addCons(XT[3, semana] + XQ[3, semana] + bool_esta_sexta(sextas_em_feriados, semana, 3) <= 2)
        # Bia(1) e Regina(6) - Quarta e Quinta
        model.addCons(XQ[1, semana] + Vet_Quintas[semana] + bool_esta_sexta(sextas_em_feriados, semana, 1) <= 2)
        model.addCons(XQ[6, semana] + Vet_Quintas[semana] + bool_esta_sexta(sextas_em_feriados, semana, 6) <= 2)

    # Faz a Juliana(0) e a Ana(4) não serem convocadas para nenhum dos dias a noite
    # Zera as variáveis de quarta para as que não trabalham quarta e o mesmo para terça
    for semana in range(quant_semanas_feriados):
        # Juliana(0)
        model.addCons(XT[0, semana] == 0)
        model.addCons(XQ[0, semana] == 0)
        # Ana(4)
        model.addCons(XT[4, semana] == 0)
        model.addCons(XQ[4, semana] == 0)
        # Bia(1)
        model.addCons(XT[1, semana] == 0)
        # Gislene(2)
        model.addCons(XQ[2, semana] == 0)
        # Irene(5)
        model.addCons(XQ[5, semana] == 0)
        # Regina(6)
        model.addCons(XT[6, semana] == 0)


    return model

try:
    with open(file_name, 'r', encoding='utf-8') as file:

        # Lê todas as linhas do arquivo
        lines = [line.strip() for line in file if line.strip()]  # Remove linhas vazias
        print(lines[3])

        # Variáveis para armazenar os dados
        primeiro_dia = None
        ultimo_dia = None
        dias_sem_trabalho = []

        # Pega o ano a partir da primeira linha do arquivo de restrição
        # 1. Quebra a string na vírgula e no espaço ', '
        partes = lines[3].split(',') 
        # O resultado será uma lista: ['ano', '2025']

        # 2. Pega o segundo elemento da lista (índice 1)
        ano_texto = partes[1]

        # 3. Converte o texto para um número inteiro
        ano = int(ano_texto)
        print("Ano: ", ano)

        print(calendar.calendar(ano))

        i = 4
        while i < len(lines):
            line = lines[i].replace(',', '')  # Remove visualmente os `,` da linha
            if line.lower() == "primeiro dia":
                i += 1
                # Pula o cabeçalho "dia,mes" se existir
                if i < len(lines) and lines[i].lower() == "dia,mes":
                    i += 1
                if i < len(lines):
                    primeiro_dia = [int(val.strip()) for val in lines[i].split(',') if val.strip()]
                i += 1
            elif line.lower() == "ultimo dia":
                i += 1
                if i < len(lines) and lines[i].lower() == "dia,mes":
                    i += 1
                if i < len(lines):
                    ultimo_dia = [int(val.strip()) for val in lines[i].split(',') if val.strip()]
                i += 1
            elif line.lower() == "dias sem trabalho":
                i += 1
                if i < len(lines) and lines[i].lower() == "dia,mes":
                    i += 1
                while i < len(lines):
                    if lines[i].lower() in ["primeiro dia", "ultimo dia", "dias sem trabalho"]:
                        break
                    if lines[i].lower() == "dia,mes":
                        i += 1
                        continue
                    dia = [int(val.strip()) for val in lines[i].split(',') if val.strip()]
                    if dia:
                        dias_sem_trabalho.append(dia)
                    i += 1
            else:
                i += 1


        # Exibe os resultados
        print("Primeiro dia:", primeiro_dia)
        print("Ultimo dia:", ultimo_dia)
        print("Dias sem trabalho:")
        for dia in dias_sem_trabalho:
            print(dia)

        # Recebe todos os parâmetros necessários para a modelagem das SEXTAS (4)
        quant_sextas_mes, sextas_semestre, n_sextas, matriz_indice_sextas, num_meses_sextas = aloca_tudo(ano, primeiro_dia, dias_sem_trabalho, 4)

        print("MATRIZ", matriz_indice_sextas)
        print("MESES", num_meses_sextas)
        print("TOTAL SEXTAS", n_sextas)
        print(quant_sextas_mes)
        print(sextas_semestre)

        # Recebe todos os parâmetros necessários para a modelagem dos SÁBADOS (5)
        quant_sabados_mes, sabados_semestre, n_sabados, matriz_indice_sabados, num_meses_sabados = aloca_tudo(ano, primeiro_dia, dias_sem_trabalho, 5)

        print("MATRIZ", matriz_indice_sabados)
        print("MESES", num_meses_sabados)
        print("TOTAL SABADOS", n_sabados)
        print(quant_sabados_mes)
        print(sabados_semestre)

        feriados_matriz, novos_feriados, quant_semanas_feriados, dias_feriados = contar_feriados(dias_sem_trabalho, ano)
        print("Feriados:")
        print(novos_feriados)
        print(f"Semanas com feriados: {quant_semanas_feriados}, Total de dias de feriado: {dias_feriados}")
        print(feriados_matriz)

        # Número de funcionários
        # TODO ver se faz sentido a definição de numero de funcionario como len(asab)
        # Talvez seja interessante perguntar o num de STI e num de SAU
        # n_funcionarios = len(asab)
        n_sti = 4
        n_sau = 3
        n_noturnos = n_funcionarios - 2 # Quantidade de funcionários da escala noturna

        # Variáveis de decisão:
        #   X[i][d] -> 1 se o funcionário i trabalha na SEXTA d
        #   Y[i][d] -> 1 se o funcionário i trabalha no SÁBADO d
        X, Y, alegria = {}, {}, {}
        MSb_sti = []
        MSb_sau = []
        MSx = []
        a_sab = [[] for _ in range(n_funcionarios)]
        a_sex = [[] for _ in range(n_funcionarios)]

        # Resolver modelo
        model = building_model()
        model.optimize()

       # Criar dicionários para armazenar os dias trabalhados de cada funcionário
        dias_trabalhados_sextas = {i: [] for i in range(n_funcionarios)}
        dias_trabalhados_sabados = {i: [] for i in range(n_funcionarios)}
        xt_val = [[0] * quant_semanas_feriados for _ in range(n_funcionarios)]
        xq_val = [[0] * quant_semanas_feriados for _ in range(n_funcionarios)]


        # Exibir solução
        if model.getStatus() == "optimal":
            print("Solução Ótima Encontrada!")

            ''' Adicionado pelo Douglas '''
            print("\nAlegrias:")
            for i in range(n_funcionarios):
                print("Funcionária " + format(i) + " = " + format(model.getVal(alegria[i])))
            print()
            ''' Adicionado pelo Douglas '''

            # Armazena os dias trabalhados nas sextas
            for i in range(n_funcionarios):
                dias_trabalhados_sextas[i] = [d + 1 for d in range(n_sextas) if model.getVal(X[(i, d)]) > 0.5]
                print(f"{next((k for k, v in FUNCIONARIAS.items() if v == i), 'Desconhecido'):<{10}} trabalha nas sextas: {dias_trabalhados_sextas[i]}")

            print(sextas_semestre)
            print()

            # Armazena os dias trabalhados nos sábados
            for i in range(n_funcionarios):
                dias_trabalhados_sabados[i] = [d + 1 for d in range(n_sabados) if model.getVal(Y[(i, d)]) > 0.5]
                print(f"{next((k for k, v in FUNCIONARIAS.items() if v == i), 'Desconhecido'):<{10}} trabalha nos sábados: {dias_trabalhados_sabados[i]}")

            print(sabados_semestre)
            sol = model.getObjVal()
            print("Valor ótimo encontrado:", sol)

            #   Zmin -> Quantidade de dias trabalhados pelo funcionário mais "folgado"
            #   Zmin -> Quantidade de dias trabalhados pelo funcionário menos "folgado"
            Zmin, Zmin = {}, {}
            #   XT[i][s] -> 1 se o funcionário i trabalha na terça da semana s
            #   XQ[i][s] -> 1 se o funcionário i trabalha na quarta da semana s
            XT, XQ = {}, {}
            Vet_Segundas = [0] * quant_semanas_feriados
            Vet_Quintas = [0] * quant_semanas_feriados

            # Resolver modelo
            model_feriados = feriados_model()
            model_feriados.optimize()

            # Verifica se a solução é ótima
            if model_feriados.getStatus() == "optimal":
                print("Solução ótima encontrada!")

                # Imprime os valores das variáveis binárias XT e XQ para cada funcionário e semana
                for i in range(n_funcionarios):
                    for s in range(quant_semanas_feriados):
                        xt_val[i][s] = model_feriados.getVal(XT[(i, s)])
                        xq_val[i][s] = model_feriados.getVal(XQ[(i, s)])
                        print(f"XT({i},{s}) = {xt_val[i][s]} \t XQ({i},{s}) = {xq_val[i][s]}")

                # Se quiser imprimir os vetores Python já calculados (por exemplo, Vet_Segundas, Vet_Quintas ou sextas_em_feriados):
                print("Vet_Segundas =", Vet_Segundas)
                print("Vet_Quintas =", Vet_Quintas)
                sol = model_feriados.getObjVal()
                print("Delta:", sol)
            else:
                print("Solução não ótima.")

            file_name = "SolucaoSemestre.csv"
            printa_escala(primeiro_dia[0], primeiro_dia[1], ultimo_dia[0], ultimo_dia[1], n_funcionarios, dias_trabalhados_sabados, dias_trabalhados_sextas, dias_sem_trabalho, xt_val, xq_val, ano, file_name)

            gerar_escala_final_com_nomes_dias()

        elif model.getStatus() not in ["optimal", "infeasible"]:
            print("Modelo não resolveu adequadamente.")
            exit()
        else:
            print("Não foi possível encontrar uma solução ótima.")
        print("Status:", model.getStatus())
except Exception as e:
    print(f"Erro ao processar o arquivo: {e}")