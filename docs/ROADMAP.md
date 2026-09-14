# Roadmap proposto

Este roadmap separa as ideias solicitadas das sugestões técnicas. Prioridade não significa início automático: cada marco deve ser validado com critérios de aceite e testes.

## Princípios

- Segurança de movimento e laser acima de conveniência.
- Compatibilidade com trabalhos existentes enquanto houver migração.
- Modelo interno independente do formato importado e da controladora.
- Toda operação deve poder ser simulada sem hardware.
- Mudanças pequenas, versionadas e reversíveis.

## Fase 0 — Baseline reproduzível (P0)

**Objetivo:** saber exatamente o que é executado e impedir regressões.

- Criar fork/clone com histórico e registrar `upstream` após escolha da conta GitHub.
- [Concluído] Instalar a fonte oficial 0.71; a base 0.64 foi removida posteriormente por solicitação do responsável.
- Comparar formalmente 0.64 com 0.71 e registrar as mudanças relevantes para o desenvolvimento.
- [Concluído] Ambiente Python por computador, dependências fixadas e preparação automatizada no Windows.
- Modernizar o build Windows e produzir instruções PT-BR de desenvolvimento.
- Criar smoke test de inicialização e fixtures pequenas de SVG, DXF, raster e G-code.
- Capturar saídas de referência de geometria e EGV.
- Adicionar modo dry-run e regra de testes que não acesse hardware.

**Dificuldade:** M.  
**Critério de saída:** instalação limpa reproduzível, testes executáveis e comparação documentada 0.64 → 0.71.

## Fase 1 — Estrutura interna e idioma (P0)

**Objetivo:** permitir evolução incremental sem reescrever tudo.

- Extrair serviços de configuração, documento/trabalho, transformações, importação e controladora.
- Definir um `JobModel` com objetos, camadas, operação, cor, geometria e imagem.
- Introduzir interfaces `Importer` e `MachineBackend`.
- Migrar configurações para formato versionado (JSON ou TOML), com importação do TXT legado.
- [Em andamento] Interface PT-BR inicial entregue; falta extrair as strings para catálogo i18n e oferecer alternância PT-BR/inglês.
- Criar tratamento central de erros e logging útil para suporte.

**Dificuldade:** G.  
**Critério de saída:** interface abre em PT-BR/inglês; configuração antiga migra; importadores e máquina atual passam pelos novos contratos sem mudar o resultado.

## Fase 2 — Ganhos rápidos de fluxo (P1)

**Objetivo:** reduzir preparação fora do programa.

- Painel de propriedades com largura, altura, escala uniforme/não uniforme.
- Espelhamento horizontal/vertical e rotações 90°/180°/270°.
- Array retangular com linhas, colunas e espaçamento.
- Desfazer/refazer para transformações.
- Preview com seleção, limites da mesa, origem e alerta de extrapolação.
- Biblioteca de predefinições por material/processo, com nome, velocidade, passes e notas.
- Atribuição explícita de operação e cor por objeto/camada.

**Dificuldade:** G no conjunto; M por entrega.  
**Critério de saída:** um trabalho pode ser importado, dimensionado, replicado, classificado e preparado sem abrir editor externo para essas tarefas.

## Fase 3 — Importação moderna e raster nativo (P1)

**Objetivo:** aumentar compatibilidade e eliminar dependências desnecessárias.

Ordem recomendada:

1. DXF via `ezdxf`, com relatório de entidades suportadas/ignoradas e fallback temporário.
2. PNG, JPEG, BMP e TIFF diretos via Pillow, com DPI/tamanho físico explícitos, após a consolidação do DXF.
3. SVG vetorial nativo mais previsível e rasterização via backend empacotável.
4. PDF e AI compatível com PDF, com mensagens claras para variantes não suportadas.
5. 3DM com seleção de curvas/camadas e projeção 2D documentada.
6. DWG por conversor/adaptador opcional, após decisão de licença e distribuição.

**Dificuldade:** G–XG.  
**Critério de saída:** matriz de compatibilidade por formato, corpus de arquivos reais e nenhum erro silencioso de escala/unidade.

## Fase 4 — Backend GRBL (P1 estratégico)

**Objetivo:** usar o mesmo aplicativo com lasers K40/Nano e GRBL.

- Implementar `MachineBackend` primeiro para a Nano sem alterar comportamento.
- Criar gerador G-code a partir do `JobModel`.
- Criar transporte serial GRBL com descoberta de porta, handshake e leitura de estado.
- Implementar buffer/streaming, pausa, retomada, cancelamento, soft reset e recuperação.
- Mapear perfis de máquina: área, origem, limites, homing, aceleração e comandos de laser.
- Suportar GRBL 1.1 e validar diferenças relevantes de firmware/controladora.
- Criar simulador de protocolo e testes de longa duração antes de bancada.
- Só depois habilitar testes físicos graduais.

**Dificuldade:** XG.  
**Critério de saída:** o mesmo trabalho produz preview equivalente e executa com segurança em perfis Nano e GRBL homologados.

## Fase 5 — UX e operação (P2 contínuo)

- Fluxo guiado: Importar → Preparar → Simular → Executar.
- Fila/histórico local de trabalhos e reexecução controlada.
- Diagnóstico de conexão e exportação de pacote de suporte.
- Perfis de máquina e materiais com backup/exportação.
- Atalhos, acessibilidade, temas e layout responsivo.
- Documentação do operador, manutenção e solução de problemas em PT-BR.

## Ideias solicitadas

- Tradução PT-BR.
- Espelhamento, escala e arrays.
- DXF mais robusto.
- Raster nativo sem dependência do Inkscape.
- Predefinições de velocidades.
- Troca de cores/atribuição de linhas.
- Melhorias visuais e de fluxo.
- AI, 3DM, DWG e outros formatos.
- Suporte futuro a GRBL para padronização entre lasers.

## Sugestões para aprovação

Estas sugestões não foram tratadas como requisitos aprovados:

1. **Atualizar primeiro para 0.71**, preservando o histórico e isolando a atualização das novas funções.
2. **Criar um modelo de trabalho independente** para evitar que cada formato e controladora implemente regras duplicadas.
3. **Adicionar simulação/dry-run obrigatória** e testes sem hardware desde a primeira fase.
4. **Separar operação de cor**: vermelho/azul continuam importáveis, mas deixam de ser a única forma de decidir corte/gravação.
5. **Priorizar raster direto e DXF antes de AI/3DM/DWG**, pois atendem mais trabalhos com menor risco técnico/licenciamento.
6. **Tratar DWG como integração opcional**, condicionada à escolha de biblioteca/conversor e licença.
7. **Começar GRBL somente após a interface de controladoras**, usando simulador antes de qualquer máquina real.
8. **Incluir limites e origem no preview**, bloqueando execução fora da área útil por padrão.
9. **Criar presets completos de processo**, não apenas velocidade: passes, modo, intervalo/DPI e notas, deixando potência vinculada à capacidade da máquina.
10. **Manter migração compatível das configurações**, para não perder ajustes atuais de operação.

## Primeira sequência de implementação recomendada

1. Recuperar histórico/fork sobre a base 0.71 já instalada.
2. Montar ambiente Python e smoke tests.
3. Testes de caracterização para importação, transformações e EGV.
4. Extrair catálogo de textos e configuração versionada.
5. Entregar PT-BR e presets como primeira melhoria visível.
6. Consolidar transformações e implementar array com preview/limites.
7. Migrar DXF para adaptador robusto.
8. Implementar raster direto após a consolidação do DXF.
9. Preparar e implementar GRBL.
10. Avaliar AI/3DM/DWG com arquivos reais dos usuários.

## Decisões pendentes

- Conta ou organização GitHub que receberá o fork.
- Sistemas operacionais prioritários (presumido: Windows primeiro).
- Modelos exatos das placas Nano e GRBL em uso.
- Dimensões, origem, homing e limites de cada laser.
- Formatos e arquivos reais mais frequentes na operação.
- Se os presets serão globais, por máquina ou compartilhados em rede.
- Política de potência: manual no painel da K40 ou controlada por firmware nos equipamentos GRBL.
