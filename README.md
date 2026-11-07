# Cantina em Dia

Sistema local de gestão da cantina do Senai em Paulista, desenvolvido por etapas com Python, React e PostgreSQL.

## O que funciona nesta versão

- Tela inicial responsiva com as informações que precisamos levantar.
- Plano de implantação em oito etapas.
- Leitura e download dos quatro documentos de planejamento dentro do aplicativo.
- Configurações básicas persistidas no PostgreSQL.
- Verificações separadas da API e do banco, incluindo a migração aplicada.
- Inicialização do PostgreSQL local, migrações, API e frontend por um comando.

Esta é a **etapa 1: fundação**. Caixa, estoque, equipe, compras, produção e meta ainda serão implementados. Os indicadores operacionais aparecem como pendentes. Nenhum valor fictício é apresentado como venda ou saldo real.

## Requisitos no Windows

- Windows x64.
- Python 3.12 ou superior, disponível pelo comando `python`.
- Node.js 22.12 ou superior e npm.
- Internet na instalação inicial das dependências; a aplicação usa fontes locais e funciona sem recursos externos de interface.

O inicializador inclui binários PostgreSQL 17 distribuídos pelo pacote `@embedded-postgres/windows-x64`. Não precisa instalar Docker nem cadastrar um serviço do Windows. Uma instalação PostgreSQL existente também pode ser configurada.

## Instalar e iniciar

No PowerShell, dentro da pasta do repositório:

```powershell
cd C:\dev\cantina-em-dia
npm.cmd run setup
npm.cmd start
```

Nesta máquina, as dependências já foram instaladas durante a preparação. Para abrir novamente, basta `npm.cmd start`.

- Aplicação: http://127.0.0.1:5173
- Documentação da API: http://127.0.0.1:8000/docs
- Saúde do processo: http://127.0.0.1:8000/api/health
- Conexão real e migração: http://127.0.0.1:8000/api/health/database

Mantenha o terminal aberto. **Ctrl+C** encerra os processos iniciados por essa sessão, inclusive o PostgreSQL quando ele foi iniciado pelo comando. Portas ocupadas geram uma mensagem; o inicializador não encerra serviços de outros projetos.

`npm.cmd` evita depender da política de execução de scripts PowerShell. Também é possível executar os comandos pelo terminal do VS Code.

## Onde ficam os dados

Na primeira execução, o inicializador gera uma senha aleatória em `.env`, arquivo ignorado pelo Git. Os arquivos ativos do PostgreSQL ficam em:

```text
%LOCALAPPDATA%\CantinaEmDia\postgres
```

Isso mantém o banco fora do OneDrive. Remover o repositório não remove esse diretório. Preserve o `.env`, pois a senha existente precisa corresponder ao banco já criado. Não copie os arquivos de um PostgreSQL ativo como se fossem um backup consistente; o fluxo de backup e restauração será desenvolvido antes do uso operacional.

Por enquanto, só há uma tabela de configuração e a tabela de controle das migrações. A aplicação atende apenas em `127.0.0.1`, para uso pessoal neste computador. Acesso por outros dispositivos e autenticação ainda não fazem parte desta versão.

## Usar um PostgreSQL já instalado

Copie `.env.example` para `.env` antes da primeira inicialização, preencha `DATABASE_URL` e mantenha `CANTINA_MANAGED_POSTGRES=0`. O banco indicado deve existir e o usuário precisa ter permissão para as migrações. O aplicativo não usa SQLite.

```text
DATABASE_URL=postgresql+psycopg://USUARIO:SENHA@127.0.0.1:5432/cantina_em_dia
CANTINA_MANAGED_POSTGRES=0
API_PORT=8000
WEB_PORT=5173
```

Caracteres especiais da senha precisam de codificação apropriada na URL. Não versione `.env` nem compartilhe sua URL de conexão.

## Validar

```powershell
npm.cmd run build
npm.cmd test
```

O build executa TypeScript e Vite. Os testes usam PostgreSQL de verdade em um banco **separado**, `cantina_em_dia_test`. O script aplica migrações nesse banco e verifica persistência, validação, indisponibilidade do banco e acesso permitido aos documentos. Em PostgreSQL externo, o usuário do teste precisa poder criar esse banco dedicado.

Para conferir migrações manualmente, com o PostgreSQL em execução:

```powershell
.\.venv\Scripts\python.exe -m alembic -c backend\alembic.ini current
.\.venv\Scripts\python.exe -m alembic -c backend\alembic.ini check
```

## Organização

```text
backend/
  app/                  # API, configurações, modelos e conexão
  migrations/           # Histórico versionado do banco
  tests/                # Testes no PostgreSQL isolado
  requirements.txt      # Dependências diretas
  requirements.lock.txt # Versões verificadas nesta etapa
frontend/
  src/                  # Interface React e estilos
scripts/                # Instalação, inicialização e testes locais
```

## Contexto para continuar

- [Estado atual e próxima etapa](ESTADO_DO_PROJETO.md)
- [Projeto de gestão](PROJETO_GESTAO_CANTINA.md)
- [Especificação do sistema](ESPECIFICACAO_SISTEMA_PYTHON.md)
- [Perguntas para o pai](PERGUNTAS_PARA_O_PAI.md)
- [Prompt de desenvolvimento por etapas](PROMPT_DESENVOLVIMENTO.md)

Próxima entrega planejada: cadastro da equipe e escalas, com responsável previsto por dia/horário, confirmação de abertura e substituição manual com histórico.
