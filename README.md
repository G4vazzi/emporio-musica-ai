# 🎸 Empório da Música AI

**Assistente virtual de atendimento para uma loja fictícia de instrumentos musicais**, desenvolvido em Python como solução para o desafio técnico de **AI Engineer da Artefact**.

O agente conversa em português, identifica quando precisa consultar dados da operação e quando precisa buscar regras do manual da loja. A aplicação utiliza um modelo de linguagem executado localmente com **Ollama**, ferramentas Python, um banco **SQLite** e uma interface web em **Streamlit**.

> **Escopo:** protótipo demonstrativo com dados fornecidos para o desafio. Preços, estoque, pedidos e rastreamentos são informações de uma base estática, não de sistemas comerciais em tempo real.

## Funcionalidades

- **Catálogo:** pesquisa por nome, categoria, disponibilidade e faixa de preço.
- **Detalhes de produtos:** descrição, especificações, preço e estoque registrados.
- **Promoções:** aplicação das condições de desconto registradas na base de dados.
- **Consulta de pedidos:** busca por número do pedido e e-mail cadastrado, com status e informações históricas.
- **Políticas da loja:** recuperação de trechos do manual em PDF para dúvidas sobre trocas, devoluções, pagamentos e funcionamento.
- **Conversa contextual:** mantém o histórico da sessão e permite selecionar um produto de uma lista pelo número.
- **Respostas responsáveis:** procura não inventar dados nem apresentar uma política não documentada como regra confirmada.
- **Duas interfaces:** chat web com Streamlit e atendimento via terminal.

## Arquitetura

A solução adota uma **arquitetura híbrida de Function Calling e recuperação lexical de documentos**.

```text
                         ┌──────────────────────┐
                         │      Cliente         │
                         └──────────┬───────────┘
                                    │
                         ┌──────────▼───────────┐
                         │  Streamlit ou CLI    │
                         └──────────┬───────────┘
                                    │
                         ┌──────────▼───────────┐
                         │     AtendenteIA      │
                         │  Histórico + Prompt  │
                         └──────────┬───────────┘
                                    │
                         ┌──────────▼───────────┐
                         │  Qwen 2.5 3B /       │
                         │       Ollama         │
                         └──────────┬───────────┘
                                    │
                         Seleção de ferramenta
                                    │
               ┌────────────────────┼────────────────────┐
               │                    │                    │
        ┌──────▼───────┐     ┌──────▼───────┐    ┌──────▼──────────┐
        │  Produtos e  │     │   Pedidos    │    │    Políticas    │
        │  promoções   │     │              │    │                 │
        │    SQLite    │     │    SQLite    │    │ PDF / PyMuPDF   │
        └──────┬───────┘     └──────┬───────┘    └──────┬──────────┘
               └────────────────────┼───────────────────┘
                                    │
                         ┌──────────▼───────────┐
                         │  Resposta ao cliente │
                         └──────────────────────┘
```

### Ferramentas disponíveis

| Ferramenta | Objetivo | Fonte |
|---|---|---|
| `buscar_produtos` | Pesquisar instrumentos e filtrar resultados | SQLite |
| `consultar_produto` | Obter detalhes de um instrumento | SQLite |
| `consultar_pedido` | Consultar o registro histórico de um pedido | SQLite |
| `consultar_politicas` | Localizar seções pertinentes do manual | PDF |

O modelo **não executa SQL livremente**. Ele escolhe entre ferramentas previamente registradas; as consultas e os filtros são implementados em Python.

## Decisões técnicas

### Modelo de linguagem: Ollama + Qwen 2.5 3B

Foi escolhido um modelo local para evitar custos de inferência por requisição e permitir a execução do protótipo sem depender de uma API comercial. O Qwen 2.5 3B realiza a interpretação da mensagem e a seleção das ferramentas.

Essa escolha envolve um compromisso: modelos menores podem confundir categorias ou argumentos e apresentar latência elevada em máquinas sem GPU dedicada. Por isso, o código valida filtros de produtos e utiliza respostas formatadas diretamente em Python quando possível.

### Function Calling em vez de respostas baseadas apenas no prompt

Dados como preços, estoque, promoções e pedidos não são confiados à memória do modelo. Quando necessário, o agente invoca funções Python que consultam a base estruturada.

Nas pesquisas simples de produtos, o Python formata a lista retornada, evitando uma segunda inferência do modelo. Isso reduz o tempo de resposta e preserva os valores encontrados.

### SQLite para dados estruturados

As seis tabelas CSV disponibilizadas são importadas para um banco relacional local. O SQLite permite relacionar clientes, pedidos, itens, produtos, categorias e promoções sem exigir um servidor separado.

Os valores monetários são tratados em **centavos inteiros** na base, reduzindo problemas de precisão típicos de operações com ponto flutuante.

### Recuperação lexical do manual

O manual em PDF é processado com **PyMuPDF**. As seções são identificadas e classificadas conforme a correspondência entre os termos da pergunta e o conteúdo, com normalização de palavras e sinônimos.

Não há embeddings ou banco vetorial nesta versão. Para um manual pequeno e organizado em seções, essa abordagem é simples e tem baixo custo de execução; em contrapartida, pode ter dificuldade com perguntas ambíguas ou formuladas com vocabulário muito diferente do documento.

### Prompt, histórico e tratamento de incertezas

O prompt de sistema orienta o agente a manter um tom de atendimento adequado à loja, utilizar as fontes disponíveis e evitar informações não confirmadas. O histórico é mantido em memória durante a sessão, com um limite configurável de mensagens.

Quando uma regra não está disponível ou existe ambiguidade documental, o comportamento esperado é informar a limitação e orientar o cliente a confirmar com a equipe da loja.

## Tecnologias

| Tecnologia | Aplicação |
|---|---|
| Python 3.12 | Linguagem principal |
| Ollama | Execução local do modelo |
| Qwen 2.5 3B | LLM com suporte a chamadas de ferramentas |
| SQLite | Dados de produtos, clientes e pedidos |
| PyMuPDF | Leitura e segmentação do manual PDF |
| Streamlit | Interface de chat no navegador |
| python-dotenv | Configurações locais |
| Pytest | Testes automatizados |

## Estrutura do projeto

```text
emporio-musica-ai/
├── .streamlit/
│   └── config.toml
├── app/
│   ├── agent.py                  # Orquestração do agente e ferramentas
│   ├── prompts.py                # Instruções do atendente
│   ├── main.py                   # Chat via terminal
│   ├── database/
│   │   ├── connection.py         # Conexão SQLite
│   │   └── import_data.py        # Criação e importação das tabelas
│   ├── services/
│   │   └── retrieval.py          # Recuperação de seções do PDF
│   └── tools/
│       ├── products.py           # Catálogo e detalhes dos produtos
│       ├── orders.py             # Consulta de pedidos
│       └── policies.py           # Consulta das políticas
├── data/
│   ├── categories.csv
│   ├── customers.csv
│   ├── products.csv
│   ├── orders.csv
│   ├── order_items.csv
│   ├── promotions.csv
│   └── politicas_da_loja.pdf
├── tests/                         # Testes com Pytest
├── examples/                      # Conversas reais de demonstração
├── streamlit_app.py               # Interface web
├── requirements.txt
├── .env.example
└── README.md
```

O arquivo `data/emporio_musica.db` é criado localmente na etapa de importação e não precisa ser versionado.

## Instalação e execução

### Pré-requisitos

- **Python 3.12** instalado.
- **Ollama** instalado e em execução.
- Terminal PowerShell, Bash ou equivalente.
- Acesso aos CSVs e ao PDF incluídos em `data/`.

### 1. Baixar e configurar o Ollama

Instale o Ollama: <https://ollama.com/download>

Baixe o modelo utilizado:

```bash
ollama pull qwen2.5:3b
```

Confira se o modelo está disponível:

```bash
ollama list
```

O serviço Ollama precisa estar em execução para o agente responder.

### 2. Preparar o ambiente Python

Na raiz do projeto, crie um ambiente virtual:

```bash
python -m venv .venv
```

Ative-o no **Windows (PowerShell)**:

```powershell
.\.venv\Scripts\Activate.ps1
```

Ou no **Linux/macOS**:

```bash
source .venv/bin/activate
```

Instale as dependências:

```bash
python -m pip install -r requirements.txt
```

### 3. Configurar as variáveis de ambiente

Copie `.env.example` para `.env` e confira os parâmetros:

```dotenv
LLM_PROVIDER=ollama
OLLAMA_HOST=http://127.0.0.1:11434
OLLAMA_MODEL=qwen2.5:3b
DATABASE_PATH=data/emporio_musica.db
POLICIES_PATH=data/politicas_da_loja.pdf
MAX_HISTORY_MESSAGES=12
```

O arquivo `.env` contém configurações locais e não deve ser enviado ao repositório.

### 4. Criar o banco de dados

Com o terminal aberto na raiz do projeto:

```bash
python -m app.database.import_data
```

O comando cria as tabelas do SQLite e importa os seis CSVs:

| Tabela | Registros de exemplo |
|---|---:|
| `categories` | 9 |
| `customers` | 50 |
| `products` | 65 |
| `orders` | 20 |
| `order_items` | 22 |
| `promotions` | 25 |

> **Atenção:** repetir a importação recria os registros a partir dos CSVs. Alterações locais feitas diretamente nessas tabelas podem ser perdidas.

### 5. Iniciar o atendimento

**Interface web (recomendada):**

```bash
python -m streamlit run streamlit_app.py
```

Acesse <http://localhost:8501> no navegador. A interface possui histórico da sessão, perguntas sugeridas, opção de iniciar uma conversa e exportação do atendimento em Markdown.

**Interface de terminal:**

```bash
python -m app.main
```

No terminal, use `/limpar` para reiniciar a conversa e `/sair` para encerrar.

## Exemplos de interação

A pasta [`examples/`](examples/) reúne conversas registradas durante a execução da aplicação:

| Exemplo | Cenário demonstrado |
|---|---|
| [`01_catalogo.md`](examples/01_catalogo.md) | Pesquisa de violões com limite de preço e seleção de produto |
| [`02_devolucao.md`](examples/02_devolucao.md) | Aplicação das regras de devolução do manual |
| [`03_pedido.md`](examples/03_pedido.md) | Consulta de um pedido e conferência dos dados informados |
| [`04_fora_escopo.md`](examples/04_fora_escopo.md) | Limites do catálogo e tratamento de políticas não documentadas |

Os exemplos representam o comportamento do protótipo sobre a base fornecida, sem comunicação com serviços externos de venda ou logística.

## Testes

Execute a suíte automatizada na raiz do projeto:

```bash
python -m pytest tests/ -v
```

Os testes cobrem filtros de produtos, descontos, seleção de itens, consultas de pedidos, recuperação do manual, validação de argumentos e orquestração de ferramentas. Os testes do agente simulam as respostas do cliente Ollama, permitindo verificar a lógica sem exigir uma inferência real a cada execução.

A validação manual na interface é complementar, pois o comportamento do modelo de linguagem pode variar entre execuções.

## Segurança, escopo e limitações

- **Dados estáticos:** o catálogo e os pedidos refletem os CSVs fornecidos, sem sincronização em tempo real.
- **Autenticação:** a conferência por número de pedido e e-mail é apenas uma verificação demonstrativa; não substitui autenticação segura em produção.
- **Rastreamento:** códigos e previsões são registros históricos, não informações confirmadas pela transportadora.
- **Precisão do LLM:** o modelo pode interpretar incorretamente solicitações ou argumentos; algumas entradas são verificadas pelo código Python.
- **Recuperação documental:** a busca lexical não equivale a uma busca semântica completa e pode falhar em perguntas ambíguas.
- **Desempenho:** o Qwen 2.5 3B pode apresentar latência perceptível quando executado somente em CPU.
- **Histórico:** as mensagens são armazenadas apenas em memória durante a sessão, sem persistência após seu encerramento.
- **Operações:** o protótipo não realiza compras, pagamentos, alterações de pedido ou comunicação direta com a transportadora.

Os dados e as regras são destinados **exclusivamente à demonstração técnica**. Para uso real, seriam necessários autenticação, controles de acesso, monitoramento, integração com sistemas operacionais e avaliação contínua das respostas.

## Possíveis evoluções

- Recuperação semântica com embeddings e avaliação de relevância.
- Autenticação do cliente com código temporário ou integração a uma identidade verificada.
- Integração com catálogo e gestão de pedidos atualizados.
- Persistência opcional de conversas e métricas de atendimento.
- Testes de qualidade de resposta com cenários e respostas esperadas.
- Logs estruturados, métricas de latência e rastreamento de chamadas de ferramentas.
- Implantação em infraestrutura apropriada para inferência local ou remota.

---

**Empório da Música AI** — Projeto demonstrativo desenvolvido para o desafio técnico de AI Engineer da Artefact.
