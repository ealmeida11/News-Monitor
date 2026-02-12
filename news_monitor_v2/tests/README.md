# Testes de Scrapers - Monitor de Notícias V2

## Objetivo

Validar que cada scraper está coletando **todas** as notícias possíveis do site, não apenas de algumas seções. Os testes rodam o scraper atual do projeto principal de forma isolada e geram relatórios para análise.

## Pré-requisitos

- Python com dependências do projeto principal instaladas (`r:\Economics\Ealmeida\Brasil\News\requirements.txt`)
- Chrome instalado (para Selenium)
- Executar a partir da pasta **Brasil/News** ou garantir que o script encontra o projeto principal

## Como rodar

### Testar uma fonte por vez

```bash
# Da pasta news_monitor_v2/tests/
python run_test_scraper.py valor
python run_test_scraper.py estadao
python run_test_scraper.py folha
python run_test_scraper.py oglobo
```

Ou da raiz do repositório:

```bash
cd news_monitor_v2/tests
python run_test_scraper.py valor
```

### Analisar cobertura

Após rodar testes, ver resumo comparativo:

```bash
python analise_cobertura.py
python analise_cobertura.py --ultimos 3
```

## Saídas

- `tests/output/test_*_YYYYMMDD_HHMMSS.json` — notícias coletadas
- `tests/output/relatorio_*_YYYYMMDD_HHMMSS.json` — relatório (total, por categoria, por hora, amostra de títulos)

## Checklist de validação (manual)

Para cada fonte, após rodar o teste:

1. Abra o site da fonte no navegador e conte quantas notícias aparecem nas últimas 24h.
2. Compare com o total do relatório.
3. Verifique se as categorias no relatório cobrem as seções que você vê no site.
4. Anote gaps (notícias visíveis no site que não aparecem no JSON) no arquivo de documentação do plano.
