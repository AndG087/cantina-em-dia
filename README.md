# Cantina em Dia

Sistema local de gestão da cantina do Senai em Paulista, desenvolvido por etapas com Python, React e PostgreSQL.

## O que funciona nesta versão (0.5.0)

- Painel com vendas, despesas, responsável pelo caixa, estoque e pendências registrados, e a situação das cinco rotinas de acompanhamento exigidas pela gestão.
- Calendário da escola: cursos e turmas em andamento, feriados, recessos e paralisações com efeito previsto na cantina, e registro de cada averiguação.
- Conferência diária de aberturas e fechamentos do caixa, com apontamentos automáticos e registro da conferência.
- Conferência das notas recebidas (valor da nota × itens, custo × estimado, pedido × recebido) e folha de inventário com vários itens.
- Identificação de gastos fora do padrão, com explicação registrada para cada alerta.
- Relatório semanal imprimível, com texto pronto para WhatsApp, download em Markdown e histórico das versões entregues.
- Equipe, escalas semanais, substituições pontuais, feriados e confirmação de responsabilidade.
- Estoque por produto/insumo, lotes, validade, entradas, perdas, estornos e inventários.
- Fornecedores, pedidos, aprovação, recebimento parcial e reembolsos vinculados às compras.
- Abertura, passagem com contagem, fechamento e reabertura do último caixa para correção.
- Vendas por item, pagamentos divididos, cancelamentos, devolução física e registro do dinheiro devolvido.
- Despesas, pagamentos e conciliação de recebimentos digitais com taxas.
- Fichas técnicas versionadas, rendimento, produção medida/estimada e pesagem de porções prontas.
- Relatórios mensais, exportação CSV, metas por base acordada e apurações preservadas.
- Importação de CSV com seleção de colunas, prévia, validação transacional e proteção contra duplicidade.
- Comprovantes em PDF, imagem, texto ou áudio, com caixa de recebidos, vinculação, verificação de integridade e arquivamento reversível.
- Backup dos registros e anexos, cópia diária na inicialização, teste de recuperação e restauração em outro banco.
- Consulta dos documentos e configurações persistidas no PostgreSQL.
- Inicialização local do banco, migrações, API e interface por um comando.

As etapas 1 a 8 estão implementadas, incluindo CSV, anexos e backup/restauração, além da rotina de acompanhamento (etapa 9). A validação com dados reais e as regras pendentes da família continuam necessárias. Nenhum dado de demonstração foi inserido no banco operacional.

O desenvolvimento foi retomado a pedido do usuário. Consulte `ESTADO_DO_PROJETO.md` para acompanhar as entregas e verificações.

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

Isso mantém o banco fora do OneDrive. Remover o repositório não remove esse diretório. Preserve o `.env`, pois a senha existente precisa corresponder ao banco já criado. Para uma cópia consistente, use **Backup e recuperação**, conforme o procedimento abaixo.

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

O build executa TypeScript e Vite. Os 65 testes atuais usam PostgreSQL de verdade em um banco **separado**, `cantina_em_dia_test`. Cobrem persistência, validação, escala, estoque, compras, financeiro, produção, relatórios, importação, anexos, recuperação de backup e as rotinas de acompanhamento. Os testes de recuperação criam e removem bancos isolados com nomes gerados. Em PostgreSQL externo, o usuário precisa poder criar esses bancos dedicados.

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

- [Guia prático para administrar a cantina](GUIA_PRATICO_DA_CANTINA.md)
- [Mapa das funcionalidades](MAPA_FUNCIONALIDADES.md)
- [Estado atual e próxima etapa](ESTADO_DO_PROJETO.md)
- [Projeto de gestão](PROJETO_GESTAO_CANTINA.md)
- [Especificação do sistema](ESPECIFICACAO_SISTEMA_PYTHON.md)
- [Perguntas para o pai](PERGUNTAS_PARA_O_PAI.md)
- [Prompt de desenvolvimento por etapas](PROMPT_DESENVOLVIMENTO.md)

## Comprovantes e anexos

Abra **Comprovantes e anexos** para guardar arquivos de até 8 MB. É possível recebê-los na caixa de entrada, sem lançar uma despesa, e vinculá-los depois a uma compra, pagamento/reembolso, venda, movimento, inventário, produção, caixa ou funcionário/treinamento.

Arquivos aceitos: PDF, PNG, JPEG, WebP, texto UTF-8, MP3, M4A, OGG/Opus e WAV. O conteúdo precisa corresponder ao formato. Os arquivos ficam em `%LOCALAPPDATA%\CantinaEmDia\attachments`, fora do repositório. Não há leitura automática das conversas do WhatsApp: salve o comprovante, mensagem ou captura e anexe pelo formulário.

O sistema verifica o hash antes de entregar o arquivo, rejeita duplicatas no mesmo registro e permite arquivar/recuperar sem apagar o documento físico. Vinculações e mudanças ficam no histórico. O armazenamento de arquivos pode ser configurado por `CANTINA_DATA_DIR`; isso não muda o diretório do PostgreSQL.

## Backup e recuperação

Abra **Backup e recuperação**. **Criar backup agora** guarda um ZIP com o retrato dos registros e os anexos, inclusive arquivados. A leitura do banco usa uma transação consistente; os arquivos são conferidos por tamanho e SHA-256. Um anexo ausente ou alterado impede a criação da cópia.

Ao executar `npm.cmd start`, o inicializador cria uma cópia na primeira inicialização de cada dia. Isso depende de iniciar o aplicativo: não há serviço agendado com o computador desligado nem cópias contínuas durante o dia. Para desativar, configure `CANTINA_AUTO_BACKUP=0` no `.env`. Uma falha é informada no terminal e a aplicação permanece disponível para corrigir a pendência.

As cópias ficam em `%LOCALAPPDATA%\CantinaEmDia\backups`, ou na pasta `backups` dentro de `CANTINA_DATA_DIR`, se configurado. **Baixar .zip** permite guardar uma cópia em outro dispositivo/local. O ZIP contém dados privados e não é criptografado. Não inclui senha, `.env`, código do programa ou os arquivos de outros backups. Preserve separadamente o código correspondente e as configurações necessárias à reinstalação.

1. Clique em **Testar restauração**. O sistema cria um banco temporário, aplica as migrações, restaura e compara todos os registros, confere os anexos e remove esse banco ao concluir. A data de verificação só é registrada em caso de sucesso.
2. Para recuperar dados, use **Restaurar uma cópia em outro banco**. Ela cria `cantina_restore_<identificador>`, confere os registros e recupera arquivos ausentes. Não substitui o banco em uso nem um anexo local diferente com o mesmo identificador.
3. Para passar a usar a cópia, encerre o aplicativo no terminal de origem, troque **somente o nome do banco** em `DATABASE_URL`, no `.env`, pelo nome apresentado e execute `npm.cmd start`. Preserve usuário, senha, endereço e porta. O banco anterior continua disponível.
4. Se o histórico de backups foi perdido, use **Importar uma cópia guardada fora do aplicativo**, selecionando seu ZIP. A importação valida e cadastra a cópia; não restaura automaticamente.

O formato é um backup lógico próprio da aplicação, não um arquivo `pg_dump`. Exige a **mesma revisão de estrutura** do aplicativo para recuperar; consulte `manifest.json` dentro do ZIP para ver revisão e versão. Limites: ZIP de 512 MB, registros JSON de 64 MB, conteúdo total expandido de 1 GB e até 20.000 anexos de 8 MB cada, respeitando o limite total. O usuário PostgreSQL precisa poder criar bancos; o sistema não altera permissões.

### Recuperação pelo terminal

Com o PostgreSQL em execução, é possível usar a recuperação mesmo sem a interface. Para iniciar somente o PostgreSQL gerenciado, execute `node scripts/database.mjs` na raiz e mantenha esse terminal aberto. Em outro terminal:

```powershell
cd C:\dev\cantina-em-dia\backend
..\.venv\Scripts\python.exe -m app.backup_cli create
..\.venv\Scripts\python.exe -m app.backup_cli verify --file "C:\Caminho\copia.zip"
..\.venv\Scripts\python.exe -m app.backup_cli restore --file "C:\Caminho\copia.zip"
```

`verify` remove a cópia temporária após a conferência. `restore` preserva um banco novo e informa seu nome; a troca da configuração continua manual. Em instalação nova, execute o setup e as migrações antes da recuperação. Se a URL estiver apontando para uma cópia que não existe mais, ajuste temporariamente apenas o nome do banco para `cantina_em_dia` antes de iniciar o PostgreSQL gerenciado.

Continuidade pendente: validação com os relatórios reais da Stone, custos e preços da operação e regras ainda não informadas pela família.

## Preços com vigência

Em **Preços e custos**, registre a nova tabela com preço, data e hora de início, indicação de preço fixado pela licitação, documento de origem e justificativa. Datas futuras são permitidas. A venda é conferida pela data da ocorrência, inclusive na importação CSV por produto. Regras que alcançariam vendas já registradas são bloqueadas. Uma regra sem vendas posteriores pode ser cancelada com justificativa; o histórico permanece. Use Comprovantes e anexos para guardar o documento da tabela.

## Retificação de custos

Em **Preços e custos**, prepare a correção de um lote de entrada e confira as vendas e produções afetadas antes de confirmar. Os relatórios consultados usam o custo gerencial corrigido; os valores originais e apurações guardadas ficam preservados. Lotes já consumidos são elegíveis. Para produtos produzidos na cantina, corrija os ingredientes/embalagens de origem. Uma nova movimentação ou revisão exige refazer a prévia. A operação não altera notas, despesas, pagamentos, quantidade ou custo padrão do cadastro. Correções financeiras de compras liquidadas ainda não têm um fluxo completo de ajustes. Registre a pendência e confira separadamente.

A estrutura atual é `0014_rotina_acompanhamento`. Como os backups exigem a mesma revisão, preserve o código correspondente às cópias antigas e crie/teste uma nova cópia depois de atualizar. O uso permanece exclusivamente local, conforme confirmado pelo usuário.

## Rotina de acompanhamento

As cinco atividades exigidas pela gestão aparecem no topo da **Visão geral**, cada uma com situação (em dia, atenção ou pendente) e atalho:

| Atividade | Onde fazer | O que o sistema confere |
|---|---|---|
| Calendário da escola | **Calendário da escola** | Cursos em andamento por turno, feriados, recessos e paralisações; averiguação com a escola a cada 7 dias. Eventos com efeito "cantina fechada" dispensam abertura de caixa e responsável. |
| Compras, notas e inventário | **Compras e reembolsos** e **Estoque** | Valor impresso na nota × soma dos itens (diferença exige explicação), custo 10% ou mais acima do estimado no pedido, itens que faltam receber e contagem física nos últimos 7 dias. A folha de inventário grava vários itens de uma vez, ou nenhum. |
| Caixa diário | **Caixa** | Dia útil sem abertura, troco de abertura diferente do contado no fechamento anterior, diferenças de contagem e caixa sem fechamento. A conferência registrada fica desatualizada se os registros mudarem depois. |
| Relatório semanal | **Relatório semanal** | Semana de segunda a domingo comparada à anterior, com caixa, compras, estoque, gastos e calendário. Imprimir/PDF, copiar texto para WhatsApp, baixar .md e guardar a versão entregue. |
| Gastos fora do padrão | **Financeiro** | Despesa 50% acima da mediana da categoria, possível duplicidade (mesmo favorecido e valor em até 7 dias), categoria 30% acima dos períodos anteriores e custo de compra 15% acima das compras recentes do item. |

Os critérios são fixos nesta versão e aparecem na tela. Um alerta indica um ponto a conferir, não prova de erro ou desvio. Com pouco histórico, algumas comparações ainda não são feitas; a tela informa quais categorias estão nessa situação.

## Aprender a administrar e usar o sistema

Abra **Documentos** e comece pelo **Guia prático da cantina**. Ele reúne a implantação, rotina de duas a três horas à tarde, mensagens para a equipe, conferência de dinheiro e recebimentos, compras, estoque, marmitas, equipe e fechamento mensal, com exemplos fictícios e plano dos primeiros trinta dias. O **Mapa das funcionalidades** explica cada módulo, seus dados de entrada, resultados, regras, limites e conexões. Seus atalhos abrem os módulos dentro da aplicação. Ambos podem ser baixados em Markdown; há também a opção de imprimir ou salvar PDF pelo navegador. Tabelas e listas de conferência são exibidas na leitura.
