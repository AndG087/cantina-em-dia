# Cantina em Dia

Sistema local de gestão da cantina do Senai em Paulista, desenvolvido por etapas com Python, React e PostgreSQL.

## O que funciona nesta versão (0.2.0)

- Painel com vendas, despesas, responsável pelo caixa, estoque e pendências registrados.
- Equipe, escalas semanais, substituições pontuais, feriados e confirmação de responsabilidade.
- Estoque por produto/insumo, lotes, validade, entradas, perdas, estornos e inventários.
- Fornecedores, pedidos, aprovação, recebimento parcial e reembolsos vinculados às compras.
- Abertura, passagem com contagem, fechamento e reabertura do último caixa para correção.
- Vendas por item, pagamentos divididos, cancelamentos, devolução física e registro do dinheiro devolvido.
- Despesas, pagamentos e conciliação de recebimentos digitais com taxas.
- Fichas técnicas versionadas, rendimento, produção medida/estimada e pesagem de porções prontas.
- Relatórios mensais, exportação CSV, metas por base acordada e apurações preservadas.
- Importação de CSV com seleção de colunas, prévia, validação transacional e proteção contra duplicidade.
- Consulta dos documentos e configurações persistidas no PostgreSQL.
- Inicialização local do banco, migrações, API e interface por um comando.

As etapas 1 a 7 estão implementadas. A etapa 8 tem a **parte de importação CSV concluída**; anexos, backup e restauração ainda estão pendentes. Há estrutura de tabelas preparada para essa continuidade, mas ainda não há telas ou operações de backup/anexos. Nenhum dado de demonstração foi inserido no banco operacional.

O desenvolvimento foi interrompido a pedido do usuário após o commit da importação. Consulte `ESTADO_DO_PROJETO.md` antes de continuar.

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

Os registros operacionais e suas trilhas de alteração ficam no PostgreSQL. A aplicação atende apenas em `127.0.0.1`, para uso pessoal neste computador. Acesso por outros dispositivos e autenticação ainda não fazem parte desta versão.

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

O build executa TypeScript e Vite. Os 33 testes atuais usam PostgreSQL de verdade em um banco **separado**, `cantina_em_dia_test`. Cobrem persistência, validação, escala, estoque, compras, financeiro, produção, relatórios e importação. Em PostgreSQL externo, o usuário do teste precisa poder criar esse banco dedicado.

As portas padrão são 8000 (API) e 5173 (interface). Se outra instância estiver usando essas portas, encerre-a no terminal em que foi aberta ou configure `API_PORT` e `WEB_PORT` no `.env`. O inicializador não encerra processos alheios.

## Uso e regras importantes

1. Cadastre a equipe e a escala. A pessoa prevista pelo relógio e a pessoa que confirmou assumir o caixa são informações diferentes.
2. Cadastre produtos, ingredientes e embalagens, respeitando as unidades. Faça a contagem inicial acompanhada e registre os custos conhecidos.
3. Nas compras, crie e aprove o pedido e registre o recebimento com nota e lotes. Reembolso à equipe liquida a mesma despesa, sem criar outra compra.
4. Abra o caixa com o troco contado. Registre vendas, despesas em espécie, retiradas, passagens e fechamento.
5. Para marmitas, registre a produção: ela consome ingredientes e gera produto pronto. A venda baixa somente o produto pronto. Consumo estimado permanece identificado como estimativa.
6. Concilie cartões e Pix com os créditos efetivos. Recebimento não é uma segunda venda.
7. Configure a meta apenas depois de confirmar o acordo. Sem valor/base definidos, a parcela variável permanece pendente. Apurações guardadas preservam o retrato usado na conferência.

Os relatórios são gerenciais e usam os registros disponíveis. Mercadorias recebidas não são descontadas novamente como despesa operacional: o custo é reconhecido conforme venda, perda ou consumo. O resultado e a meta sobre resultado ficam pendentes quando há custos não confirmados, consumo estimado ou conciliação incompleta identificados pelo sistema. Registrar apenas parte da operação não comprova lucro completo.

## Importação de CSV

Abra **Importação CSV**, escolha o tipo e carregue o arquivo. Arquivos de até 2 MB e 2.000 linhas são aceitos. Selecione UTF-8 ou Windows-1252 conforme a origem, confira o mapeamento, valide a prévia e só então importe.

Tipos disponíveis:

- Cadastros de produtos/insumos.
- Resumos financeiros de vendas, sem baixa de estoque e sem inventar custos.
- Vendas por produto, com SKU, quantidade e preço unitário, com baixa de estoque.
- Recebimentos digitais vinculados à referência externa da venda.
- Saldos iniciais por lote.

A tela oferece modelos de cabeçalho. As referências externas devem ser estáveis e únicas. Uma linha de venda por produto representa um registro desse produto; relatórios por pedido com vários itens precisam ser adaptados ao modelo antes da importação. Datas sem fuso são interpretadas em Brasília; registros em dinheiro precisam estar dentro do caixa selecionado. Validades podem ser futuras.

A prévia não grava lançamentos. Ao confirmar, o lote inteiro é validado novamente e salvo de forma atômica. Arquivos ou referências já importados são rejeitados. O conteúdo original fica preservado no histórico, disponível para download como texto. A estrutura exportada pela Stone ainda precisa ser conferida com o relatório real; não há integração automática com a maquininha.

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

Continuidade pendente: anexos de comprovantes, backup/restauração verificados e validação com os relatórios reais da Stone e as regras ainda não informadas pela família.
