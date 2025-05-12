# Monitor de Notícias

Um scraper que extrai as últimas notícias de fontes como o Valor Econômico e o Estadão, exibindo-as em uma tabela HTML organizada.

## Funcionalidades

- Extrai notícias de múltiplas fontes:
  - Valor Econômico (https://valor.globo.com/ultimas-noticias/)
  - Estadão (https://www.estadao.com.br/ultimas/)
- Utiliza o Microsoft Edge para acessar os sites e garantir a obtenção correta dos dados
- Extrai todas as notícias disponíveis utilizando as mecânicas específicas de cada site:
  - Navegação por páginas no Valor Econômico
  - Botão "Carregar mais notícias" no Estadão
- Organiza as notícias por data e hora (mais recentes primeiro)
- Exibe título, categoria, fonte, data, hora e link para a notícia original
- Gera uma página HTML com layout limpo e responsivo
- Permite filtrar notícias por fonte
- Também salva os dados em formato JSON para uso em outras aplicações
- Suporte para modo automático com atualização a cada 1 minuto
- Servidor web integrado para acesso remoto via celular ou qualquer dispositivo na rede

## Estrutura do Projeto

- `scraper.py`: Contém a lógica de extração das notícias usando Selenium com Microsoft Edge
- `app.py`: Script simplificado para extrair notícias e abrir o resultado no navegador
- `main.py`: Interface interativa com menu para todas as funcionalidades
- `monitor_automatico.bat`: Script batch para iniciar o modo automático facilmente (Windows)
- `app_auto.bat`: Script batch para iniciar a versão simplificada em modo automático (Windows)
- `app_auto_loop.bat`: Script batch para atualizar automaticamente o GitHub enquanto roda o servidor web
- `servidor_web.bat`: Script batch para iniciar o servidor web com atualização automática (Windows)
- `requirements.txt`: Lista de dependências do projeto

## Requisitos

- Python 3.8+
- Microsoft Edge (navegador)
- Dependências listadas em `requirements.txt`:
  - requests
  - beautifulsoup4
  - pandas
  - lxml
  - selenium
  - webdriver-manager
  - flask (para servidor web)

## Instalação

1. Certifique-se de ter o Python instalado. Caso não tenha, baixe-o em [python.org](https://www.python.org/downloads/)

2. Clone ou baixe este repositório

3. Instale as dependências:

```bash
# Usando pip (Windows)
py -m pip install -r requirements.txt

# Linux/macOS
pip3 install -r requirements.txt
```

## Uso

### Modo Interativo

Execute o script principal para acessar o menu interativo:

```bash
# Windows
py main.py

# Linux/macOS
python3 main.py
```

O menu oferece as seguintes opções:
1. Extrair notícias
2. Abrir monitor no navegador
3. Iniciar modo automático (atualizar a cada 1 minuto)
0. Sair

### Linha de Comando

Você também pode usar argumentos na linha de comando:

```bash
# Extrair notícias
py main.py --extrair

# Abrir monitor no navegador
py main.py --monitor

# Iniciar modo automático (atualizar a cada 1 minuto)
py main.py --auto

# Definir intervalo personalizado para o modo automático (em segundos)
py main.py --auto --intervalo 120  # Atualiza a cada 2 minutos
```

### Servidor Web (acesso pelo celular)

Para acessar o monitor pelo celular ou qualquer dispositivo na mesma rede:

```bash
# Iniciar servidor web
py app.py --web

# Iniciar servidor web com atualização automática
py app.py --web --auto

# Definir porta personalizada (padrão: 5000)
py app.py --web --porta 8080
```

O script exibirá os endereços para acessar o monitor:
- `http://localhost:5000` (acesso local)
- `http://SEU_IP_LOCAL:5000` (acesso na rede)

Para acessar pelo celular, conecte-se à mesma rede WiFi do computador e abra o endereço `http://SEU_IP_LOCAL:5000` no navegador.

### Arquivos Batch (Windows)

Para iniciar rapidamente os diferentes modos, execute os arquivos batch:

```
# Modo automático com interface completa
monitor_automatico.bat

# Modo automático com versão simplificada
app_auto.bat

# Servidor web com atualização automática
servidor_web.bat
```

### Execução Simplificada

Para apenas extrair notícias e abrir o resultado:

```bash
py app.py
```

## Arquivos Gerados

- `monitor_noticias.html`: Tabela com as notícias extraídas de todas as fontes
- `index.html`: Cópia do arquivo HTML para publicação no GitHub
- `noticias_valor.json`: Dados das notícias do Valor Econômico em formato JSON
- `noticias_estadao.json`: Dados das notícias do Estadão em formato JSON
- `noticias_combinadas.json`: Dados combinados de todas as fontes em formato JSON

## Personalização

Você pode modificar os arquivos de código para ajustar:

- A aparência da página HTML
- O número máximo de páginas a serem processadas
- As configurações do navegador Edge
- O intervalo de atualização no modo automático
- A porta do servidor web

## Limitações

- O script depende da estrutura atual do site Valor Econômico. Mudanças no layout do site podem quebrar o scraper.
- O site pode limitar o número de requisições consecutivas. O script inclui pausas para evitar sobrecarregar o servidor.
- Para acesso pelo celular, é necessário que ambos os dispositivos estejam na mesma rede WiFi.

## Próximos passos

- Adicionar suporte para outros sites de notícias
- Implementar filtros por fonte e categoria
- Adicionar suporte para outros navegadores além do Edge
- Implementar uma interface web mais interativa

## Licença

Este projeto é distribuído sob a licença MIT. 