# Relatório do estado atual — K40 Whisperer

**Data da avaliação:** 14 de setembro de 2026  
**Base originalmente avaliada:** K40 Whisperer 0.64  
**Base de trabalho atual:** K40 Whisperer 0.71 (fonte oficial, atualizada em 14 de setembro de 2026)  
**Escopo:** inspeção estática do código-fonte recebido; nenhum equipamento laser foi acionado.

## Resumo executivo

O projeto é uma aplicação desktop em Python com interface Tkinter para preparar e enviar trabalhos a controladoras K40/Lihuiyu (Nano). A base é funcional e contém bastante conhecimento de domínio, mas sua arquitetura é predominantemente monolítica: `k40_whisperer.py` concentra interface, estado, transformação geométrica, configuração e orquestração do equipamento.

A recomendação é **não iniciar por novos formatos ou GRBL**. A fonte local já foi atualizada da 0.64 para a 0.71; as próximas etapas devem recuperar o histórico Git correto, preservar o comportamento atual com testes de caracterização e criar fronteiras internas para importadores, documento, configurações e controladores. Em seguida, tradução PT-BR, predefinições, transformação/array e raster nativo podem ser entregues com risco controlado.

## Inventário técnico

- Linguagem e interface: Python 2/3 legado e Tkinter.
- Dimensão aproximada: 22 arquivos Python, 13.135 linhas; o arquivo principal sozinho tem aproximadamente 5.318 linhas.
- Dependências declaradas: `lxml`, `pyusb`, `Pillow`, `pyclipper` e `pyinstaller`.
- Controladora atual: família Lihuiyu/Nano por USB, implementada principalmente em `nano_library.py`, `egv.py` e `LaserSpeed.py`.
- Entradas expostas pela aplicação: SVG, DXF e G-code; EGV pode ser aberto/enviado e também salvo.
- Raster: representado com Pillow, mas a rasterização de conteúdo SVG é delegada a um processo externo do Inkscape.
- Persistência: arquivo de texto `k40_whisperer.txt`, com leitura e escrita manual de pares de configuração.
- Empacotamento: scripts antigos de py2exe e uma especificação PyInstaller voltada ao macOS.
- Testes: não foi encontrada suíte automatizada. O arquivo `k40_whisperer_test.svg` é uma amostra, não um teste executável.
- Ambiente atual: Python 3.14 de 64 bits; ambiente por computador em `.venv-<NOME_DO_PC>`, recriável por `Preparar_Ambiente.bat`, com dependências fixadas e `ezdxf` para a etapa DXF.
- Verificação local: os módulos e as dependências foram validados sem inicializar USB. A opção `--help` legada cria a interface antes de processar os argumentos e não deve ser usada como smoke test automatizado.
- Git: a pasta recebida não contém `.git`; continua sendo um snapshot, não um clone ou fork.
- Atualização: o pacote oficial `K40_Whisperer-0.71_src.zip` foi instalado na pasta principal. SHA-256: `F0294F61AE2E1BAEB6BDE74CBD209D001E436ECDD5D2A9F2B28B9F0087EB0986`.
- Limpeza: a base 0.64 e os arquivos temporários de atualização foram removidos em 14 de setembro de 2026, por solicitação do responsável. A pasta de trabalho contém somente a base 0.71.

## Capacidades já existentes

| Área | Estado encontrado | Observação |
|---|---|---|
| Espelhamento | Existe | Opção booleana e transformação de coordenadas; precisa ser mais visível e testada. |
| Rotação | Parcial | Rotação fixa de 90°; não é uma ferramenta geral de edição. |
| Escala | Parcial | Fatores de calibração X/Y e escala rotativa; falta escala de objeto amigável, uniforme/não uniforme e validação visual. |
| Array/cópias | Ausente | Não foi encontrada ferramenta de duplicação em grade. |
| Cores de operação | Parcial | SVG/DXF classificam azul como gravação e vermelho como corte; o usuário não possui um editor de atribuição/recoloração na aplicação. |
| Predefinições | Parcial | Há configuração global em texto; não há biblioteca nomeada por material/processo. |
| Raster nativo | Parcial | Pillow processa a imagem resultante, mas SVG ainda depende do Inkscape para rasterização e conversão de texto. |
| DXF | Legado próprio | Parser interno extenso, sujeito a variantes modernas e entidades não suportadas. |
| AI, 3DM e DWG | Ausente | Precisam de adaptadores e, em alguns casos, conversores/bibliotecas externos. |
| GRBL | Ausente | O fluxo atual está acoplado ao protocolo EGV/Nano. |
| Internacionalização | Ausente | Textos ingleses estão espalhados pela criação da interface e pelas mensagens. |

## Arquitetura observada

O fluxo principal é aproximadamente:

`arquivo -> leitor SVG/DXF/G-code -> coordenadas/imagem -> transformações -> EGV -> USB Nano`

Os limites entre essas etapas não estão formalizados. O objeto `Application` mantém variáveis Tkinter, dados do desenho, configurações, comandos e estado da máquina. Isso dificulta testes sem abrir a interface e impede substituir apenas o backend de máquina.

Pontos de maior risco:

1. **Segurança operacional:** alterações em coordenadas, velocidade, unidades ou backend podem causar movimento inesperado do equipamento.
2. **Ausência de testes:** não existe proteção automática contra regressões geométricas ou de geração EGV.
3. **Configuração frágil:** o formato textual é analisado por buscas em linhas, sem schema, versão ou validação centralizada.
4. **Importação acoplada:** cor também representa intenção de processo, o que limita edição e futuros formatos.
5. **Dependência externa:** rasterização e conversão de texto SVG exigem Inkscape.
6. **Compatibilidade:** a base local 0.64 está atrás da versão oficial 0.71.

## Avaliação das melhorias solicitadas

Escala usada: **P** (pequena), **M** (média), **G** (grande) e **XG** (muito grande). A classificação considera implementação, testes, UX, empacotamento e risco de máquina.

| Melhoria | Dificuldade | Valor | Dependências e decisão sugerida |
|---|---:|---:|---|
| Tradução PT-BR | M | Alto | Primeiro extrair strings para catálogo; evitar tradução direta espalhada pelo código. |
| Espelhar/rotacionar/escala na UI | M | Alto | Reaproveitar matemática existente, adicionar preview e testes. |
| Array retangular | M | Alto | Criar serviço de transformação independente da UI; validar limites da mesa. |
| Predefinições de velocidade | M | Muito alto | Migrar configuração para modelo versionado; incluir velocidade, passes e processo. Potência só pode ser incluída onde o hardware permitir. |
| Troca/atribuição de cor/operacão | M–G | Alto | Separar cor visual de operação (raster, gravação, corte) no modelo interno. |
| DXF robusto | M–G | Muito alto | Preferir `ezdxf` atrás de um adaptador, mantendo o parser atual como fallback durante a migração. |
| Raster nativo | G | Muito alto | Abrir PNG/JPEG/BMP/TIFF diretamente é mais simples; renderizar SVG completo sem Inkscape exige backend como CairoSVG/resvg e estratégia para fontes/texto. |
| AI | G | Médio | Arquivos AI modernos costumam ter conteúdo PDF; suporte deve ser definido como importação compatível, não cobertura universal. |
| 3DM | G | Médio | `rhino3dm` lê geometria, mas será necessário projetar seleção/projeção 2D, unidades, camadas e tolerâncias. |
| DWG | XG | Médio | Formato complexo; normalmente requer conversão confiável para DXF por solução externa/licenciada. Não é bom candidato inicial. |
| Melhorias visuais/fluxo | G contínuo | Muito alto | Fazer por jornadas: importar, preparar, simular, executar; não apenas trocar aparência. |
| GRBL | XG | Muito alto | Exige interface de controlador, geração/streaming G-code, descoberta serial, estados, pausa/cancelamento, limites e testes com simulador antes do hardware. |

## Estratégia Git recomendada

Não foi criado um repositório Git artificial sobre o snapshot, pois isso descartaria o histórico e dificultaria atualizações futuras. A origem identificada no README é `stephenhouser/k40-whisperer`, cujo `master` corresponde ao snapshot 0.64. A fonte local foi atualizada para a versão oficial 0.71, distribuída pelo site do autor; também existe um espelho comunitário com ramo `scorchworks`.

Sequência segura:

1. Criar um fork real em uma conta/organização definida pelo responsável do projeto.
2. Clonar o fork em uma nova pasta com histórico completo.
3. Cadastrar a origem escolhida como `upstream`.
4. Importar ou atualizar para 0.71 em um commit isolado.
5. Aplicar esta documentação e futuras mudanças em branches curtas.
6. Registrar a procedência e licença GPL dos componentes.

Antes dessa operação falta apenas definir **em qual conta/organização GitHub o fork deve viver**. A criação remota não foi feita nesta avaliação.

## Critérios mínimos antes de controlar uma laser

- Simulador/dry-run que nunca abra USB/serial.
- Visualização do caminho, origem, dimensões, limites e tempo estimado.
- Testes dourados de SVG/DXF/G-code para coordenadas e saída gerada.
- Validação rígida de unidades, velocidades e área útil.
- Estados explícitos de conexão, execução, pausa, retomada, cancelamento e falha.
- Testes de bancada sem laser habilitado e checklist posterior com potência mínima/material seguro.

## Conclusão

Há valor em evoluir este software, especialmente para uma operação padronizada entre máquinas. O ativo mais importante é o conhecimento de protocolo e preparação já existente. A dívida principal é estrutural, não cosmética. A rota de menor risco é estabilizar e modularizar a base, entregar melhorias de uso de alto valor e somente então introduzir novos backends de controladora.
