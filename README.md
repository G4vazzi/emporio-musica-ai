
# 🎸 Empório da Música AI

Assistente virtual de atendimento desenvolvido em Python para o desafio técnico de **AI Engineer da Artefact**.

O projeto simula o atendimento de uma loja de instrumentos musicais, permitindo consultar produtos, preços, disponibilidade, pedidos e políticas comerciais por meio de linguagem natural.

A solução utiliza um modelo de linguagem local, integrado a ferramentas Python e a uma base de dados SQLite.

## Funcionalidades

- Atendimento conversacional em português brasileiro.
- Pesquisa de instrumentos por nome, categoria e orçamento.
- Consulta de preços, estoque e especificações.
- Aplicação de descontos e promoções registrados na base.
- Seleção de instrumentos por número.
- Consulta de pedidos históricos por número e e-mail.
- Recuperação de informações do manual de políticas em PDF.
- Tratamento de perguntas fora do escopo e informações ausentes.
- Interface web com Streamlit.
- Testes automatizados com Pytest.

As consultas aos dados operacionais são realizadas sobre uma base local fornecida para o desafio. Não existe integração com um sistema de gestão ou transportadora em tempo real.

## Tecnologias

| Tecnologia | Utilização |
|---|---|
| Python 3.12 | Linguagem principal |
| Ollama | Execução local do LLM |
| Qwen 2.5 3B | Interpretação de mensagens e seleção de ferramentas |
| SQLite | Armazenamento dos dados estruturados |
| PyMuPDF | Extração de informações do PDF |
| Streamlit | Interface web |
| Pytest | Testes automatizados |
| python-dotenv | Configurações de ambiente |

## Arquitetura

O agente utiliza uma abordagem híbrida baseada em **Function Calling e recuperação lexical de documentos**.

O fluxo principal é:

1. O cliente envia uma mensagem pelo Streamlit ou terminal.
2. O modelo Qwen interpreta a solicitação.
3. Quando necessário, o modelo seleciona uma ferramenta Python.
4. A ferramenta consulta o SQLite ou recupera seções do PDF.
5. O resultado é utilizado para construir a resposta.
6. O cliente recebe as informações na interface.

```text
Cliente
   |
   v
Streamlit / CLI
   |
   v
AtendenteIA
   |
   v
Qwen 2.5 3B (Ollama)
   |
   +---- buscar_produtos ------> SQLite
   |
   +---- consultar_produto ----> SQLite
   |
   +---- consultar_pedido -----> SQLite
   |
   +---- consultar_politicas --> Manual PDF
   |
   v
Resposta ao cliente
```

### Ferramentas do agente

| Função | Responsabilidade |
|---|---|
| `buscar_produtos()` | Pesquisa instrumentos por filtros |
| `consultar_produto()` | Recupera detalhes de um instrumento |
| `consultar_pedido()` | Consulta dados históricos de um pedido |
| `consultar_politicas()` | Recupera trechos relevantes do manual |

As ferramentas são registradas explicitamente no agente. O modelo não recebe permissão para executar comandos arbitrários no banco de dados.

### Respostas determinísticas

As buscas simples de produtos são formatadas diretamente pelo Python, depois que o modelo seleciona a ferramenta.

Essa decisão reduz o número de inferências, evita alterações indevidas nos preços apresentados e melhora o desempenho em computadores com recursos limitados.

O projeto também valida determinados argumentos produzidos pelo modelo. Por exemplo, evita confundir a categoria "violões" com "viola" quando a solicitação original é clara.

## Pré-requisitos

- Python 3.12
- Ollama instalado
- Modelo `qwen2.5:3b` disponível localmente
- Memória suficiente para executar o modelo
- Git, caso deseje clonar o repositório

O uso de GPU é opcional. O modelo também funciona em CPU, mas as respostas podem ser mais lentas.

## Instalação

### 1. Instalar o Ollama

Baixe o instalador para seu sistema operacional:

https://ollama.com/download

Depois de instalar, execute:

```powershell
ollama pull qwen2.5:3b
```

Confirme a instalação:

```powershell
ollama list
```

O serviço Ollama deve estar em execução durante o atendimento.

### 2. Criar o ambiente virtual

Na raiz do projeto:

```powershell
python -m venv .venv
```

No PowerShell do Windows:

```powershell
.\.venv\Scripts\Activate.ps1
```

### 3. Instalar dependências

```powershell
python -m pip install -r requirements.txt
```

### 4. Configurar variáveis de ambiente

Crie um arquivo `.env` com base em `.env.example`.

Configuração utilizada:

```dotenv
LLM_PROVIDER=ollama
OLLAMA_HOST=http://127.0.0.1:11434
OLLAMA_MODEL=qwen2.5:3b

DATABASE_PATH=data/emporio_musica.db
POLICIES_PATH=data/politicas_da_loja.pdf

MAX_HISTORY_MESSAGES=12
```

Não é necessário possuir uma chave da API OpenAI.

### 5. Inicializar o banco de dados

O banco SQLite é criado a partir dos seis arquivos CSV fornecidos no desafio.

Execute:

```powershell
python -m app.database.import_data
```

A base inicial possui:

| Tabela | Registros |
|---|---:|
| Categorias | 9 |
| Clientes | 50 |
| Produtos | 65 |
| Pedidos | 20 |
| Itens de pedidos | 22 |
| Promoções | 25 |

**Atenção:** o importador recria os registros dessas tabelas a partir dos CSVs. Alterações manuais no banco podem ser perdidas ao executar novamente o script.

## Executando o projeto

### Interface web

```powershell
python -m streamlit run streamlit_app.py
```

A aplicação estará disponível normalmente em:

http://localhost:8501

### Interface de terminal

```powershell
python -m app.main
```

Comandos disponíveis:

- `/sair`: encerra a aplicação de terminal.
- `/limpar`: limpa o histórico da conversa.

## Testes automatizados

Para executar todos os testes:

```powershell
python -m pytest tests/ -v
```

Os testes verificam consultas aos produtos, regras de disponibilidade, promoções, pedidos, recuperação documental e orquestração de ferramentas.

Os testes do agente utilizam um cliente Ollama simulado, evitando consumo de recursos de inferência e permitindo a validação isolada do fluxo de Function Calling.

Os testes automatizados não substituem a avaliação de respostas produzidas pelo modelo real.

## Decisões técnicas

### Por que Ollama e Qwen 2.5 3B?

O desafio permite modelos locais ou via API.

Escolhi o Ollama para executar um LLM sem custos por requisição e reduzir a dependência de serviços externos.

O Qwen 2.5 3B foi selecionado pelo equilíbrio entre tamanho, capacidade de compreender português e suporte a chamadas de ferramentas.

A limitação principal é o desempenho em CPU e a menor confiabilidade do modelo em comparação com modelos maiores.

### Por que SQLite?

Os dados fornecidos são estruturados, possuem identificadores relacionais e representam um volume pequeno.

SQLite permite consultas SQL, integridade referencial e execução local sem a necessidade de configurar um servidor de banco de dados.

### Por que recuperação lexical em vez de banco vetorial?

O manual de políticas possui oito páginas e está organizado em seções numeradas.

Por esse motivo, optei por extrair o texto usando PyMuPDF, separar as seções e classificá-las por correspondência de termos e sinônimos.

Essa estratégia é mais simples e econômica para o volume de documentos disponibilizado.

Não foram utilizados embeddings ou banco vetorial. O mecanismo apresenta limitações para consultas ambíguas e perguntas semanticamente distantes da redação do manual.

### Estratégia de prompt

O prompt de sistema define a identidade da loja, o tom de atendimento e as regras de utilização das ferramentas.

O agente é orientado a consultar dados antes de informar preços, estoque, condições comerciais e status de pedidos.

A ausência de informações deve ser informada com transparência, sem inventar políticas ou resultados.

### Histórico de conversa

O agente mantém um histórico limitado em memória. Na interface Streamlit, cada sessão possui seu próprio estado de conversação.

O histórico não é salvo de forma persistente em um banco de dados.

## Segurança e privacidade

O protótipo utiliza apenas ferramentas de consulta e não permite modificar pedidos, excluir registros ou efetuar compras.

As consultas de pedidos utilizam parâmetros SQL, evitando a concatenação direta de valores fornecidos pelo cliente.

Para consultar um pedido, é necessário informar o número e o e-mail cadastrado.

Entretanto, **essa conferência não representa autenticação forte**. Uma implementação real precisaria de verificação de identidade, por exemplo, usando um código temporário enviado ao titular.

O projeto utiliza dados fictícios disponibilizados para o desafio e não deve ser utilizado diretamente em produção.

## Limitações conhecidas

- O Ollama e o modelo precisam estar instalados na máquina de execução.
- A inferência local em CPU pode apresentar latência elevada.
- O modelo pode interpretar incorretamente a intenção ou os argumentos de uma ferramenta.
- A recuperação lexical não garante correspondência semântica perfeita.
- Os CSVs representam uma base estática, sem atualização em tempo real.
- Pedidos e rastreamentos são dados históricos.
- O histórico não persiste após o encerramento da sessão.
- A verificação por número e e-mail não é autenticação suficiente para produção.
- Não existem integrações reais com WhatsApp, pagamentos, Correios ou sistemas de gestão.

## Melhorias futuras

Com mais tempo, as principais evoluções seriam:

- Implementação de autenticação com código temporário.
- Integração com um banco de dados operacional atualizado.
- Recuperação semântica com embeddings e avaliação de relevância.
- Testes de qualidade das respostas com casos de referência.
- Observabilidade estruturada das chamadas de ferramentas.
- Cache de consultas frequentes.
- Persistência de sessões e histórico.
- Implantação em ambiente com recursos adequados para inferência.

## Exemplos de interação

A pasta `examples/` contém conversas de demonstração que ilustram diferentes comportamentos do agente.

Os exemplos devem ser registrados a partir de execuções reais da aplicação, especialmente nos cenários de consulta ao catálogo, pedidos, aplicação das políticas e situações fora do escopo.

## Uso de assistentes de IA no desenvolvimento

Utilizei o ChatGPT como apoio durante o planejamento, implementação e revisão do projeto.

O assistente foi utilizado para discutir decisões arquiteturais, estruturar módulos Python, propor testes, identificar erros e apoiar a documentação.

As implementações foram integradas e testadas no ambiente local utilizando VS Code, GitHub Desktop, Pytest e Ollama.

O ChatGPT não é o modelo utilizado para o atendimento ao cliente: essa função é realizada localmente pelo Qwen 2.5 por meio do Ollama.

## Contexto

Projeto desenvolvido exclusivamente para a etapa técnica do processo seletivo de AI Engineer da Artefact.

A Empório da Música é uma empresa fictícia criada para o cenário do desafio.
