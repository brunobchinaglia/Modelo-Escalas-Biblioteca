# Escala de Horários da Biblioteca ICMC/USP

Este projeto, desenvolvido com o apoio da **FAPESP** (Fundação de Amparo à Pesquisa do Estado de São Paulo) no âmbito de Iniciação Científica, oferece uma solução computacional robusta para a otimização da escala de horários dos funcionários da Biblioteca do Instituto de Ciências Matemáticas e de Computação (ICMC) da USP. O objetivo é gerar uma escala de trabalho justa e eficiente, que respeite as regras de funcionamento da biblioteca, as leis trabalhistas e as preferências individuais dos funcionários.

O projeto evoluiu para incorporar duas abordagens de modelagem matemática: um modelo clássico de restrições e um modelo avançado baseado na **Geração de Padrões**. O resultado é uma escala semestral detalhada, apresentada em formato de calendário, que busca maximizar a satisfação e o bem-estar da equipe.

## Sobre o Projeto

A gestão da escala de horários em setores de atendimento ao público, como bibliotecas, é um desafio que envolve múltiplas variáveis. A solução proposta utiliza a Pesquisa Operacional para criar uma escala que equilibra a carga de trabalho, especialmente nos rodízios de sextas-feiras à noite e sábados de manhã, distribuindo de forma equitativa as folgas decorrentes de feriados. 

O sistema original foi validado pela equipe da biblioteca alcançando um índice de satisfação entre 97% e 100%. Com a adoção da nova formulação por padrões, o algoritmo ganha maior flexibilidade e eficiência computacional na exploração de escalas válidas.

## Funcionalidades

* **Múltiplas Abordagens de Otimização:** Implementação em duas frentes independentes para fins de estudo e eficiência (Modelo Clássico de Restrições e Modelo de Padrões).
* **Coleta de Preferências Automatizada:** Importação das preferências dos funcionários diretamente de formulários para simplificar a entrada de dados.
* **Equilíbrio de Carga:** Distribuição justa de turnos críticos (sextas e sábados) e folgas em semanas com feriados.
* **Geração de Padrões (Nova Funcionalidade):** Algoritmo em C++ que pré-computa rotinas de trabalho viáveis (padrões) para cada funcionário, delegando ao *solver* a tarefa de selecionar a melhor combinação global.
* **Visualização Clara:** Geração de imagens (`.png`) com a escala completa do semestre e exportação de dados analíticos.

## Metodologia

O problema de escalonamento é resolvido através de abordagens matemáticas distintas contidas neste repositório.

### Abordagem 1: Modelo de Restrições em Duas Etapas (Python)
A abordagem inicial divide o problema sequencialmente:
1. **Rodízio de Fim de Semana:** Foca nos turnos de sexta à noite e sábado de manhã, maximizando a felicidade do funcionário menos satisfeito. Evita que o mesmo funcionário trabalhe em três finais de semana consecutivos ou na sequência sexta/sábado.
2. **Dias da Semana e Feriados:** Ajusta os turnos noturnos de segunda a quinta-feira, minimizando a discrepância de carga horária entre os funcionários em semanas que contêm feriados.

### Abordagem 2: Modelo por Geração de Padrões (C++ e Gurobi)
Esta nova formulação altera o paradigma de resolução. Em vez de decidir turno a turno, o modelo:
1. **Gera Padrões Válidos:** Cria todas as combinações de escalas mensais/semestrais possíveis (padrões) para um funcionário que já respeitem individualmente as regras trabalhistas e de saúde (ex: limite de turnos noturnos, folgas mínimas).
2. **Seleção Ótima:** Utiliza o *solver* Gurobi para selecionar exatamente um padrão de trabalho para cada funcionário, de modo que a combinação desses padrões atenda à demanda de cobertura da biblioteca (ex: mínimo de funcionários por turno, restrições de senioridade) e maximize a satisfação global.

## Primeiros Passos

O repositório está estruturado de acordo com a abordagem escolhida. Siga as instruções abaixo para configurar o ambiente.

### Pré-requisitos

**Para o Modelo de Restrições (Python):**
* Python 3.x
* Bibliotecas: `gspread`, `gspread-dataframe`, `pyscipopt`, `pandas`, `numpy`, `matplotlib`, `Pillow`.
* Acesso à API do Google Sheets com arquivo de credenciais (`.json`).

**Para o Modelo de Padrões (C++):**
* Compilador C++ (ex: `g++` ou `clang++`).
* **Gurobi Optimizer:** É obrigatório possuir o Gurobi instalado no sistema.
* **Licença Gurobi:** Para executar o modelo, você precisa de uma licença válida do Gurobi (Licenças acadêmicas gratuitas estão disponíveis para estudantes e pesquisadores através do site oficial).

### Configuração e Execução

**1. Preparação dos Dados (Ambos os modelos):**
* Configure a **Planilha de Preferências (Google Forms)** com as respostas "Gostaria", "Indiferente" e "Não Gostaria".
* Configure a planilha **"Restrições Semestre"** com as informações de período letivo, feriados e dias de disponibilidade.

**2. Executando o Modelo Python:**
* Insira seu arquivo de credencial Google renomeado para `direct-plasma-459913-t4-d69064b9f4bc.json` na raiz.
* Execute o script principal. A saída incluirá arquivos `.csv` e a imagem `escala_semestre_final.png`.

**3. Executando o Modelo C++ (Gurobi):**
* Certifique-se de que as variáveis de ambiente do Gurobi (`GUROBI_HOME`, `PATH`, `LD_LIBRARY_PATH` ou equivalente no seu SO) estão configuradas corretamente.
* Compile o código fonte utilizando o comando fornecido:
  ```bash
  g++ -std=c++17 ModeloBibliotecaPadroes.cpp   -I$GUROBI_HOME/include   -L$GUROBI_HOME/lib   -lgurobi_c++ -lgurobi130   -o staff_sched
  ```
* Execute o binário gerado, passando os parâmetros de entrada caso necessário:
  ```bash
  ./staff_sched
  ```

## Licença

Este projeto é distribuído sob a **Licença Pública Geral GNU (GPL)**. Esta licença garante a liberdade de usar, estudar, modificar e distribuir o software. Qualquer trabalho derivado deve ser distribuído sob a mesma licença, conforme o princípio de *copyleft*.

## Agradecimentos

Este trabalho é fruto de muita colaboração. Gostaria de expressar meus sinceros agradecimentos a:

* **FAPESP** (Fundação de Amparo à Pesquisa do Estado de São Paulo), pelo apoio financeiro e fomento à pesquisa de Iniciação Científica.
* **Professora Dra. Franklina Maria Bragion Toledo** (Orientadora).
* **Dr. Douglas N. Nogueira** (Coorientador).
* **Prof. Greet Vanden Berghe**, pela sugestão da adoção do modelo de padrões, que abriu novos caminhos metodológicos para este projeto.
* **Juliana de Souza Moraes** (Chefe-técnica da Biblioteca do ICMC/USP).
* **Regina C. V. Medeiros** e **Irene Lucinda** (Funcionárias da Biblioteca do ICMC/USP), pelas valiosas contribuições e pela constante validação das soluções geradas.
* Ao trabalho anterior de **Lanzuolo, Nascimento e Toledo (2024)**, que serviu como sólida base inicial para este sistema.
