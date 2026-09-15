# Roadmap da primeira versão funcional

## Objetivo

Entregar o melhor fluxo possível para preparar e executar trabalhos reais na
K40, com baixo consumo de tempo, memória e processamento. A V1 fica concentrada
em DXF, raster nativo, transformações essenciais e arrays procedurais.

Funcionalidades que não reduzam trabalho recorrente do operador ou não sejam
necessárias para esses quatro pilares ficam fora do caminho crítico.

## Princípios de decisão

- Priorizar arquivos e operações usados na prática.
- Medir antes de otimizar e manter benchmarks reproduzíveis.
- Evitar cópias de geometria e processamento antecipado desnecessário.
- Preservar objetos procedurais e curvas analíticas pelo maior tempo possível.
- Executar tarefas pesadas fora da thread da interface e publicar em lotes.
- Não adicionar dependências externas quando houver implementação interna
  simples, testável e distribuível.
- Cada marco precisa de testes automatizados e validação com arquivos reais.

## Ordem da V1

### 1. Concluir as otimizações de importação

**Objetivo:** abrir DXFs grandes com feedback contínuo, uso controlado de memória
e sem congelar a interface.

Já concluído:

- ambiente Python isolado por computador e dependências fixadas;
- importação DXF em thread de trabalho, cancelamento e barra de progresso;
- publicação atômica do trabalho e deslocamento por referência;
- correções de OCS/WCS, projeção, layers, cores e entidades preenchidas;
- composição e simplificação de linhas explodidas;
- instrumentação por fase;
- uma única decomposição das entidades e preservação de curvas analíticas;
- discretização de curvas somente na fronteira legada.
- discretização adaptativa por desvio geométrico máximo para arcos e Béziers.

Pendente para encerrar o marco:

1. Otimizar a leitura do arquivo e verificar alternativas seguras do `ezdxf`.
2. Reduzir o custo da composição topológica em desenhos inteiramente explodidos.
3. Medir tempo e pico de memória com corpus pequeno, médio e grande.
4. Garantir atualização incremental do preview sem pico na thread principal.
5. Criar testes de regressão para DXFs grandes, curvas, textos e contornos
   explodidos.
6. Definir um formato de projeto salvo manualmente para reabrir o documento já
   processado, sem cache automático.

**Critério de conclusão:** os arquivos reais de referência abrem sem congelamento,
com progresso e cancelamento funcionais, métricas registradas e sem alteração de
posição, escala ou geometria.

### 2. Implementar arrays procedurais inteligentes

**Objetivo:** replicar peças sem duplicar seus vetores e sem exigir DXFs enormes.

Esta etapa vem antes da edição completa de vetores porque afeta diretamente
memória, preview, limites da mesa, estimativa de tempo e cálculo de rotas.

Escopo:

1. Criar objeto de instância que referencie uma geometria-base.
2. Implementar array retangular por quantidade e espaçamento ou distância total.
3. Manter o array editável, sem explodir clones em vetores.
4. Calcular limites e preview a partir de transformações das instâncias.
5. Reutilizar resultados geométricos e preparar otimização de rota por peça.
6. Permitir transformar, habilitar e remover o array sem alterar a base.

Estado atual: primeira versão implementada com grade, zig-zag, desvios manuais,
preenchimento da área disponível, preview leve e expansão assíncrona na fronteira
legada. Falta validar o fluxo visual com trabalhos reais e avançar a reutilização
de rotas para evitar materialização proporcional no backend antigo.

**Critério de conclusão:** centenas de cópias usam uma única geometria-base,
continuam editáveis e não provocam crescimento proporcional do modelo canônico.

### 3. Concluir raster nativo sem Inkscape

**Objetivo:** importar e preparar gravações raster sem ferramentas externas.

Já concluído:

- representação canônica de preenchimentos e imagens;
- conversão inicial de `HATCH`, `SOLID` e `TRACE`;
- rasterização interna de preenchimentos, furos e transparência do fundo;
- intensidade normalizada preparada no modelo.

Pendente:

1. Consolidar preenchimentos DXF sólidos e seus casos de contorno.
2. Importar diretamente PNG, JPEG, BMP e TIFF com DPI/tamanho físico explícito.
3. Implementar grayscale real de 0 a 100%, mantendo a intensidade independente
   da cor de processo.
4. Definir conversão para máquinas sem PWM: dithering ou densidade de linhas.
5. Manter caminho preparado para PWM em controladoras compatíveis, sem torná-lo
   requisito da K40 atual.
6. Integrar espaçamento/DPI, velocidade, passadas, preview e estimativa de tempo.
7. Validar memória e processamento com imagens e hatches grandes.

**Critério de conclusão:** preenchimentos e imagens em grayscale podem ser
importados, visualizados, configurados e enviados sem Inkscape, com resultado e
dimensões previsíveis.

### 4. Edição simples de vetores no painel principal

**Objetivo:** preparar o trabalho sem retornar ao CAD para ajustes básicos.

Escopo:

1. Seleção do trabalho, objeto ou array no preview.
2. Largura, altura e escala uniforme ou independente.
3. Rotação livre e atalhos de 90°, 180° e 270°.
4. Espelhamento horizontal e vertical.
5. Ponto de referência previsível para cada transformação.
6. Campos no painel principal com atualização imediata de limites e preview.
7. Transformações por referência, sem reescrever todos os vetores.
8. Desfazer e refazer apenas para as operações de edição da V1.

**Critério de conclusão:** escala, rotação e espelhamento são aplicados de forma
não destrutiva e responsiva, inclusive em arrays, sem modificar a geometria-base.

## Dependências entre os marcos

```text
Importação otimizada
        |
        v
Modelo de instâncias/arrays
       / \
      v   v
Raster   Edição por transformações
   \       /
    v     v
 Fluxo funcional da V1
```

Raster pode avançar em paralelo conceitualmente, mas a sequência principal deve
estabilizar primeiro importação e instâncias. A edição usa o mesmo sistema de
transformações criado para arrays.

## Fora do escopo da V1

- suporte novo a SVG, PDF, AI, 3DM e DWG;
- backend GRBL;
- preservação procedural de blocos DXF;
- cache automático de arquivos importados;
- edição vetorial avançada de nós e curvas;
- biblioteca extensa de materiais e presets;
- fila ou histórico completo de trabalhos;
- temas, internacionalização completa e reformulação visual ampla;
- recursos de nuvem ou colaboração.

Os leitores SVG e G-code já existentes permanecem por compatibilidade, mas não
recebem desenvolvimento ativo antes do fechamento da V1.

## Próxima ação

Usar a instrumentação atual para atacar os dois custos dominantes do
`teste_Chaveiro.dxf`: leitura pelo `ezdxf` e composição topológica. Depois de
fechar e medir esse marco, iniciar o modelo procedural de instâncias e o array
retangular antes de retomar o raster grayscale.
