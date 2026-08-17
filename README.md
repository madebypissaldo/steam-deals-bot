# Steam Deals Bot

Aplicação Python para consultar preços e promoções da Steam por meio de um bot interativo público no Telegram. O bot aceita conversas privadas, usa long polling e menus com Inline Keyboard.

## Funcionalidades

- Consulta de promoções em destaque da Steam.
- Listas de maiores descontos (até 5 páginas de 5 resultados), jogos até R$ 20 e descontos de 80% ou mais.
- Pesquisa de jogo por nome.
- Pesquisa por categorias suportadas pelos gêneros retornados pela API Steam.
- Menus interativos e paginação de resultados no Telegram.
- Feedback visual enquanto uma consulta está em andamento.
- Cache em memória de promoções por cinco minutos.
- Long polling com tratamento de falhas temporárias e logs de duração.
- Proteções em memória: rate limit, limite de concorrência por usuário e limite global de pesquisas.
- Validação de mensagens, callbacks e tamanho de pesquisas por nome.

## Demonstração

```text
🎮 Steam Deals Bot

O que deseja fazer?

[ 🔥 Maiores descontos ] [ 🔎 Pesquisar jogo ]
[ 💸 Até R$ 20 ]         [ 📉 80% ou mais ]
[ ⭐ Minha Watchlist ]
```

## Arquitetura

```text
Telegram
   │
   ▼
telegram.bot (long polling)
   │
   ▼
telegram.handlers ───────► telegram.keyboards / telegram.states
   │
   ├──► services.telegram ───► Telegram Bot API
   │
   └──► services.steam ──────► Steam Store API
```

## Estrutura do projeto

```text
.
├── data/
│   └── games_appid.json
├── services/
│   ├── steam.py
│   └── telegram.py
├── telegram/
│   ├── bot.py
│   ├── handlers.py
│   ├── keyboards.py
│   ├── protection.py
│   └── states.py
├── tests/
├── .env.example
├── main.py
├── requirements.txt
└── start_bot.sh
```

## Tecnologias

- Python
- Telegram Bot API
- Steam Store API (`appdetails` e `featuredcategories`)
- Requests
- python-dotenv
- unittest

## Requisitos

- Python 3.10 ou superior.
- Uma conta Telegram e um bot criado no BotFather.
- Credencial da Steam configurada em `STEAM_API_KEY`.

## Instalação

```bash
git clone <repository-url>
cd Steam_Dev_app

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Configuração

Crie o arquivo `.env` a partir do exemplo:

```bash
cp .env.example .env
```

Preencha as variáveis:

```env
STEAM_API_KEY=
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
```

| Variável | Descrição |
| --- | --- |
| `STEAM_API_KEY` | Chave usada nas consultas de detalhes da Steam. |
| `TELEGRAM_BOT_TOKEN` | Token do bot fornecido pelo BotFather. |
| `TELEGRAM_CHAT_ID` | Opcional. Destino padrão das notificações enviadas pelo modo CLI. Não limita o acesso público ao bot. |

## Como iniciar

Na raiz do projeto:

```bash
./start_bot.sh
```

Caso necessário, conceda permissão de execução uma única vez:

```bash
chmod +x start_bot.sh
```

O script usa automaticamente `.venv/bin/python`. Iniciar o processo não envia mensagens ao Telegram; envie `/start` para abrir o menu.

## Uso

- `/start` ou `/menu`: abre o menu principal.
- `/help`: mostra uma instrução curta.

Pelo menu, qualquer usuário em conversa privada pode consultar promoções, pesquisar um jogo por nome e filtrar ofertas. Em **Maiores descontos**, são exibidos até 25 resultados em páginas de 5, quando houver promoções suficientes. A watchlist aparece como placeholder e ainda não possui persistência.

As categorias atualmente disponíveis são Ação, RPG, Corrida, Estratégia e Indie. FPS, Survival e Terror dependem de tags que não são retornadas pelos endpoints Steam estruturados utilizados; o bot as identifica como indisponíveis e oferece retorno às categorias, sem executar uma pesquisa incorreta.

## Testes

Execute os testes sem acessar a Steam ou o Telegram:

```bash
.venv/bin/python -m unittest discover -s tests -p 'test_*.py' -v
```

## Segurança

- Não versione o arquivo `.env` nem exponha `TELEGRAM_BOT_TOKEN`.
- Use `.env.example` somente com valores vazios.
- O bot aceita apenas chats privados; grupos, supergrupos e canais são ignorados.
- Pesquisas são limitadas a uma operação a cada dois segundos por usuário, com burst de até cinco operações em dez segundos.
- Cada usuário pode ter uma pesquisa ativa e o processo executa no máximo quatro pesquisas Steam simultâneas.
- A lista de promoções é mantida em cache compartilhado por cinco minutos.

## Roadmap

- [ ] Watchlist persistente.
- [ ] Alertas personalizados de preço.
- [ ] Histórico de preços.
- [ ] Persistência do cache.
- [ ] Webhook como alternativa futura ao long polling.
