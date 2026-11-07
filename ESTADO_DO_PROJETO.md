# Estado do projeto

Atualizado em 7 de novembro de 2026. Repositório: `C:\dev\cantina-em-dia`. Versão local 0.2.0. Commits feitos localmente; não houve envio ao GitHub.

## Continuidade autorizada

O usuário pediu “continue”. A pausa anterior foi encerrada e o desenvolvimento foi retomado. Manter um commit por etapa validada. A etapa de anexos (8b) está concluída; a próxima entrega é backup/restauração (8c).

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

| 8b | Commit desta entrega | Anexos com integridade e arquivamento reversível |

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

- 37 testes passaram em PostgreSQL isolado (`cantina_em_dia_test`).
- Build TypeScript/Vite passou.
- `alembic check` passou: nenhuma alteração de estrutura pendente em relação aos modelos.
- API respondeu 200 para saúde do banco, configuração de importação e painel.
- Tela de importação conferida no navegador; console sem avisos/erros nessa conferência. Nenhum arquivo de teste foi importado no banco operacional pelo navegador.
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
- Backup consistente e restauração testada. As tabelas `attachments` e `backup_records` foram preparadas pela migração 0008, e serão usadas na próxima etapa; não há operação de backup/restauração implementada ainda.
- Integração automática com Stone/WhatsApp. O que existe é lançamento manual e importação CSV assistida.
- Adaptação e validação com o arquivo real exportado pela solução Stone contratada.
- Confirmação dos nomes/horários da equipe, cardápio, tabela oficial de preços, regras de consumo e base/valor da meta.
- Revisão com dados reais dos custos e regras antes do uso operacional definitivo. Retificações históricas de custos e preços precisam de tratamento adicional; os registros existentes e as apurações guardadas não devem ser sobrescritos silenciosamente.
- Acesso por outros dispositivos, autenticação e publicação em rede. A versão atual é pessoal e local, em loopback.

## Dados e segurança do repositório

Credenciais estão em `.env`, ignorado pelo Git. Dados ativos do PostgreSQL em `%LOCALAPPDATA%\CantinaEmDia\postgres`, fora do OneDrive. Não tratar cópia de arquivos de um banco ativo como backup consistente. Dados de testes são isolados do banco operacional.

## Anexos (8b)

Quatro testes adicionais verificam integridade e download, rejeição de formatos inválidos, vínculo e arquivamento reversível e proteção de caminhos/referências. Testes usam armazenamento temporário isolado. Build TypeScript/Vite aprovado.
