# K40 Whisperer PT-BR — DXF refatorado

Fork do [K40 Whisperer original](https://github.com/stephenhouser/k40-whisperer)
voltada a um fluxo moderno de preparação e produção em máquinas laser K40.
O projeto mantém compatibilidade com a controladora Nano M2 e concentra seu
desenvolvimento em importação DXF robusta, raster nativo, edição essencial e
arrays procedurais.

## Download para Windows

- **[Baixar o instalador final da versão 1.1.1](https://github.com/LauckGui/k40-whisperer-ptbr-dxf/releases/download/v1.1.1/K40-Whisperer-Setup-1.1.1-x64.exe)**
- [Baixar a versão portátil em ZIP](https://github.com/LauckGui/k40-whisperer-ptbr-dxf/releases/download/v1.1.1/K40-Whisperer-Portable-1.1.1-x64.zip)
- [Ver notas completas e arquivos da versão 1.1.1](https://github.com/LauckGui/k40-whisperer-ptbr-dxf/releases/tag/v1.1.1)

O instalador inclui a aplicação e suas dependências Python. O driver USB
compatível com a controladora K40 continua sendo necessário, assim como na
distribuição original.

## Principais diferenças em relação ao projeto original

- importação DXF em thread separada, com progresso, cancelamento e publicação
  incremental;
- correções de OCS/WCS, projeção de eixos, layers, cores, textos e entidades
  preenchidas;
- composição topológica de contornos explodidos, simplificação e curvas
  analíticas com discretização adaptativa;
- rasterização interna de `HATCH`, `SOLID` e `TRACE`, sem depender do Inkscape;
- importação e alinhamento de imagens com escala, deslocamento, zoom, pan e
  máscara por contorno vetorial;
- grayscale com brilho, contraste, gama, inversão e diferentes algoritmos de
  dithering;
- transformações sincronizadas de vetor e imagem: escala, dimensões, rotação e
  espelhamento;
- arrays procedurais em grade ou zig-zag, com instâncias ignoráveis e um único
  bitmap-base compartilhado;
- execução do array por processo ou conclusão integral de cada peça antes da
  próxima;
- projetos `.k40p` autocontidos, preservando geometria, imagens, alinhamento,
  posição e parâmetros de produção;
- interface em português do Brasil e inglês, com configurações persistentes.

## Arrays e geração EGV

Os arrays permanecem procedurais no modelo interno: a geometria e o bitmap da
peça não são clonados. No modo de execução por peça, a geometria-base é preparada
uma vez e reutilizada por deslocamento em cada instância.

A controladora Nano M2 não oferece subrotinas ou loops no protocolo EGV. Por
isso, embora a preparação geométrica seja reutilizada, os movimentos de todas
as instâncias ainda precisam ser transmitidos integralmente à máquina.

## Estado da versão 1.1.1

- 108 testes automatizados aprovados;
- inicialização da aplicação-fonte e do executável empacotado verificada;
- instalador e pacote portátil publicados;
- validação física completa na máquina K40 prevista como próxima etapa.

Antes de executar lotes grandes, valide origem, dimensões, sentido dos eixos,
velocidades e potência com um trabalho pequeno e seguro.

## Desenvolvimento

As instruções para preparar o ambiente, executar testes e gerar o instalador
estão em [README_DESENVOLVIMENTO.md](README_DESENVOLVIMENTO.md). O roadmap
atualizado está em [docs/ROADMAP.md](docs/ROADMAP.md).

## Créditos e licença

Este trabalho foi desenvolvido a partir do K40 Whisperer original. O projeto e
seu autor original continuam devidamente creditados. Esta fork preserva a
licença GNU GPL; consulte [gpl-3.0.txt](gpl-3.0.txt).
