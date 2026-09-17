# Roadmap enxuto — K40 Whisperer PT-BR 1.1

## Objetivo

Manter um fluxo rápido e previsível para produção real em uma K40, priorizando
DXF, raster nativo, transformações essenciais e arrays procedurais. Funcionalidades
sem impacto recorrente no uso da máquina ficam fora do caminho crítico.

## Entregue na versão 1.1

### Importação e projetos

- ambiente Python isolado por computador e dependências fixadas;
- DXF assíncrono com progresso, cancelamento e publicação incremental;
- correções de OCS/WCS, projeção, layers, cores e entidades preenchidas;
- composição topológica, simplificação e discretização adaptativa de curvas;
- modelo canônico com curvas analíticas preservadas até a fronteira legada;
- instrumentação das fases de importação;
- projeto `.k40p` com novo, abrir, salvar e salvar como, incluindo geometria,
  imagem, alinhamento, parâmetros de processo e arrays.

### Raster nativo

- preenchimentos DXF (`HATCH`, `SOLID` e `TRACE`) sem Inkscape;
- importação direta de imagens e alinhamento visual com escala, deslocamento,
  zoom, pan e máscara por contorno vetorial;
- brilho, contraste, gama, inversão e algoritmos de dithering;
- preview e geração de rota usando o mesmo tratamento raster;
- bitmap-base preservado uma única vez em arrays, com repetição procedural das
  rotas e consideração dos limites efetivos da imagem e da máscara.

### Edição

- escala por porcentagem, largura ou altura, rotação e espelhamento;
- transformações sincronizadas entre vetor e imagem;
- posicionamento por referência, jog pelo teclado e régua da área útil;
- configurações persistentes e interface PT-BR/Inglês.

### Arrays procedurais

- grade e zig-zag com espaçamento e ajustes X/Y;
- preenchimento da área útil, preview leve e instâncias individualmente
  ignoráveis/reativáveis;
- uma única geometria e um único bitmap-base no modelo canônico;
- escolha entre execução por processo ou conclusão integral de cada peça;
- no modo por peça, a geometria vetorial é tessellada/otimizada uma vez e só os
  deslocamentos são aplicados a cada instância; scanlines raster também são
  reutilizadas sem recompor bitmaps.

O protocolo EGV/Nano M2 não oferece uma instrução de subrotina ou repetição.
Por isso o processamento geométrico pode ser reutilizado, mas todos os movimentos
de cada instância ainda precisam ser transmitidos à controladora.

## Validação antes da liberação definitiva

1. Executar o conjunto de testes automatizados e verificar inicialização do
   executável empacotado.
2. Na máquina real, validar um trabalho pequeno em cada modo de array:
   por processo e por peça.
3. Validar raster com máscara, grayscale e uma instância ignorada.
4. Confirmar origem, sentido Y, dimensões e retorno do cabeçote antes de usar um
   lote grande.

## Fora do escopo atual

- novos formatos vetoriais além dos leitores legados já mantidos;
- backend GRBL ou potência dinâmica/PWM para a K40 atual;
- preservação procedural de blocos DXF;
- cache automático de importação;
- edição avançada de nós e curvas;
- fila completa de produção, biblioteca de materiais ou recursos de nuvem;
- nesting automático por contorno côncavo.

Depois da validação física da 1.1, novos itens só entram se resolverem um problema
observado no uso real da máquina.
