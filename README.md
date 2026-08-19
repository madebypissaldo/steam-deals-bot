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
- Alertas opt-in de Best Deals com varredura diária, deduplicação persistente e envio proativo.

## Demonstração

```text
🎮 Steam Deals Bot

O que deseja fazer?

[ 🔥 Maiores descontos ] [ 🔎 Pesquisar jogo ]
[ 💸 Até R$ 20 ]         [ 📉 80% ou mais ]
[ 🔔 Alertas Best Deals ]
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
   ├──► services.steam / services.best_deals ───► Steam Store API
   │
   └──► scheduler.best_deals ───► storage.database (SQLite)
```

## Estrutura do projeto

```text
.
├── data/
│   └── games_appid.json
├── services/
│   ├── best_deals.py
│   ├── steam.py
│   └── telegram.py
├── scheduler/
│   └── best_deals.py
├── storage/
│   └── database.py
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
git clone https://github.com/madebypissaldo/steam-deals-bot.git
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
BEST_DEALS_MIN_DISCOUNT=90
BEST_DEALS_MAX_PRICE=10
BEST_DEALS_MAX_NOTIFICATIONS=10
BEST_DEALS_SCAN_HOUR=12
APP_TIMEZONE=America/Sao_Paulo
```

| Variável | Descrição |
| --- | --- |
| `STEAM_API_KEY` | Chave usada nas consultas de detalhes da Steam. |
| `TELEGRAM_BOT_TOKEN` | Token do bot fornecido pelo BotFather. |
| `TELEGRAM_CHAT_ID` | Opcional. Destino padrão das notificações enviadas pelo modo CLI. Não limita o acesso público ao bot. |
| `BEST_DEALS_MIN_DISCOUNT` | Desconto mínimo para uma oferta excepcional barata. Padrão: `90`. |
| `BEST_DEALS_MAX_PRICE` | Preço final máximo, em reais, para essa regra. Padrão: `10`. |
| `BEST_DEALS_MAX_NOTIFICATIONS` | Máximo de ofertas processadas por varredura. Padrão: `10`. |
| `BEST_DEALS_SCAN_HOUR` | Hora diária da varredura, de `0` a `23`. Padrão: `12`. |
| `APP_TIMEZONE` | Timezone do agendador. Padrão: `America/Sao_Paulo`. |

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

## Best Deals Alerts

Consultas normais são iniciadas pelo usuário. Os alertas de **Best Deals** executam uma varredura diária independente e notificam proativamente apenas usuários que ativaram `🔔 Alertas Best Deals` no menu. Ao ativar, o bot também envia as Best Deals atuais disponíveis naquele momento; a mesma tela permite desativar os alertas a qualquer momento.

Uma oferta é considerada Best Deal quando é temporariamente gratuita com preço original positivo, ou quando tem desconto de pelo menos `BEST_DEALS_MIN_DISCOUNT` e preço final de até `BEST_DEALS_MAX_PRICE`. Jogos permanentemente gratuitos não são classificados como promoções gratuitas.

Assinaturas, data da última varredura bem-sucedida e ofertas notificadas são armazenadas em `data/steam_deals_bot.sqlite3`. Uma oferta com o mesmo app, preço final e desconto não é reenviada; uma alteração nesses valores pode gerar um novo alerta. Se o bot estiver offline no horário configurado, a varredura é recuperada no máximo uma vez para o dia atual.

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
- Alertas são opt-in e podem ser desativados pelo próprio usuário.
- O banco SQLite armazena somente dados de assinatura e histórico de ofertas; tokens permanecem no `.env` e fora do Git.

## Roadmap

- [ ] Watchlist persistente.
- [x] Alertas globais de Best Deals.
- [ ] Alertas personalizados por jogo ou preço.
- [ ] Histórico de preços.
- [ ] Persistência do cache.
- [ ] Webhook como alternativa futura ao long polling.
