# Estado do projeto

Atualizado em 7 de novembro de 2026. Repositório: `C:\dev\cantina-em-dia`. Versão local 0.3.0. Commits feitos localmente; não houve envio ao GitHub.

## Continuidade autorizada

O usuário pediu “continue”. A pausa anterior foi encerrada e o desenvolvimento foi retomado, mantendo um commit por etapa validada. Anexos (8b) e backup/restauração (8c) estão concluídos. Os módulos das etapas 1 a 8 estão disponíveis; a próxima frente é validar o fluxo com as informações reais e resolver as regras de negócio ainda abertas.

## Entregas registradas

| Etapa | Commit | Entrega |
|---|---|---|
| 1 | abb0ec1 | React, FastAPI, PostgreSQL, documentos e configurações |
| 2 | 9965ab1 | Equipe, escalas, substituições, feriados, confirmações e auditoria |
| 3 | 3c7f4ae | Estoque, lotes, validade, movimentos, estornos e inventário |
| 4 | ff98dda | Pedidos, aprovação, recebimento parcial e reembolsos |
| 5 | 893d222 | Caixa, vendas, despesas, conciliação, cancelamentos e devoluções |
| 6 | 1761cf1 | Receitas versionadas, produção, rendimento e porções |
| 7 | dd69a20 | Painel, relatórios mensais, metas e apurações preservadas |
| 8a | 3e69f6e | CSV com mapeamento, prévia, validação e rastreabilidade |
| 8b | e1aa190 | Anexos com integridade e arquivamento reversível |
| 8c | Commit desta entrega | Backup consistente, importação e restauração em banco isolado |

## Importação concluída

- CSV UTF-8 ou Windows-1252, até 2 MB e 2.000 linhas.
- Tipos: cadastro, resumo financeiro, venda por produto, recebimento digital e saldo inicial por lote.
- Seleção de colunas com campos obrigatórios e modelos de cabeçalho.
- Prévia sem gravação de lançamentos; validação repetida ao confirmar.
- Uma transação para todo o lote, com rollback em erro.
- Proteção por hash do arquivo e referências externas únicas.
- Conteúdo original preservado no banco, com download como texto.
- Resumos sem itens não baixam estoque nem inventam custo; a apuração sobre resultado permanece pendente nesses casos.

## Verificações finais desta etapa

- 46 testes passaram em PostgreSQL isolado (`cantina_em_dia_test`).
- Build TypeScript/Vite passou.
- `alembic check` passou: nenhuma alteração de estrutura pendente em relação aos modelos.
- Inicializador criou o primeiro backup local dos dados existentes. Pela interface, o teste restaurou essa cópia em outro banco, comparou os registros e removeu o banco temporário; a data de verificação apareceu no histórico.
- Telas de backup e anexos conferidas no navegador; console sem avisos/erros nessa conferência. Nenhum cadastro ou comprovante fictício foi inserido no banco operacional.
- A porta 8000 já estava ocupada por outra instância. Para a conferência, foram usadas temporariamente 8011/5184, sem alterar o `.env` nem encerrar processos alheios.
- Há um aviso de depreciação da biblioteca de testes Starlette/httpx, sem falha nos testes.

## Executar

```powershell
cd C:\dev\cantina-em-dia
npm.cmd start
```

Interface padrão: `http://127.0.0.1:5173`. Migrações são aplicadas pelo inicializador. Em instalação nova, executar `npm.cmd run setup` primeiro. Portas podem ser configuradas no `.env` quando necessário.

## O que ainda está pendente

- Validação do fluxo de anexos com comprovantes reais recebidos da equipe. O recebimento manual, vínculo, download e arquivamento reversível já estão disponíveis.
- Definir onde guardar a cópia externa dos backups e executar a rotina com os dados reais. A criação, verificação e restauração já estão disponíveis; não há envio automático para nuvem.
- Integração automática com Stone/WhatsApp. O que existe é lançamento manual e importação CSV assistida.
- Adaptação e validação com o arquivo real exportado pela solução Stone contratada.
- Confirmação dos nomes/horários da equipe, cardápio, tabela oficial de preços, regras de consumo e base/valor da meta.
- Revisão com dados reais dos custos e regras antes do uso operacional definitivo. Retificações históricas de custos e preços precisam de tratamento adicional; os registros existentes e as apurações guardadas não devem ser sobrescritos silenciosamente.
- Acesso por outros dispositivos, autenticação e publicação em rede. A versão atual é pessoal e local, em loopback.

## Dados e segurança do repositório

Credenciais estão em `.env`, ignorado pelo Git. Dados ativos do PostgreSQL em `%LOCALAPPDATA%\CantinaEmDia\postgres`, fora do OneDrive. Não tratar cópia de arquivos de um banco ativo como backup consistente. Dados de testes são isolados do banco operacional.

## Anexos (8b)

Quatro testes adicionais verificam integridade e download, rejeição de formatos inválidos, vínculo e arquivamento reversível e proteção de caminhos/referências. Testes usam armazenamento temporário isolado. Build TypeScript/Vite aprovado.

## Backup e recuperação (8c)

- ZIP lógico próprio da aplicação com registros de todas as tabelas e anexos, inclusive arquivados. Não inclui credenciais, código ou outros ZIPs de backup.
- Snapshot em transação PostgreSQL REPEATABLE READ, valores decimais preservados, datas com fuso e sequências restauradas sem reutilizar IDs reservados.
- Verificação de hash, tamanho, estrutura, revisão de migração e arquivos vinculados. Não executa SQL do arquivo nem extrai caminhos arbitrários.
- Teste de restauração em banco temporário, conferência dos registros e remoção ao concluir. Falha de limpeza é informada sem marcar sucesso.
- Recuperação cria um banco novo com nome gerado; não sobrescreve o banco em uso. Recupera anexos ausentes e preserva arquivos locais diferentes. A troca do banco no `.env` é manual.
- Importação de ZIP externo para recuperar o catálogo; verificação e restauração disponíveis também por CLI.
- Cópia automática na primeira inicialização do dia pelo `npm.cmd start`; pode ser desativada com `CANTINA_AUTO_BACKUP=0`. Não é um serviço contínuo ou agendado.
- Armazenamento em `%LOCALAPPDATA%\CantinaEmDia\backups`, configurável com `CANTINA_DATA_DIR`. O diretório do PostgreSQL permanece separado.
- Migração atual: `0010_backups`. Este formato exige a mesma revisão para recuperar; guardar o código correspondente junto à estratégia de cópia externa. Procedimento completo no README.

Nove testes adicionais cobrem restauração real com decimais, datas, horários, JSON e sequências; recuperação física de anexo ausente; preservação do banco de origem; arquivos adulterados; perda do catálogo; duplicidade; limites; caminhos indevidos; revisão incompatível; proteção do banco original; criação diária pelo CLI e bloqueio de alterações iniciadas por outro site. Os dados, arquivos e bancos de recuperação dos testes são isolados e limpos.
