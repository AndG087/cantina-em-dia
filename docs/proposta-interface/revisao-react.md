# Revisão do protótipo em React

O protótipo está em `frontend/src/proposal`, acessível em **http://127.0.0.1:5173/proposta**. A aplicação principal continua em `/`. O endereço antigo na porta 5190 encaminha para a rota nova enquanto seu servidor estiver ligado.

## Correções aplicadas

- Cenários diferentes são renderizados a partir de `data.ts`. Não existem mais duas versões do texto de cada produto mantidas juntas no HTML.
- Dia, compra, despesa, produto e resumo semanal usam os mesmos objetos. O relatório filtra os dias pelo início e fim da semana, calcula seus totais e abre o dia correto.
- O cenário `?cenario=primeiro-uso` começa sem dias, compras, gastos, fornecedores de compras ou eventos registrados. Seus produtos ainda não foram contados. Cada cenário guarda somente suas próprias simulações.
- Nomes dos responsáveis começam vazios. Mensagens de validação permanecem junto ao campo, com `aria-invalid` e `aria-describedby`. O bloco recolhido abre quando contém um erro, e o foco vai para o primeiro campo inválido.
- As etapas usam `#daily/1`, `#daily/2` e `#daily/3`. Voltar/avançar no navegador muda a etapa. Recarregar mantém o rascunho e a etapa neste navegador.
- Voltar a “Registrar um dia” pelo botão habitual oferece continuar o rascunho ou começar de novo. Após salvar, o rascunho do dia é removido. Links para etapas sem um rascunho indicam o ponto inicial, em vez de fingir que os dados existem em outro computador.
- “Esse dia já foi registrado” oferece abrir o dia ou corrigir o último fechamento. Dias anteriores continuam protegidos pela regra atual. A correção carrega os valores existentes e exige motivo.
- “Ver dia” abre recebimentos, conta da gaveta, responsáveis, horários, conferência e correção quando permitida. “Ver nota” abre todos os produtos, quantidades, custos, soma, total impresso, diferença e gasto vinculado.
- Compras aceitam vários produtos, inclusão e remoção de linhas, subtotais, busca no catálogo de exemplo, quantidades fracionadas para kg, unidades inteiras para `un`, explicação da nota divergente e prevenção de documento duplicado por fornecedor.
- Salvar uma compra no simulador atualiza a nota, os saldos dos produtos e um único gasto vinculado. As telas seguintes usam esses registros, sem valores independentes no HTML.
- Diferenças de gaveta usam aviso âmbar com texto; valores corretos usam verde. A cor não é a única indicação.
- Avisos de validação pertencem ao formulário. Não há avisos flutuantes globais que apareçam na próxima tela.
- A troca de tela ou etapa move o foco para o título. Os alvos visíveis de navegação e ação têm pelo menos 44 px, em geral 48 px. Valores em reais e quantidades em kg usam `inputMode="decimal"`.
- O registro é renderizado uma etapa por vez. Os detalhes da conta e os horários ficam recolhidos quando não estão sendo consultados.

## Estrutura

| Arquivo | Responsabilidade |
|---|---|
| `data.ts` | Tipos, dados por cenário, cálculos, derivação da semana e armazenamento isolado |
| `components.tsx` | Campos, erros, foco, navegação, diferenças e mensagens reutilizáveis |
| `DailyFlow.tsx` | Dia em três etapas, rascunho, detecção de duplicidade e correção |
| `PurchaseFlow.tsx` | Nota com vários produtos e rascunho local da compra |
| `StockFlow.tsx` | Busca, contagem parcial e revisão antes de registrar |
| `Views.tsx` | Listas, detalhes, semana, despesas, consulta e funcionamento |
| `Proposal.tsx` | Rota, navegação, cenário, foco e estado do simulador |
| `styles.css` | Estilos restritos a `.p-app`, sem alterar as telas atuais |

O frontend reaproveita os formatadores de dinheiro e quantidade de `components/ui.tsx`. Os formulários do protótipo usam componentes próprios porque o componente genérico atual não oferece validação contextual, preenchimento e navegação por etapas.

## Relação com a API e limites

Os objetos seguem os campos usados por `/cash-reviews/days`, `/purchase-receipts`, `/items`, `/expenses` e pelo resumo semanal. **Isso não significa que o novo fluxo já possa ser enviado à API atual.**

As informações propostas sobre horários desconhecidos e itens não contados estão identificadas em `DemoMeta`. Ao salvar um dia sem horários no simulador, não são fabricados horários reais: os instantes ficam ausentes no exemplo. A API atual ainda não aceita esse registro como um fechamento completo. A integração futura precisa resolver essa diferença explicitamente, conforme a análise.

As compras diretas também exigem a operação transacional já descrita na proposta. O simulador aplica os efeitos somente ao seu estado local. Momentos administrativos das simulações usam uma referência fixa e não representam um horário real informado pela equipe.

O catálogo tem seis produtos fictícios representativos, sem importar nem alterar os 217 cadastros reais. O cenário inicial permanece “não contado” até que cada item seja explicitamente contado.

Rascunhos e registros de exemplo usam apenas as chaves `cantina.proposta.v2.*` no armazenamento local do navegador. “Reiniciar exemplo” pede confirmação e limpa somente o cenário de demonstração escolhido. Falha no armazenamento é informada. Nenhuma requisição à API é feita pela rota.

Pedidos antecipados permanecem como caminho secundário descrito; edição completa de cadastro, exclusão, impressão e versões de relatório não foram integradas nesta revisão. São recursos preservados no sistema atual. Os detalhes do dia e da nota, dia já existente e compra com vários produtos foram priorizados conforme a revisão do usuário.

## Verificação

- TypeScript e build do Vite passaram.
- Navegação e interações verificadas no Chrome em 1365 px e 390 px, sem erros JavaScript nem chamadas à API na rota de proposta.
- Exercitados: nomes vazios em bloco recolhido, foco de erro e de título, passos no endereço, voltar/avançar, recarregar, retomar rascunho, soma dos quatro recebimentos, falta na gaveta, nota com diferença, compra de vários itens, gasto vinculado uma única vez, dia duplicado e busca sem acentos.
- Primeiro uso conferido em Caixa, Compras, Semana, Estoque e Histórico, sem reaproveitar números ou notas do outro cenário.
- Alvos de toque visíveis verificados com pelo menos 44 px. Reais e kg conferidos com teclado decimal. Cada etapa é renderizada isoladamente.
- O estado de exemplo usado nas verificações é limpo ao final; capturas são produzidas a partir dos dados originais do cenário.

## Estado da tarefa anterior

Na verificação de 10/11/2026, a API real respondeu com `0002_vale_refeicao` e o banco `cantina_em_dia` continha 217 itens. Não foi necessário reiniciar processos nem repetir o cadastro. As alterações anteriores permanecem sem commit; esta revisão não faz commit nem modifica esses dados.
