# Mapeamento dos sites – o que fazemos hoje

Documento de referência para revisão. Para cada site: **onde coletamos**, **o que extraímos**, **como paginamos** e **possíveis gaps**. Você pode ir dizendo o que quer melhorar; depois testamos cada um e só então otimizamos.

---

## 1. Valor Econômico (valor.globo.com)

### Onde coletamos
- **URL base:** `https://valor.globo.com/ultimas-noticias/`
- **Páginas seguintes:** `https://valor.globo.com/ultimas-noticias/index/feed/pagina-2`, `pagina-3`, etc.
- Uma única seção: **“Últimas notícias”** (feed geral do Valor).

### O que extraímos por notícia
- **Título** – do link com classe `feed-post-link`
- **Link** – href do mesmo elemento
- **Categoria** – texto do `span.feed-post-metadata-section` (ex.: Empresas, Política, Finanças)
- **Data e hora** – do `span.feed-post-datetime`, no formato `DD/MM/AAAA, HH:MM`

### Como funciona a coleta
- Acessamos a página 1; depois, em loop, a página 2, 3, … até no máximo **20 páginas**.
- Em cada página: parse do HTML com BeautifulSoup, buscamos todos os `div.feed-post-body`.
- **Critérios de parada:**  
  - 3 ou mais notícias “antigas” (fora das últimas 24h) na mesma página, ou  
  - zero notícias novas na página (e já estamos na página 2+), ou  
  - chegamos na página 20.

### Filtros aplicados
- Só entram notícias com **data/hora nas últimas 24 horas**.
- Desconsideramos notícias já existentes no banco (por título/hash).
- Depois, no fluxo geral, entram as **categorias excluídas** (lista em `categorias_excluidas.txt`).

### O que NÃO fazemos hoje
- Não acessamos seções específicas (ex.: só Economia, só Política).
- Não extraímos resumo/lead da notícia.
- Qualquer notícia que não esteja no feed “últimas notícias” ou que use outro formato de HTML não é capturada.

### Possíveis pontos de melhoria (para você decidir)
- [ ] Incluir outras URLs do Valor (ex.: páginas por editoria)?
- [ ] Aumentar/diminuir o limite de 20 páginas?
- [ ] Exigir data/hora em formato explícito (hoje ignoramos itens sem `feed-post-datetime`)?
- [ ] Coletar mais algum campo (ex.: resumo)?

---

## 2. Estadão (estadao.com.br)

### Onde coletamos
- **Uma única URL:** `https://www.estadao.com.br/ultimas/`
- Página de **“Últimas”** que tem botão **“Carregar mais”** (conteúdo carregado por JavaScript).

### O que extraímos por notícia
- **Título** – atributo `title` do elemento `<a data-component-name="lista-ultimas">`
- **Link** – atributo `href` do mesmo elemento
- **Categoria** – **inferida pela URL** (não vem no HTML da lista). Mapeamento:
  - `/politica/` → Política, `/economia/` → Economia, `/esportes/` → Esportes, `/cultura/` → Cultura, `/internacional/` → Internacional, `/sustentabilidade/` → Sustentabilidade, `/educacao/` → Educação, `/saude/` → Saúde, `/brasil/` → Brasil, `/tecnologia/` → Tecnologia, `/jornal-do-carro/` → Automóveis, `/sao-paulo/` → São Paulo, `/estadao-verifica/` → Fato ou Fake, `/opiniao/` → Opinião
  - Se não bater com nenhum → **“Não especificada”**
- **Data e hora** – do `span.date` dentro do `div` pai do link, formato `DD/MM/AAAA, XhYY`.

### Como funciona a coleta
- Uma única página; em loop:
  - Fazemos parse do HTML atual.
  - Coletamos todos os `<a data-component-name="lista-ultimas">` visíveis.
  - Rolamos até o fim da página, removemos alguns banners (por JavaScript), clicamos no botão **“Carregar mais”** (`button.see-more[data-component-name='lista-ultimas']`).
  - Esperamos 2 segundos e repetimos.
- **Critérios de parada:**  
  - 3 ou mais notícias antigas (fora de 24h) na mesma “rodada”, ou  
  - 2 duplicatas consecutivas (já estavam no banco), ou  
  - 3 rodadas seguidas sem notícias novas, ou  
  - **15 cliques** em “Carregar mais” (limite de segurança).

### Filtros aplicados
- Só notícias nas **últimas 24 horas** (usando data do `span.date`).
- Duplicatas por título no banco.
- Depois, categorias excluídas no fluxo geral.

### O que NÃO fazemos hoje
- Não acessamos páginas por editoria (ex.: só economia, só política).
- Categoria vem só da URL; se a URL mudar ou tiver um formato novo, cai em “Não especificada”.
- Se o botão “Carregar mais” mudar de seletor ou nome, o script para de carregar mais.

### Possíveis pontos de melhoria
- [ ] Aumentar/diminuir o limite de 15 cliques?
- [ ] Tratar outros formatos de data no `span.date`?
- [ ] Incluir mais caminhos de URL no mapeamento de categorias?
- [ ] Coletar categoria de outro elemento na página (se existir)?
- [ ] Extrair resumo, se aparecer na lista?

---

## 3. Folha de S.Paulo (folha.uol.com.br)

### Onde coletamos
- **Uma única URL:** `https://www1.folha.uol.com.br/ultimas-noticias/`
- Página **“Últimas notícias”** com botão **“Ver mais”**.

### O que extraímos por notícia
- **Título** – para a manchete principal: `h2.c-main-headline__title` dentro de `a.c-main-headline__url`; para as demais: `h2.c-headline__title` dentro de links cujo `href` contém `folha.uol.com.br/... .shtml`
- **Link** – href do respectivo link
- **Categoria** – **inferida pela URL**: primeiro segmento após `folha.uol.com.br/` (ex.: `poder`, `mercado`). Mapeamento:
  - poder→Política, mercado→Economia, cotidiano→Cotidiano, mundo→Mundo, esporte→Esporte, ilustrada→Cultura, f5→Entretenimento, ambiente→Ambiente, ciencia→Ciência, equilibrioesaude→Saúde, educacao→Educação, tecnologia→Tecnologia
  - Outros segmentos viram nome “bonito” (ex.: título com primeiras letras maiúsculas); se não der match → **“Não especificada”**
- **Data e hora** – de `time.c-headline__dateline` (ou `c-main-headline` para a principal), formato **“DD.mes.AAAA às HhMM”** (mês em português abreviado: jan, fev, abr, etc.). Há normalização de encoding (ex.: Ã s → às).

### Como funciona a coleta
- **Primeira iteração:** extraímos a **notícia principal** (uma) do bloco `c-main-headline__url` + `c-main-headline__title` + `time`.
- Em todas as iterações: buscamos todos os links que tenham `folha.uol.com.br/... .shtml` e, dentro deles, `h2.c-headline__title` e `time.c-headline__dateline`.
- Em seguida: rolar até o fim, remover alguns banners por JavaScript, clicar em **“Ver mais”** (`button.c-button--expand[data-pagination-trigger]`), esperar 3 segundos, repetir.
- **Critérios de parada:**  
  - 5 ou mais notícias antigas na mesma rodada, ou  
  - 2 duplicatas consecutivas, ou  
  - 3 rodadas sem notícias novas, ou  
  - **10 cliques** em “Ver mais”.

### Filtros aplicados
- Apenas notícias nas **últimas 24 horas**.
- Duplicatas no banco.
- Categorias excluídas no fluxo geral.

### O que NÃO fazemos hoje
- Não acessamos seções específicas da Folha (só “últimas notícias”).
- Notícias sem `time.c-headline__dateline` (ou com formato de data diferente) são ignoradas.
- Qualquer URL que não termine em `.shtml` não entra no critério do regex de link.

### Possíveis pontos de melhoria
- [ ] Aumentar/diminuir o limite de 10 cliques?
- [ ] Incluir outros padrões de URL (ex.: sem .shtml)?
- [ ] Tratar mais formatos de data ou encoding?
- [ ] Mapear mais segmentos de URL para categorias?
- [ ] Garantir que a manchete principal não seja duplicada nas secundárias?

---

## 4. O Globo (oglobo.globo.com)

### Onde coletamos
- **URL base:** `https://oglobo.globo.com/ultimas-noticias/`
- **Páginas seguintes:** `https://oglobo.globo.com/ultimas-noticias/index/feed/pagina-2.ghtml`, `pagina-3.ghtml`, etc.
- Seção **“Últimas notícias”** do O Globo.

### O que extraímos por notícia
- **Título** – do link com classe `feed-post-link`
- **Link** – href do mesmo elemento
- **Categoria** – texto do `span.feed-post-metadata-section` (como no Valor)
- **Data e hora** – **não vêm em data absoluta**: vem texto **relativo** no `span.feed-post-datetime` (ex.: “há 5 minutos”, “há 2 horas”). Convertemos para data/hora absoluta com a função `calcular_tempo_absoluto`:
  - “agora” / “poucos instantes” → agora
  - “há N minutos” → agora − N minutos
  - “há N horas” → agora − N horas
  - Só aceitamos se a data calculada for **hoje**; caso contrário descartamos (retorno None).

### Como funciona a coleta
- Igual ao Valor: páginas 1, 2, 3, … até **20 páginas**.
- Em cada página: `div.feed-post-body`, depois título, link, categoria, tempo relativo → conversão para data/hora.
- **Critérios de parada:**  
  - 3 ou mais notícias antigas na página, ou  
  - 2 duplicatas consecutivas, ou  
  - zero novas na página (e página > 1), ou  
  - página 20.

### Filtros aplicados
- Só notícias que, após conversão, caem nas **últimas 24 horas** e na **data de hoje**.
- Duplicatas no banco.
- Categorias excluídas no fluxo geral.

### O que NÃO fazemos hoje
- Não tratamos textos como “ontem” ou “há 1 dia” (retornamos None e a notícia é ignorada).
- Só “minutos” e “horas” são convertidos; qualquer outro formato é descartado.
- Não acessamos outras seções do O Globo (só “últimas notícias”).

### Possíveis pontos de melhoria
- [ ] Tratar “ontem” e “há N dias” para incluir notícias do dia anterior dentro de 24h?
- [ ] Aumentar/diminuir o limite de 20 páginas?
- [ ] Incluir outras seções ou URLs do Globo?
- [ ] Extrair resumo, se existir no bloco da notícia?

---

## 5. CNN Brasil (cnnbrasil.com.br)

### Onde coletamos
- **URL base:** `https://www.cnnbrasil.com.br/ultimas-noticias/`
- **Páginas seguintes:** `https://www.cnnbrasil.com.br/ultimas-noticias/pagina/2/`, `pagina/3/`, etc.
- Seção **"Últimas Notícias"** da CNN Brasil.

### O que extraímos por notícia
- **Título** – do `<h2 class="text-xl font-bold">` dentro do `<a>` da notícia
- **Link** – `href` do mesmo `<a>`
- **Categoria** – texto do `span.text-base.font-medium.text-gray-400` (ex.: Política, Mercado, Entretenimento)
- **Data e hora** – no bloco da notícia, formato **DD/MM/YYYY | HH:MM**

### Como funciona a coleta
- Paginação por **URL**: página 1 = base, página 2 = `.../pagina/2/`, etc., até **20 páginas**.
- Em cada página: parse com BeautifulSoup; busca `<a>` que contêm `<h2 class="text-xl font-bold">`; sobe ao container (li/article/div) para pegar categoria e data.
- **Critérios de parada:** página sem notícias novas (e já na página 2+), ou 20 páginas.

### Filtros aplicados
- Só notícias nas **últimas 24 horas** (data/hora no formato DD/MM/YYYY | HH:MM).
- Categorias excluídas da coleta: Esportes, BBB, Entretenimento, Carnaval, Celebridades, Música, Cinema, Televisão, Streaming, Shows, Horóscopo, Viagem & Gastronomia, etc.

### O que NÃO fazemos hoje
- Não acessamos outras seções (só "últimas notícias").
- Sem resumo na lista; classificação apenas pelo título.

### Possíveis pontos de melhoria
- [ ] Ajustar lista de categorias excluídas?
- [ ] Coletar resumo se a CNN passar a exibir na listagem?

---

## Resumo rápido

| Site      | Onde              | Paginação      | Limite   | Categoria        | Data/hora              |
|----------|-------------------|----------------|----------|------------------|-------------------------|
| Valor    | /ultimas-noticias | URL por página | 20 págs  | Do HTML          | DD/MM/AAAA, HH:MM       |
| Estadão  | /ultimas/         | Botão “Carregar mais” | 15 cliques | Pela URL   | DD/MM/AAAA, XhYY        |
| Folha    | /ultimas-noticias | Botão “Ver mais”      | 10 cliques | Pela URL   | DD.mes.AAAA às HhMM     |
| O Globo  | /ultimas-noticias | URL por página | 20 págs  | Do HTML          | Relativo (há N min/hora) |
| CNN Brasil | /ultimas-noticias | URL por página | 20 págs  | Do HTML          | DD/MM/AAAA \| HH:MM       |

---

## Próximos passos (como combinado)

1. **Hoje:** você revisa este mapeamento e diz o que quer mudar ou melhorar em cada site (mais seções, mais campos, outros limites, tratamento de data, etc.).
2. **Depois:** com a ideia completa por site, testamos cada scraper separadamente para ver se está funcionando como esperado.
3. **Em seguida:** otimizamos cada um com base nos testes e nas melhorias que você indicou.

Quando quiser, pode ir site por site dizendo: “no Valor quero X”, “no Estadão quero Y”, etc., e vamos anotando e implementando.
