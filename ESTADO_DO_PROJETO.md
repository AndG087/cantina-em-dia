# Estado do projeto

Atualizado em 7 de novembro de 2026. Repositório local: `C:\dev\cantina-em-dia`. GitHub configurado: `https://github.com/AndG087/cantina-em-dia`. Alterações desta etapa ainda não foram enviadas ao GitHub.

## Etapa atual

Etapa 1 — fundação. Stack: FastAPI/Python, React/TypeScript/Vite e PostgreSQL real. Uso inicial em Windows, restrito ao computador do gerente.

## Implementado

- Os quatro documentos de contexto foram copiados do planejamento original e estão disponíveis pela interface, com download.
- Interface responsiva com visão geral, roteiro de implantação, documentos e configurações.
- Configurações de nome, local e gerente persistidas no PostgreSQL. Fuso fixado em America/Sao_Paulo.
- Endpoint de saúde do processo e endpoint distinto que consulta banco, versão e revisão da migração.
- Migração Alembic `0001_foundation`: tabela `app_settings`, com uma única linha inicial e sem registros financeiros fictícios.
- Inicializador local com PostgreSQL 17 em `%LOCALAPPDATA%\CantinaEmDia\postgres`, fora do OneDrive, senha aleatória em `.env` e serviços apenas em loopback.
- Instalação, build e testes documentados. Dependências Node com lock e dependências Python congeladas.

## Validação

- Build TypeScript/Vite concluído.
- Cinco testes passaram em PostgreSQL isolado (`cantina_em_dia_test`): saúde real e migração, persistência das configurações, rejeição de entradas inválidas, indisponibilidade do banco sem exposição de senha e leitura/download dos documentos permitidos.
- Os testes emitiram um aviso de depreciação da biblioteca Starlette sobre o cliente HTTP de testes. Isso não impediu os testes; não houve falha funcional observada.
- `alembic check` passou, sem diferenças entre os modelos e a migração aplicada.
- Conferidos no navegador integrado: tela inicial, menu compacto, formulário de configuração e leitura dos documentos. O console da aplicação não mostrou avisos nem erros durante a conferência. O layout compacto foi visto em captura; a captura completa de desktop não esteve disponível no navegador integrado.
- O build final também passou após os ajustes de navegação e remoção de fontes externas.
- O PostgreSQL foi reiniciado e a linha de configuração persistiu. O banco foi encerrado novamente após essa conferência.

## Como executar

```powershell
cd C:\dev\cantina-em-dia
npm.cmd start
```

Interface: `http://127.0.0.1:5173`. Ctrl+C encerra os serviços desta sessão. Em uma nova instalação, executar `npm.cmd run setup` primeiro.

Os servidores usados na conferência foram encerrados ao terminar. Para usar a aplicação, execute o comando acima.

## Limites desta entrega

Ainda não existem lançamentos de vendas, caixa, estoque, compras, reembolsos, produção ou remuneração. Há apenas configurações iniciais. Não há integração Stone/WhatsApp, autenticação para uso em rede nem fluxo operacional de backup e restauração. O painel distingue o que está pronto do que está pendente.

## Próxima etapa

Implementar equipe e responsabilidade pelo caixa por tarefas pequenas: primeiro funcionários e escalas; depois indicação do responsável previsto, exceções, confirmações e substituições com histórico. Considerar os limites de disponibilidade do gerente e os registros enviados pela Dona Gel.

Informações ainda não conhecidas devem continuar pendentes, especialmente nomes e horários, valor/base da meta, cardápio completo, regras de consumo da equipe e recursos efetivamente contratados da Stone. Consultar os documentos antes de perguntar novamente ou presumir uma regra.
