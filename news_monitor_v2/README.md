# Monitor de Notícias V2

Sistema de monitoramento de notícias em tempo real (em desenvolvimento).  
Desenvolvido em pasta separada para não afetar o monitor atual.

## Estrutura

```
news_monitor_v2/
├── config/          # Configurações (settings, categorias_excluidas)
├── scrapers/        # Scrapers modulares (futuro)
├── classificador/   # Classificação por temas (futuro)
├── database/        # Banco de dados (futuro)
├── email_service/   # Email matinal (futuro)
├── dashboard/       # Dashboard Streamlit (futuro)
├── scheduler/       # Agendamento (futuro)
├── logs/            # Logs de execução
├── tests/           # Testes e validação dos scrapers
│   ├── run_test_scraper.py   # Testa uma fonte por vez
│   ├── analise_cobertura.py  # Analisa relatórios gerados
│   └── output/               # Saída dos testes
└── requirements.txt
```

## Fase atual: Validação dos scrapers existentes

Antes de expandir para novas fontes (Metrópoles, G1, CNN), estamos validando os 4 scrapers atuais (Valor, Estadão, Folha, O Globo).

### Como testar

1. Instale as dependências do projeto principal (Brasil/News):
   ```bash
   cd r:\Economics\Ealmeida\Brasil\News
   pip install -r requirements.txt
   ```

2. Rode o teste de uma fonte:
   ```bash
   cd news_monitor_v2\tests
   python run_test_scraper.py valor
   ```

3. Veja o relatório no console e em `tests/output/`.

4. Analise cobertura de vários testes:
   ```bash
   python analise_cobertura.py
   ```

Ver `tests/README.md` para mais detalhes.
