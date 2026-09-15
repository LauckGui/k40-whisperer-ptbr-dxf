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
arcos e Bézier cúbicas. Nesta primeira etapa, o DXF converte curvas em linhas
usando uma tolerância explícita e registra essa tolerância no objeto. A evolução
posterior poderá preservar curvas nativas sem alterar o restante do documento.

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

## Compatibilidade legada

`k40core.legacy.vector_lines_in_inches` converte vetores achatados para a lista
`[x0, y0, x1, y1]` em polegadas atualmente consumida por `ECoord`. O adaptador é
temporário e permite integrar o novo modelo sem reescrever de imediato o envio
para a controladora Nano.

## Próximos incrementos DXF

1. Criar fixtures versionadas de entidades DXF e resultados dourados.
2. Definir a matriz de entidades suportadas e comportamento por versão DXF.
3. Preservar arcos, círculos, elipses e splines sem achatamento prematuro.
4. Tratar blocos, inserções, transformações, layers ocultos e propriedades BYLAYER.
5. Integrar o novo documento ao fluxo `Open_DXF`, mantendo fallback controlado.
6. Comparar coordenadas e limites com o parser legado antes de torná-lo padrão.

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

A análise do plano e a conversão percorrem as entidades incrementalmente. Os
pontos achatados de cada entidade são liberados antes do próximo lote, evitando
manter uma segunda cópia completa da geometria na memória. O importador publica
as fases de leitura, análise, conversão e conclusão, com atualização a cada 250
entidades. Não há paralelização interna de entidades: isso preserva ordem e
determinismo e evita compartilhar estruturas do `ezdxf` entre threads.

Essa arquitetura também prepara o futuro array procedural: uma instância poderá
referenciar a mesma geometria-base e aplicar apenas sua transformação, sem gerar
cópias vetoriais durante importação ou preparação.
