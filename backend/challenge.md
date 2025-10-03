# AI Challenge | Public Incentives

**Objetivo**

Desenvolver um sistema que permita identificar, para cada incentivo público existente em Portugal, as empresas mais adequadas, bem como disponibilizar um chatbot capaz de responder a perguntas sobre a informação contida na base de dados.

---

# Módulos

## **1. Fontes de dados**

**Empresas**

[companies.csv]

**Incentivos**

[incentives.csv]

---

## **2. Base de Dados**

Criar uma base de dados PostgreSQL com os dados acima, estruturada nas seguintes tabelas.

**Incentivos**

| **Coluna** | **Descrição** |
| --- | --- |
| **incentive_id** | ID único para cada incentivo |
| **title** | Título do incentivo |
| **description** | Descrição original |
| **ai_description** | Descrição estruturada em JSON gerada por IA |
| **document_urls** | Links para documentos associados |
| **publication_date** | Data de publicação (extraída deterministicamente ou por IA, se disponível) |
| **start_date** | Data de início (extraída deterministicamente ou por IA, se disponível) |
| **end_date** | Data de fim (extraída deterministicamente ou por IA, se disponível) |
| **total_budget** | Orçamento total (extraído deterministicamente ou por IA, se disponível) |
| **source_link** | Link para a página oficial do incentivo |

**Empresas**

Schema livre, a definir conforme a utilidade para o sistema.

---

## **3. Correspondência com Empresas**

Para cada incentivo, identificar e listar automaticamente as 5 empresas do dataset que melhor correspondem aos critérios definidos, utilizando LLMs.

Nota: a avaliação da correspondência não deve ser meramente subjetiva, devendo basear-se em critérios claros que assegurem consistência na análise.

---

## **4. Chatbot de Incentivos**

Criação de um chatbot que, utilizando LLMs, seja útil e proporcione uma boa UX, permitindo ao utilizador:

- obter informação sobre os incentivos,
- consultar dados sobre empresas,
- explorar as correspondências entre incentivos e empresas (dependente do passo 3).

# Requisitos

- Python.
- Deliver do código em git e output do matching em csv.
- **<0.30$** para identificar as 5 melhores empresas por incentivo.
- **<15$/1k** mensagens no chatbot.
- <**20s** até chegar o primeiro chunk da resposta.