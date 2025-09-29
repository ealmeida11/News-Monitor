# 📋 Configuração de Categorias Excluídas

## 📁 Arquivo: `categorias_excluidas.txt`

Este arquivo permite configurar facilmente quais categorias de notícias devem ser excluídas da extração.

### 🔧 Como Usar

1. **Adicionar nova categoria**: Simplesmente adicione o nome da categoria em uma nova linha
2. **Remover categoria**: Delete a linha correspondente
3. **Comentários**: Use `#` no início da linha para adicionar comentários
4. **Linhas vazias**: São ignoradas automaticamente

### 📝 Formato do Arquivo

```
# Comentários começam com #
Categoria1
Categoria2
# Outro comentário
Categoria3
```

### ✅ Exemplo de Uso

Para excluir uma nova categoria chamada "Esportes":

1. Abra o arquivo `categorias_excluidas.txt`
2. Adicione `Esportes` em uma nova linha
3. Salve o arquivo
4. Execute o script - a categoria será automaticamente excluída

### 🚫 Categorias Atualmente Excluídas

O arquivo contém **66 categorias** que são automaticamente filtradas, incluindo:

- **Categorias originais**: Ambiente, Astrologia, Blogs, etc.
- **Categorias adicionadas**: Ancelmo Gois, Automóveis, Empresas, Mundo, etc.

### 🔄 Atualização Automática

- O script carrega automaticamente as categorias do arquivo a cada execução
- Não é necessário reiniciar ou recompilar o código
- Mudanças no arquivo são aplicadas imediatamente

### ⚠️ Importante

- **Encoding**: O arquivo deve estar salvo em UTF-8
- **Nomes exatos**: Use os nomes exatos das categorias (case-sensitive)
- **Backup**: Mantenha um backup do arquivo antes de fazer mudanças grandes

### 📊 Resultado

Com as categorias atuais excluídas:
- **Total de notícias**: ~115 (vs ~269 sem filtro)
- **Redução**: ~57% das notícias são filtradas
- **Foco**: Economia, Política, Brasil e Finanças
