# 🎸 Empório da Música AI

**An AI-powered customer service assistant for a fictional musical instrument store**, developed in Python as a solution to Artefact's **AI Engineer technical challenge**.

The agent communicates in **Brazilian Portuguese** and determines when to query operational data or retrieve rules from the store's policy manual. The application combines a locally hosted language model through **Ollama**, Python tools, a **SQLite** database, and a **Streamlit** web interface.

> **Scope:** This is a demonstration prototype using the datasets provided for the challenge. Prices, stock levels, orders, and tracking information come from a static dataset, not live retail systems.

## Features

- **Product catalog:** Search by name, category, availability, and price range.
- **Product details:** Retrieve recorded descriptions, specifications, prices, and stock levels.
- **Promotions:** Apply discount rules recorded in the database.
- **Order lookup:** Search by order number and registered email address, including historical status and order information.
- **Store policies:** Retrieve relevant passages from a PDF manual to answer questions about exchanges, returns, payments, and business hours.
- **Context-aware conversations:** Maintain session history and let customers select an item from a product list by number.
- **Responsible responses:** Aim to avoid fabricated data or presenting undocumented policies as confirmed rules.
- **Two interfaces:** A Streamlit web chat and a command-line interface.

## Architecture

The solution uses a **hybrid architecture combining Function Calling with lexical document retrieval**.

```text
                         ┌──────────────────────┐
                         │       Customer       │
                         └──────────┬───────────┘
                                    │
                         ┌──────────▼───────────┐
                         │  Streamlit or CLI    │
                         └──────────┬───────────┘
                                    │
                         ┌──────────▼───────────┐
                         │     AtendenteIA      │
                         │  History + Prompt    │
                         └──────────┬───────────┘
                                    │
                         ┌──────────▼───────────┐
                         │  Qwen 2.5 3B /       │
                         │       Ollama         │
                         └──────────┬───────────┘
                                    │
                              Tool selection
                                    │
               ┌────────────────────┼────────────────────┐
               │                    │                    │
        ┌──────▼───────┐     ┌──────▼───────┐    ┌──────▼──────────┐
        │ Products and │     │   Orders     │    │ Store policies  │
        │ promotions   │     │              │    │                 │
        │   SQLite     │     │   SQLite     │    │ PDF / PyMuPDF   │
        └──────┬───────┘     └──────┬───────┘    └──────┬──────────┘
               └────────────────────┼───────────────────┘
                                    │
                         ┌──────────▼───────────┐
                         │  Customer response   │
                         └──────────────────────┘
```

### Available tools

| Tool | Purpose | Data source |
|---|---|---|
| `buscar_produtos` | Search for instruments and filter results | SQLite |
| `consultar_produto` | Retrieve details about an instrument | SQLite |
| `consultar_pedido` | Look up a historical order record | SQLite |
| `consultar_politicas` | Find relevant sections of the store manual | PDF |

The model **does not execute arbitrary SQL queries**. It selects from a predefined set of tools; database queries and filtering logic are implemented in Python.

## Technical Decisions

### Language model: Ollama + Qwen 2.5 3B

A local model was chosen to avoid per-request inference charges and allow the prototype to run without relying on a commercial API. Qwen 2.5 3B interprets customer messages and selects the appropriate tools.

This involves a trade-off: smaller models may confuse categories or tool arguments and may be slow on machines without a dedicated GPU. To mitigate these issues, the code validates product filters and uses responses formatted directly in Python whenever possible.

### Function Calling instead of prompt-only responses

Information such as prices, stock levels, promotions, and orders is not entrusted to the model's memory. When needed, the agent calls Python functions that query the structured dataset.

For straightforward product searches, Python formats the returned list without requiring a second model inference. This reduces response time and preserves the values retrieved from the database.

### SQLite for structured data

The six provided CSV files are imported into a local relational database. SQLite makes it possible to relate customers, orders, order items, products, categories, and promotions without running a separate database server.

Monetary amounts are stored as **integer cents** in the database, reducing the precision problems commonly associated with floating-point arithmetic.

### Lexical retrieval from the policy manual

The PDF manual is processed using **PyMuPDF**. Its sections are identified and ranked according to matches between the customer's question and the document, with word normalization and synonyms.

This version does not use embeddings or a vector database. For a small, clearly structured manual, lexical retrieval is simple and inexpensive to run. However, it may struggle with ambiguous questions or wording that differs significantly from the source document.

### Prompt, conversation history, and uncertainty handling

The system prompt instructs the agent to maintain an appropriate customer service tone, use available sources, and avoid unverified statements. Conversation history is kept in memory during the session, subject to a configurable message limit.

When a policy is unavailable or the documentation is ambiguous, the expected behavior is to acknowledge the limitation and advise the customer to confirm the details with the store's support team.

## Technology Stack

| Technology | Role |
|---|---|
| Python 3.12 | Primary programming language |
| Ollama | Local model execution |
| Qwen 2.5 3B | Language model with tool-calling support |
| SQLite | Product, customer, and order data |
| PyMuPDF | PDF reading and section extraction |
| Streamlit | Browser-based chat interface |
| python-dotenv | Local environment configuration |
| Pytest | Automated testing |

## Project Structure

```text
emporio-musica-ai/
├── .streamlit/
│   └── config.toml
├── app/
│   ├── agent.py                  # Agent and tool orchestration
│   ├── prompts.py                # Customer service instructions
│   ├── main.py                   # Terminal chat
│   ├── database/
│   │   ├── connection.py         # SQLite connection
│   │   └── import_data.py        # Table creation and CSV import
│   ├── services/
│   │   └── retrieval.py          # PDF section retrieval
│   └── tools/
│       ├── products.py           # Product catalog and details
│       ├── orders.py             # Order lookups
│       └── policies.py           # Store policy lookups
├── data/
│   ├── categories.csv
│   ├── customers.csv
│   ├── products.csv
│   ├── orders.csv
│   ├── order_items.csv
│   ├── promotions.csv
│   └── politicas_da_loja.pdf
├── tests/                         # Pytest test suite
├── examples/                      # Recorded demonstration conversations
├── streamlit_app.py               # Web interface
├── requirements.txt
├── .env.example
└── README.md
```

The `data/emporio_musica.db` file is created locally during the import step and does not need to be committed to version control.

## Installation and Usage

### Prerequisites

- **Python 3.12** installed.
- **Ollama** installed and running.
- PowerShell, Bash, or an equivalent terminal.
- The CSV files and PDF included in `data/`.

### 1. Install and configure Ollama

Install Ollama: <https://ollama.com/download>

Download the model used by this project:

```bash
ollama pull qwen2.5:3b
```

Check that the model is available:

```bash
ollama list
```

The Ollama service must be running for the agent to respond.

### 2. Set up the Python environment

From the project root, create a virtual environment:

```bash
python -m venv .venv
```

Activate it on **Windows (PowerShell)**:

```powershell
.\.venv\Scripts\Activate.ps1
```

Or on **Linux/macOS**:

```bash
source .venv/bin/activate
```

Install the dependencies:

```bash
python -m pip install -r requirements.txt
```

### 3. Configure environment variables

Copy `.env.example` to `.env` and review the settings:

```dotenv
LLM_PROVIDER=ollama
OLLAMA_HOST=http://127.0.0.1:11434
OLLAMA_MODEL=qwen2.5:3b
DATABASE_PATH=data/emporio_musica.db
POLICIES_PATH=data/politicas_da_loja.pdf
MAX_HISTORY_MESSAGES=12
```

The `.env` file contains local configuration and should not be committed to the repository.

### 4. Initialize the database

Run this command from the project root:

```bash
python -m app.database.import_data
```

The command creates the SQLite tables and imports all six CSV files:

| Table | Sample records |
|---|---:|
| `categories` | 9 |
| `customers` | 50 |
| `products` | 65 |
| `orders` | 20 |
| `order_items` | 22 |
| `promotions` | 25 |

> **Important:** Running the import again recreates the records from the CSV files. Local changes made directly to these tables may be lost.

### 5. Start the assistant

**Web interface (recommended):**

```bash
python -m streamlit run streamlit_app.py
```

Open <http://localhost:8501> in your browser. The interface provides session history, suggested questions, an option to start a new conversation, and the ability to export chat transcripts as Markdown.

**Command-line interface:**

```bash
python -m app.main
```

In the terminal, use `/limpar` to reset the conversation and `/sair` to exit. These command names remain in Portuguese because they are part of the implemented CLI.

## Conversation Examples

The [`examples/`](examples/) folder contains conversations recorded while running the application:

| Example | Scenario |
|---|---|
| [`01_catalogo.md`](examples/01_catalogo.md) | Acoustic guitar search within a budget and product selection |
| [`02_devolucao.md`](examples/02_devolucao.md) | Applying the manual's return policy |
| [`03_pedido.md`](examples/03_pedido.md) | Order lookup and checking the information provided |
| [`04_fora_escopo.md`](examples/04_fora_escopo.md) | Catalog limitations and handling undocumented policies |

The examples illustrate the prototype's behavior with the provided dataset; there is no communication with live sales or shipping services.

## Testing

Run the automated test suite from the project root:

```bash
python -m pytest tests/ -v
```

Tests cover product filtering, discounts, item selection, order lookups, policy manual retrieval, argument validation, and tool orchestration. Agent tests simulate Ollama client responses, so the application logic can be tested without performing a real model inference on every run.

Manual testing through the interface is complementary, because the language model's behavior may vary between runs.

## Security, Scope, and Limitations

- **Static data:** The catalog and orders reflect the provided CSV files and are not updated in real time.
- **Authentication:** Checking an order number and email address is only a demonstration-level verification method; it does not replace secure authentication in production.
- **Shipment tracking:** Tracking codes and estimated dates are historical records, not live confirmations from a carrier.
- **LLM accuracy:** The model may misinterpret requests or tool arguments; some inputs are validated in Python.
- **Document retrieval:** Lexical search is not equivalent to full semantic search and may fail on ambiguous questions.
- **Performance:** Qwen 2.5 3B may have noticeable latency when running on CPU only.
- **Conversation history:** Messages are kept in memory during the session and are not persisted after the session ends.
- **Operations:** The prototype cannot place orders, process payments, modify orders, or communicate directly with shipping carriers.

The data and rules are intended **exclusively for technical demonstration**. A production deployment would require authentication, access controls, monitoring, integration with operational systems, and ongoing evaluation of responses.

## Potential Improvements

- Semantic retrieval using embeddings and relevance evaluation.
- Customer authentication using one-time codes or integration with verified identities.
- Integration with live inventory and order management systems.
- Optional persistence of conversations and customer service metrics.
- Response-quality tests using predefined scenarios and expected answers.
- Structured logging, latency metrics, and tool-call tracing.
- Deployment to infrastructure suited to local or remote inference.

---

**Empório da Música AI** — A demonstration project developed for Artefact's AI Engineer technical challenge.
