# Modelo interno de trabalhos

## Objetivo

O pacote `k40core` estabelece uma fronteira entre os formatos importados, a
interface e as controladoras. Um importador produz um `JobDocument`; etapas de
preparação transformam esse documento; um backend converte o resultado para o
protocolo da máquina.

## Decisões de base

- Toda geometria interna usa milímetros. A unidade original continua registrada.
- Cor visual e operação de máquina são propriedades distintas.
- Objetos preservam camada, identificador, tipo e atributos da fonte.
- Avisos de importação possuem código, gravidade, origem e detalhes pesquisáveis.
- Transformações ficam associadas ao objeto e não destroem a geometria importada.
- Metadados permitem extensões de formatos sem aumentar o núcleo a cada atributo.
- O modelo não importa Tkinter, Pillow, ezdxf nem bibliotecas de hardware.

## Vetores

`VectorObject` contém um ou mais `VectorPath`. O contrato já prevê linhas,
arcos e Bézier cúbicas. O DXF preserva linhas e comandos Bézier analíticos no
documento canônico; quadráticas são convertidas exatamente para Bézier cúbicas.
A discretização só acontece na fronteira do backend legado, usando tolerância
explícita, sem contaminar o modelo interno com segmentos de aproximação.

O mapeamento histórico azul → gravação e demais cores → corte ocorre somente na
fronteira DXF. Depois da importação, `operation` pode ser alterada sem recolorir
o objeto.

## Raster

`FillObject` representa preenchimentos independentes de resolução. Ele mantém
os contornos, furos, transformação, camada, cor e regra de preenchimento de
entidades como DXF `HATCH`, `SOLID` e `TRACE`. O rasterizador interno converte
esses objetos sob demanda; divisões de uma malha de faces não se tornam linhas
de corte.

`RasterObject` registra:

- largura e altura em pixels;
- DPI independente em X e Y;
- dimensões físicas derivadas em milímetros;
- modo de cor e MIME type;
- origem por URI ou dados incorporados;
- transformação para posicionamento, escala, rotação e espelhamento;
- operação e referência ao objeto de origem.

O primeiro backend Pillow já compõe preenchimentos sólidos em uma imagem
monocromática, incluindo ilhas pela regra par/ímpar. A resolução da imagem de
trabalho é independente do número de passadas; o passo configurado seleciona
as linhas de varredura posteriormente. Padrões e gradientes ainda precisam de
backends próprios.

Cada preenchimento também possui intensidade normalizada de 0 a 1. O
rasterizador aceita um mapa opcional de cor para intensidade — por exemplo,
verde para 50% — sem vincular ainda essa política ao importador. O backend Nano
pode representar níveis por densidade/dithering; controladoras futuras com PWM
podem consumir a mesma intensidade como modulação de potência.

## Topologia e rotas

O adaptador legado reconstrói caminhos a partir de linhas explodidas usando um
índice espacial de extremidades. A busca é aproximadamente linear, aceita a
tolerância numérica de exportação, pode inverter segmentos e identifica
caminhos fechados. Camada, cor e operação delimitam os grupos que podem ser
unidos, evitando conectar processos diferentes.

O DXF agora executa essa composição ainda na thread de importação. Objetos com
camada, operação, cor, espessura e visibilidade compatíveis tornam-se um objeto
com múltiplos caminhos. Em seguida, Ramer–Douglas–Peucker remove pontos
redundantes apenas de caminhos formados integralmente por linhas. Curvas
analíticas não são simplificadas nem achatadas. Contornos fechados permanecem
fechados, extremidades abertas são preservadas e os handles de origem ficam
registrados no objeto composto. O adaptador legado reconhece o resultado e não
repete a análise topológica.

No arquivo real `teste_Chaveiro.dxf`, a etapa reduz 13.736 objetos para 3
objetos, 3.498 caminhos e 108.608 segmentos analíticos. Esse arquivo está
totalmente explodido em linhas, portanto não se beneficia da preservação de
curvas. Em uma medição local, a importação levou 138,5 s: 79,1 s na leitura do
DXF, 16,4 s na análise, 12,6 s na conversão e 30,4 s na composição. A adaptação
final para 108.608 linhas legadas levou apenas 0,68 s.

## Compatibilidade legada

`k40core.legacy.vector_lines_in_inches` discretiza curvas sob demanda e converte
os vetores para a lista `[x0, y0, x1, y1]` em polegadas atualmente consumida
por `ECoord`. O adaptador é temporário e permite integrar o novo modelo sem
reescrever de imediato o envio para a controladora Nano.

## Próximos incrementos DXF

1. Criar fixtures versionadas de entidades DXF e resultados dourados.
2. Definir a matriz de entidades suportadas e comportamento por versão DXF.
3. Ampliar fixtures analíticas para elipses e splines complexas.
4. Comparar coordenadas e limites com aplicações CAD de referência.

## Regressões DXF conhecidas

O parser legado lia centros de círculos diretamente em OCS. Entidades com
normal negativa no eixo Z eram posicionadas com o X invertido. O importador
`ezdxf` aplica a transformação OCS → WCS e passou a ser usado primeiro pelo
fluxo `Open_DXF`; o comportamento está protegido por teste automatizado.

O importador também resolve herança de camada e cor em blocos `INSERT`, respeita
cores True Color e mantém layers ocultos fora da saída enviada ao backend
legado. Para geometria 3D, o modo automático reconhece desenhos contidos nos
planos XY, XZ ou YZ e registra a projeção como aviso estruturado. Geometria que
não esteja em um desses planos exige a escolha explícita de XY, XZ ou YZ; assim
a projeção continua disponível sem acontecer silenciosamente.

Falhas inesperadas do leitor moderno interrompem a abertura com uma mensagem de
erro. O parser antigo só pode ser usado quando o importador declarar
explicitamente uma incompatibilidade segura para fallback.

Antes do envio físico, largura, altura e posição do trabalho — incluindo
calibração, rotativo, origem e deslocamento — são comparadas com a área útil
configurada. A geração de arquivo EGV continua permitida sem essa restrição,
pois não movimenta equipamento.

## Importação de arquivos grandes

A abertura DXF é executada em uma thread de trabalho; somente a fila de eventos
e os diálogos são tratados pela thread do Tkinter. O desenho anterior permanece
ativo até que o novo documento esteja completo e validado. O operador pode
cancelar usando **Parar**.

Uma barra de progresso temporária aparece acima do status. Ela é indeterminada
durante leitura e análise inicial; após a contagem das entidades convertíveis,
passa ao modo percentual durante a conversão e chega a 100% antes da publicação
do documento.

A análise do plano de projeção decompõe cada entidade uma única vez e conserva
temporariamente seus comandos analíticos. A conversão reutiliza esses comandos,
eliminando o segundo percurso de decomposição e o segundo achatamento que antes
dominavam o tempo de arquivos densos. Apenas preenchimentos são discretizados
para o rasterizador. O importador publica
as fases de leitura, análise, conversão e conclusão, com atualização a cada 250
entidades. Não há paralelização interna de entidades: isso preserva ordem e
determinismo e evita compartilhar estruturas do `ezdxf` entre threads.

Essa arquitetura também prepara o futuro array procedural: uma instância poderá
referenciar a mesma geometria-base e aplicar apenas sua transformação, sem gerar
cópias vetoriais durante importação ou preparação.

## Arrays procedurais

`InstanceArray` referencia os IDs dos objetos-base e armazena somente linhas,
colunas, modo, espaçamento e ajustes de deslocamento. Grade e zig-zag compartilham
a mesma geometria; a linha alternada do zig-zag recebe um desvio X configurável e
o avanço vertical aceita ajuste Y. O objeto original é sempre a primeira cópia.

Limites e preenchimento da área útil são calculados diretamente pelas
transformações das instâncias. A janela **Múltiplas Cópias** usa envelopes leves
para atualizar o encaixe sem clonar os vetores e desenha a área de corte na
proporção configurada da máquina. A expansão em coordenadas ocorre somente na
fronteira legada, em uma thread de trabalho, enquanto o documento canônico
continua contendo uma única geometria-base. Preenchimentos sólidos pertencem ao
mesmo array e são rasterizados novamente com os deslocamentos das instâncias.

## Configuração persistente

As preferências são gravadas atomicamente em `k40_whisperer.config.json`, com
schema JSON versionado. O arquivo fica ao lado do aplicativo para acompanhar a
pasta sincronizada entre computadores e é ignorado pelo Git por conter escolhas
locais. Alterações são consolidadas automaticamente após 500 ms e novamente ao
fechar. Na primeira execução, o TXT legado é importado e migrado. Um arquivo de
exemplo versionado documenta o formato, e a opção **Resetar configurações**
restaura os padrões internos sem apagar trabalhos.
