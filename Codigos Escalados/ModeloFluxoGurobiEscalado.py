import math
import re
from datetime import date, timedelta
from pathlib import Path

import gurobipy as gp
import pandas as pd
from gurobipy import GRB

ROOT = Path(__file__).resolve().parent
PASTA_RESTRICOES = ROOT / "RestricoesSemestre"
PASTA_RESPOSTAS = ROOT / "Respostasfuncionarios"

NUM_FUNCIONARIOS = (6, 18, 30, 42, 54)

def ler_restricoes(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        linhas = [l.strip() for l in f if l.strip()]

    ano = 2024
    primeiro_dia = ultimo_dia = None
    feriados = set()
    estado = None

    for linha in linhas:
        partes = [p.strip() for p in linha.split(",")]
        chave = partes[0].lower()

        if chave == "ano":
            ano = int(partes[1])
            continue

        if chave in {"primeiro dia", "ultimo dia", "dias sem trabalho"}:
            estado = chave
            continue

        if chave == "dia" and len(partes) > 1 and partes[1].lower() == "mes":
            continue

        if (
            estado
            and len(partes) >= 2
            and partes[0].isdigit()
            and partes[1].isdigit()
        ):
            dm = (int(partes[0]), int(partes[1]))
            if estado == "primeiro dia":
                primeiro_dia = dm
            elif estado == "ultimo dia":
                ultimo_dia = dm
            else:
                feriados.add(dm)

    if primeiro_dia is None or ultimo_dia is None:
        raise ValueError(f"Período incompleto em {filepath}")

    return ano, primeiro_dia, ultimo_dia, feriados

def construir_calendario(ano, primeiro_dia, ultimo_dia, feriados):
    inicio = date(ano, primeiro_dia[1], primeiro_dia[0])
    fim = date(ano, ultimo_dia[1], ultimo_dia[0])

    calendario = []
    atual = inicio
    semana = 0

    while atual <= fim:
        wd = atual.weekday()
        calendario.append({
            "data": atual,
            "dia": atual.day,
            "mes": atual.month,
            "wd": wd,
            "holiday": (atual.day, atual.month) in feriados,
            "week": semana,
        })
        if wd == 6:
            semana += 1
        atual += timedelta(days=1)

    return calendario, semana + 1

def mapear_preferencia(valor):
    if pd.isna(valor):
        return 0

    s = str(valor).strip().lower()
    if s == "gostaria":
        return 7
    if s == "indiferente":
        return 5
    return 0

def descobrir_coluna_nome(df):
    for col in df.columns:
        if str(col).strip().lower() == "nome":
            return col
    if len(df.columns) >= 3:
        return df.columns[2]
    raise ValueError("A tabela não possui uma coluna de nome identificável.")

def carregar_funcionarios(df, n):
    nome_col = descobrir_coluna_nome(df)
    funcionarios = []
    prefs = {}
    sti_names = set()
    sau_names = set()
    count_a = count_b = 0
    limite_departamento = n // 4

    for _, row in df.iterrows():
        if len(funcionarios) >= n:
            break

        nome = str(row[nome_col]).strip()
        if not nome or nome.lower() == "nan":
            continue

        idx = len(funcionarios)

        if idx % 2 == 0:
            if len(sti_names) < limite_departamento:
                grupo = "A"
                count_a += 1
            else:
                grupo = "B"
                count_b += 1
            sti_names.add(nome)
        else:
            if len(sau_names) < limite_departamento:
                grupo = "B"
                count_b += 1
            else:
                grupo = "A"
                count_a += 1
            sau_names.add(nome)

        funcionarios.append({"name": nome, "group": grupo})

        sexta = []
        sabado = []
        for col in df.columns:
            c = str(col).strip().lower()
            if "sexta" in c:
                sexta.append(mapear_preferencia(row[col]))
            elif "sábado" in c or "sabado" in c or "sábados" in c or "sabados" in c:
                sabado.append(mapear_preferencia(row[col]))
        prefs[nome] = {"friday": sexta, "saturday": sabado}

    if len(funcionarios) != n:
        raise ValueError(f"A tabela possui menos de {n} funcionários válidos.")

    return funcionarios, prefs, sti_names, sau_names, count_a, count_b

def indexar_arcos(vertices, arcos):
    entrada = {v: [] for v in vertices}
    saida = {v: [] for v in vertices}
    trabalho = {}

    for arco in arcos:
        u, v, dia, shift = arco
        saida[u].append(arco)
        entrada[v].append(arco)
        if shift == 1:
            trabalho.setdefault(dia, []).append(arco)

    return entrada, saida, trabalho

def construir_rede_series(calendario, dias_base):
    source, sink = "SOURCE_S", "SINK_S"
    vertices = {source, sink}
    arcos = []

    estado0 = (False, False, 0, False)
    primeiro = f"d0_{estado0}"
    vertices.add(primeiro)
    arcos.append((source, primeiro, -1, None))

    estados = {estado0}

    for d_idx, dia in enumerate(calendario):
        novos = set()

        for estado in estados:
            sexta_ant, sabado_ant, qtd_base, weekend_worked = estado
            no = f"d{d_idx}_{estado}"
            vertices.add(no)

            wd = dia["wd"]
            feriado = bool(dia["holiday"])
            domingo = wd == 6
            base = wd in dias_base and not feriado
            sexta = wd == 4 and not feriado
            sabado = wd == 5 and not feriado

            transicoes = []

            if domingo:
                transicoes.append(((sexta_ant, sabado_ant, 0, False), 0))

            elif feriado:
                transicoes.append(((sexta_ant, sabado_ant, qtd_base, weekend_worked), 0))

            elif base:
                transicoes.append(((sexta_ant, sabado_ant, qtd_base, weekend_worked), 0))

                if qtd_base < 2:
                    transicoes.append(((sexta_ant, sabado_ant, qtd_base + 1, weekend_worked), 1))

            elif sexta:
                transicoes.append(((False, sabado_ant, qtd_base, False), 0))

                if not sexta_ant and not weekend_worked and qtd_base < 2:
                    transicoes.append(((True, sabado_ant, qtd_base, True), 1))

            elif sabado:
                transicoes.append(((sexta_ant, False, qtd_base, weekend_worked), 0))

                if not sabado_ant and not weekend_worked:
                    transicoes.append(((sexta_ant, True, qtd_base, True), 1))

            else:
                transicoes.append(((sexta_ant, sabado_ant, qtd_base, weekend_worked), 0))

            for proximo, shift in transicoes:
                prox_no = f"d{d_idx + 1}_{proximo}"
                vertices.add(prox_no)
                arcos.append((no, prox_no, d_idx, shift))
                novos.add(proximo)

        estados = novos

    for estado in estados:
        arcos.append((f"d{len(calendario)}_{estado}", sink, len(calendario), None))

    return vertices, arcos, source, sink

def construir_rede_contratos(num_dias):
    source, sink = "SOURCE_C", "SINK_C"
    vertices = {source, sink}
    arcos = []

    for d in range(num_dias):
        vertices.update({f"c_d{d}", f"c_d{d + 1}"})
        arcos.append((f"c_d{d}", f"c_d{d + 1}", d, 0))
        arcos.append((f"c_d{d}", f"c_d{d + 1}", d, 1))

    arcos.append((source, "c_d0", -1, None))
    arcos.append((f"c_d{num_dias}", sink, num_dias, None))
    return vertices, arcos, source, sink

def resolver_instancia(semestre, ano, tabela, n_funcionarios, restricao_path, resposta_path):
    ano_arq, primeiro, ultimo, feriados = ler_restricoes(restricao_path)
    df = pd.read_csv(resposta_path)

    calendario, W = construir_calendario(ano_arq, primeiro, ultimo, feriados)
    funcionarios, prefs, sti_names, sau_names, count_a, count_b = carregar_funcionarios(
        df, n_funcionarios
    )
    N = len(funcionarios)
    fator = N / 6.0
    num_dias = len(calendario)

    eligible_sti = [i for i, e in enumerate(funcionarios) if e["name"] in sti_names]
    eligible_sau = [i for i, e in enumerate(funcionarios) if e["name"] in sau_names]

    day_exists = [[False] * 6 for _ in range(W)]
    day_holiday = [[False] * 6 for _ in range(W)]
    day_index = [[None] * 6 for _ in range(W)]
    day_month = [[None] * 6 for _ in range(W)]

    for idx, d in enumerate(calendario):
        w, wd = d["week"], d["wd"]
        if wd < 6:
            day_exists[w][wd] = True
            day_holiday[w][wd] = d["holiday"]
            day_index[w][wd] = idx
            day_month[w][wd] = d["mes"]

    months = sorted({d["mes"] for d in calendario})
    fridays_month = {m: [] for m in months}
    saturdays_month = {m: [] for m in months}
    all_fridays = []
    all_saturdays = []

    for w in range(W):
        if day_exists[w][4] and not day_holiday[w][4]:
            fridays_month[day_month[w][4]].append(w)
            all_fridays.append(w)
        if day_exists[w][5] and not day_holiday[w][5]:
            saturdays_month[day_month[w][5]].append(w)
            all_saturdays.append(w)

    # Mantemos somente a rede de séries. A rede de contratos era redundante:
    # qualquer sequência binária já pode percorrer o grafo de contratos.
    VA, AA, SA, TA = construir_rede_series(calendario, [0, 1])
    VB, AB, SB, TB = construir_rede_series(calendario, [2, 3])
    IA, OA, WA = indexar_arcos(VA, AA)
    IB, OB, WB = indexar_arcos(VB, AB)

    model = gp.Model(f"Fluxo_{semestre}_{ano}_tabela_{tabela}_{N}")
    model.Params.OutputFlag = 0
    model.Params.TimeLimit = 3600
    model.Params.Presolve = 2
    model.Params.Symmetry = 2

    f = []
    work_expr = []

    for i, e in enumerate(funcionarios):
        if e["group"] == "A":
            entrada_s, saida_s, trabalho_s = IA, OA, WA
            source_s, sink_s = SA, TA
            arcos_rede = AA
        else:
            entrada_s, saida_s, trabalho_s = IB, OB, WB
            source_s, sink_s = SB, TB
            arcos_rede = AB

        vars_i = {a: model.addVar(vtype=GRB.BINARY) for a in arcos_rede}
        f.append(vars_i)
        work_expr_i = [gp.quicksum(vars_i[a] for a in trabalho_s.get(d, [])) for d in range(num_dias)]
        work_expr.append(work_expr_i)

        model.addConstr(gp.quicksum(vars_i[a] for a in saida_s[source_s]) == 1)
        model.addConstr(gp.quicksum(vars_i[a] for a in entrada_s[sink_s]) == 1)

        for v in saida_s:
            if v not in {source_s, sink_s}:
                model.addConstr(
                    gp.quicksum(vars_i[a] for a in entrada_s[v]) ==
                    gp.quicksum(vars_i[a] for a in saida_s[v])
                )

    def trabalha(i, d):
        return work_expr[i][d]

    # Cobertura.
    for w in range(W):
        for wd in range(4):
            if not day_exists[w][wd]:
                continue
            d = day_index[w][wd]
            if day_holiday[w][wd]:
                model.addConstr(gp.quicksum(trabalha(i, d) for i in range(N)) == 0)
            else:
                model.addConstr(
                    gp.quicksum(trabalha(i, d) for i in range(N)) == 2 * fator
                )

        if day_exists[w][4]:
            d = day_index[w][4]
            if day_holiday[w][4]:
                model.addConstr(gp.quicksum(trabalha(i, d) for i in range(N)) == 0)
            else:
                model.addConstr(
                    gp.quicksum(
                        trabalha(i, d) for i in range(N)
                        if funcionarios[i]["group"] == "A"
                    ) == fator
                )
                model.addConstr(
                    gp.quicksum(
                        trabalha(i, d) for i in range(N)
                        if funcionarios[i]["group"] == "B"
                    ) == fator
                )

        if day_exists[w][5]:
            d = day_index[w][5]
            if day_holiday[w][5]:
                model.addConstr(gp.quicksum(trabalha(i, d) for i in range(N)) == 0)
            else:
                model.addConstr(gp.quicksum(trabalha(i, d) for i in eligible_sti) == fator)
                model.addConstr(gp.quicksum(trabalha(i, d) for i in eligible_sau) == fator)

    def add_balance(ids, periods, wd):
        for weeks in periods:
            if not weeks or not ids:
                continue
            target = len(weeks) * fator / len(ids)
            low, high = math.floor(target), math.ceil(target)
            for i in ids:
                model.addConstr(
                    gp.quicksum(trabalha(i, day_index[w][wd]) for w in weeks) >= low
                )
                model.addConstr(
                    gp.quicksum(trabalha(i, day_index[w][wd]) for w in weeks) <= high
                )

    group_a = [i for i, e in enumerate(funcionarios) if e["group"] == "A"]
    group_b = [i for i, e in enumerate(funcionarios) if e["group"] == "B"]

    periods_fri = [fridays_month[m] for m in months]
    periods_fri += [
        fridays_month[months[k]] + fridays_month[months[k + 1]]
        for k in range(len(months) - 1)
    ]
    periods_fri.append(all_fridays)

    periods_sat = [saturdays_month[m] for m in months]
    periods_sat += [
        saturdays_month[months[k]] + saturdays_month[months[k + 1]]
        for k in range(len(months) - 1)
    ]
    periods_sat.append(all_saturdays)

    add_balance(group_a, periods_fri, 4)
    add_balance(group_b, periods_fri, 4)
    add_balance(eligible_sti, periods_sat, 5)
    add_balance(eligible_sau, periods_sat, 5)

    msx = math.floor(len(all_fridays) * fator / count_a) if all_fridays and count_a else 0
    msb_sti = (
        math.floor(len(all_saturdays) * fator / len(eligible_sti))
        if all_saturdays and eligible_sti else 0
    )
    msb_sau = (
        math.floor(len(all_saturdays) * fator / len(eligible_sau))
        if all_saturdays and eligible_sau else 0
    )

    alegria = model.addVars(N, lb=0.0, ub=1.0, vtype=GRB.CONTINUOUS, name="alegria")
    z = model.addVar(lb=0.0, ub=1.0, vtype=GRB.CONTINUOUS, name="z")

    for i, e in enumerate(funcionarios):
        pr = prefs[e["name"]]
        numerador = gp.LinExpr()
        denominador = 0.0

        pref_fri = pr["friday"]
        for pos, w in enumerate(all_fridays):
            if pos < len(pref_fri):
                numerador += 10.0 + (pref_fri[pos] - 10.0) * trabalha(i, day_index[w][4])
        for k, pref in enumerate(sorted(pref_fri, reverse=True)[:len(all_fridays)]):
            denominador += pref if k < msx else 10.0

        pref_sat = pr["saturday"]
        for pos, w in enumerate(all_saturdays):
            if pos < len(pref_sat):
                numerador += 10.0 + (pref_sat[pos] - 10.0) * trabalha(i, day_index[w][5])

        t_sat = msb_sti if e["name"] in sti_names else msb_sau
        for k, pref in enumerate(sorted(pref_sat, reverse=True)[:len(all_saturdays)]):
            denominador += pref if k < t_sat else 10.0

        if denominador > 0:
            model.addConstr(alegria[i] * denominador == numerador)
        else:
            model.addConstr(alegria[i] == 1.0)
        model.addConstr(alegria[i] >= z)

    model.setObjective(
        10.0 * z + gp.quicksum(alegria[i] for i in range(N)),
        GRB.MAXIMIZE,
    )
    model.optimize()

    if model.SolCount == 0:
        print(f"[SEM SOLUÇÃO] {semestre}-{ano} tabela {tabela}, N={N}")
        return None

    output = ROOT / f"resultado_{semestre}-{ano}_{N}func_{tabela}.txt"
    with open(output, "w", encoding="utf-8") as out:
        out.write(f"Semestre: {semestre}-{ano}\n")
        out.write(f"Funcionários: {N}\n")
        out.write(f"ObjVal: {model.ObjVal}\n")
        out.write(f"ObjBound: {model.ObjBound}\n")
        out.write(f"MIPGap: {model.MIPGap}\n")
        out.write(f"Runtime: {model.Runtime}\n")
        out.write("\n=== Felicidade (Alegria) por Funcionária ===\n")
        for i in range(N):
            out.write(f"FUNCIONÁRIA {i + 1}: {alegria[i].X}\n")
        out.write("============================================\n")

    print(
        f"[OK] {semestre}-{ano} | tabela {tabela} | N={N} | "
        f"ObjVal={model.ObjVal:.6f} | z={z.X:.6f} | "
        f"tempo={model.Runtime:.3f}s"
    )
    return output

def descobrir_instancias():
    if not PASTA_RESTRICOES.is_dir():
        raise FileNotFoundError(f"Pasta não encontrada: {PASTA_RESTRICOES}")
    if not PASTA_RESPOSTAS.is_dir():
        raise FileNotFoundError(f"Pasta não encontrada: {PASTA_RESPOSTAS}")

    restricoes = {}
    for path in PASTA_RESTRICOES.glob("*.csv"):
        m = re.fullmatch(r"(\d+)-(\d+)\.csv", path.name)
        if m:
            semestre, ano = int(m.group(1)), int(m.group(2))
            restricoes[(semestre, ano)] = path

    instancias = []
    for (semestre, ano), restricao in sorted(restricoes.items()):
        prefixo = f"{semestre}-{ano}-"
        respostas = []
        for path in PASTA_RESPOSTAS.glob(f"{prefixo}*.csv"):
            m = re.fullmatch(rf"{semestre}-{ano}-(.+)\.csv", path.name)
            if m:
                respostas.append((m.group(1), path))

        def chave_tabela(item):
            s = item[0]
            return (0, int(s)) if s.isdigit() else (1, s)

        for tabela, resposta in sorted(respostas, key=chave_tabela):
            instancias.append((semestre, ano, tabela, restricao, resposta))

    return instancias

def main():
    instancias = descobrir_instancias()
    if not instancias:
        raise FileNotFoundError(
            "Nenhuma instância encontrada. Esperado: "
            "RestricoesSemestre/S-A.csv e "
            "Respostasfuncionarios/S-A-TABELA.csv"
        )

    total = 0
    for semestre, ano, tabela, restricao, resposta in instancias:
        df = pd.read_csv(resposta)
        try:
            nome_col = descobrir_coluna_nome(df)
            disponiveis = sum(
                1 for v in df[nome_col]
                if str(v).strip() and str(v).strip().lower() != "nan"
            )
        except Exception as exc:
            print(f"[ERRO] {resposta.name}: {exc}")
            continue

        numeros = [n for n in NUM_FUNCIONARIOS if n <= disponiveis]
        for n in numeros:
            try:
                resolver_instancia(
                    semestre, ano, tabela, n, restricao, resposta
                )
                total += 1
            except Exception as exc:
                print(
                    f"[ERRO] {semestre}-{ano} | tabela {tabela} | "
                    f"N={n}: {exc}"
                )

    print(f"\nInstâncias processadas: {total}")

if __name__ == "__main__":
    main()
