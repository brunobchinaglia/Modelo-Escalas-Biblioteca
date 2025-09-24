# Escala de Horários da Biblioteca ICMC/USP

Este projeto, desenvolvido no âmbito do programa "Pesquisa Operacional Pro Bono" (Edital PUB 2024/2025), oferece uma solução computacional para a otimização da escala de horários dos funcionários da Biblioteca do Instituto de Ciências Matemáticas e de Computação (ICMC) da USP. O objetivo é gerar uma escala de trabalho justa e eficiente, que respeite as regras de funcionamento da biblioteca, as leis trabalhistas e as preferências individuais dos funcionários.

O código implementa um modelo de otimização matemática em duas etapas para resolver esse complexo problema de alocação de pessoal. O resultado é uma escala semestral detalhada, apresentada em formato de calendário, que busca maximizar a satisfação da equipe.

## Sobre o Projeto

A gestão da escala de horários em setores de atendimento ao público, como bibliotecas, é um desafio que envolve múltiplas variáveis. Este projeto dá continuidade a um trabalho anterior, aprimorando o modelo para incluir novas regras e necessidades apontadas pela equipe da biblioteca do ICMC/USP.

A solução proposta utiliza a Pesquisa Operacional para criar uma escala que equilibra a carga de trabalho, especialmente nos rodízios de sextas-feiras e sábados, e distribui de forma equitativa as folgas decorrentes de feriados. O sistema foi validado pela equipe da biblioteca e a escala gerada foi adotada, alcançando um alto índice de satisfação entre os funcionários, que variou de 97% a 100%.

## Funcionalidades

* **Modelagem Matemática Avançada:** Utiliza otimização linear inteira para encontrar a melhor solução possível para a escala.
* **Resolução em Duas Etapas:**
    1.  **Rodízio de Fim de Semana:** Define as escalas para os turnos críticos de sextas-feiras à noite e sábados de manhã, focando na distribuição justa e no respeito às preferências.
    2.  **Dias da Semana e Feriados:** Ajusta a escala noturna para os demais dias da semana, garantindo uma distribuição equilibrada das folgas em semanas com feriados.
* **Coleta de Preferências Automatizada:** Importa as preferências dos funcionários diretamente de um formulário Google, simplificando o processo de entrada de dados.
* **Configuração Flexível:** Permite a definição de parâmetros semestrais, como o período letivo e feriados, através de uma planilha de configuração.
* **Visualização Clara:** Gera uma imagem (`.png`) com a escala completa do semestre, organizada por meses e com legendas de fácil compreensão.
* **Exportação de Dados:** Cria um arquivo `SolucaoSemestre.csv` com a escala detalhada.

## Metodologia

O problema de escalonamento é complexo devido ao grande número de restrições e à necessidade de equilibrar a satisfação de múltiplos funcionários. A abordagem adotada divide o problema em dois modelos matemáticos resolvidos sequencialmente.

### 1. Modelo de Rodízio (Sextas e Sábados)

O primeiro modelo foca nos dias de maior complexidade para o rodízio. Ele considera as seguintes regras:

* **Função Objetivo:** Maximizar o nível de felicidade do funcionário menos satisfeito, garantindo uma solução equitativa.
* **Restrições:**
    * Proibição de trabalho em três sextas-feiras ou três sábados consecutivos.
    * Impedimento de que um funcionário trabalhe na sexta-feira e no sábado seguinte.
    * Garantia de dois funcionários de nível técnico ou superior em todos os turnos de rodízio.
    * Distribuição equilibrada das escalas de sexta-feira ao longo dos meses.
    * Presença de pelo menos um funcionário de cada grupo funcional (STI e SAU) aos sábados.

### 2. Modelo de Ajuste (Dias da Semana e Feriados)

Após a definição da escala de sextas-feiras e sábados, o segundo modelo é executado para alocar os turnos noturnos dos demais dias da semana (segunda-feira à quinta-feira), com foco especial em semanas que contêm feriados.

* **Função Objetivo:** Minimizar a diferença entre o funcionário que mais trabalha e o que menos trabalha em semanas com feriados, promovendo o equilíbrio das folgas.
* **Restrições:**
    * Alocação de dois funcionários por noite, respeitando os dias da semana em que cada um pode trabalhar.
    * Limite máximo de dois turnos noturnos por semana para cada funcionário.
    * Contabilização das escalas de sexta-feira, já definidas pelo primeiro modelo, como parâmetro de entrada.

## Primeiros Passos

Para utilizar o sistema, siga os passos abaixo.

### Pré-requisitos

* Python 3.x
* Bibliotecas Python: `gspread`, `gspread-dataframe`, `pyscipopt`, `pandas`, `numpy`, `matplotlib`, `Pillow`.
* Acesso à API do Google Sheets com um arquivo de credenciais (`.json`).

### Configuração

1.  **Credenciais do Google:**
    * Habilite a API do Google Drive e a API do Google Sheets no seu projeto do Google Cloud Platform.
    * Crie uma conta de serviço e gere um arquivo de credencial JSON.
    * Renomeie o arquivo para `direct-plasma-459913-t4-d69064b9f4bc.json` e coloque-o na mesma pasta do script.
    * Compartilhe suas planilhas Google com o e-mail da conta de serviço.

2.  **Planilha de Preferências (Google Forms):**
    * Crie um formulário para que os funcionários possam indicar suas preferências ("Gostaria", "Indiferente", "Não Gostaria") para trabalhar nas sextas-feiras e sábados do semestre.
    * A planilha de respostas deve ser nomeada como **"Escala de Horário - Consulta (respostas)"**.

3.  **Planilha de Restrições do Semestre:**
    * Crie uma planilha no Google Sheets chamada **"Restrições Semestre"**.
    * Esta planilha deve conter as informações sobre o período do semestre, feriados e a escala de dias da semana de cada funcionário.

### Execução

1.  Execute o script Python principal.
2.  O programa irá:
    * Baixar e processar os dados das planilhas Google.
    * Resolver os modelos de otimização.
    * Imprimir a escala no terminal.
    * Gerar o arquivo `SolucaoSemestre.csv` com a solução.
    * Criar e abrir a imagem `escala_semestre_final.png` com a escala visual completa.

## Licença

Este projeto é distribuído sob a **Licença Pública Geral GNU (GPL)**. Esta licença garante a liberdade de usar, estudar, modificar e distribuir o software. Qualquer trabalho derivado deve ser distribuído sob a mesma licença, conforme o princípio de *copyleft*.

## Agradecimentos

* **Professora Dra. Franklina Maria Bragion Toledo** (Orientadora)
* **Dr. Douglas N. Nogueira** (Coorientador)
* **Juliana de Souza Moraes** (Chefe-técnica da Biblioteca do ICMC/USP).
* **Regina C. V. Medeiros** e **Irene Lucinda** (Funcionárias da Biblioteca do ICMC/USP), pelas valiosas contribuições e pela validação do modelo.
* Ao trabalho anterior de **Lanzuolo, Nascimento e Toledo (2024)**, que serviu como base para este projeto.
