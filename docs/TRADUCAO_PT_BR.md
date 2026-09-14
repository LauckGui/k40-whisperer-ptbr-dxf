# Tradução PT-BR

## Escopo da primeira entrega

- Tela principal e barra de status.
- Menus Arquivo, Visualizar, Ferramentas, Configurações e Ajuda.
- Configurações gerais, de raster e do rotativo.
- Diálogos de contorno, envio EGV, unidades DXF, escala SVG e pausa.
- Principais mensagens de validação, importação, memória, arquivos e estado USB.

Os identificadores internos, nomes das classes, chaves do arquivo de configuração e valores usados pela lógica foram preservados. Os módulos `nano_library.py`, `egv.py` e `LaserSpeed.py` não foram alterados.

## Vocabulário adotado

| Inglês | PT-BR |
|---|---|
| Raster engrave | Gravação raster |
| Vector engrave | Gravação vetorial |
| Vector cut | Corte vetorial |
| Home | Origem |
| Rail | Eixos |
| Jog step | Passo manual |
| Trace boundary | Contornar limite |
| Pass | Passada |
| Halftone / dither | Meio-tom / dithering |

Siglas e nomes de formatos — USB, SVG, DXF, EGV, CRC, DPI e G-code — permanecem inalterados.

## Próximos refinamentos

- Revisão visual em diferentes escalas do Windows.
- Revisão terminológica com operadores das máquinas.
- Extração futura das strings para catálogos de idioma, permitindo alternar entre PT-BR e inglês sem duplicar a interface.

## Reorganização da interface

O painel lateral chamado anteriormente de “Configurações avançadas” foi retirado da tela principal. As opções foram redistribuídas no menu **Configurações**:

- **Trabalho e desenho:** transformações, coordenadas, ordem e agrupamento.
- **Raster:** passo de varredura, direção, meio-tom, inversão e níveis.
- **Rotativo:** ativação, escala e velocidade rápida.
- **Geral e máquina:** unidades, comportamento, Inkscape, placa e área útil.

As janelas foram ampliadas para acomodar os rótulos em PT-BR. A tecla `F6` agora abre “Trabalho e desenho”. A chave legada `advanced` continua sendo lida para manter compatibilidade com configurações antigas, mas não controla mais um painel lateral.

O número de passadas não fica mais nessa janela: cada campo foi colocado ao lado da velocidade da operação correspondente na tela principal (raster, gravação vetorial, corte vetorial e G-code).

## Tabela de processos e gerenciador

A área operacional principal foi convertida em uma tabela com as colunas **Processo**, **Ativo**, **Velocidade**, **Passadas** e **Cor**. A coluna de potência aparece adicionalmente apenas para placas M3 com controle de potência habilitado. As cores são somente indicadores e seguem a classificação existente: preto para raster/G-code, azul para gravação vetorial e vermelho para corte vetorial.

Os antigos botões separados de execução foram substituídos por um único botão **Rodar**, que respeita as operações marcadas. Abaixo da tabela ficam **Rodar**, **Pausar/Continuar** e **Parar**. A velocidade de G-code é indicada como proveniente do próprio arquivo.

## Ícones e compactação visual

Os principais comandos passaram a usar uma biblioteca interna de ícones desenhados com Pillow: conectar, abrir, recarregar, origem, liberar eixos, mover para, direções, rodar, pausar/continuar e parar. Isso mantém traço, tamanho e cores consistentes sem fontes especiais nem dependências adicionais.

A barra lateral foi reduzida de 390 para 350 px e a janela inicial de 1100 para 1020 px. A tabela termina em 342 px, deixando apenas a margem de 8 px antes do preview. A conexão usa um único indicador, alternando entre **Desconectado**, **Conectado** e **Erro de conexão**.

A tabela também passou a reposicionar suas colunas conforme a disponibilidade de potência M3. Sem essa opção, há apenas 4 px entre Velocidade e Passadas; com M3, os cabeçalhos são abreviados para evitar cortes. Separadores horizontais leves delimitam o cabeçalho e cada processo.
