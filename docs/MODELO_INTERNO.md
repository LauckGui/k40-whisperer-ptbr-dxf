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

`RasterObject` registra:

- largura e altura em pixels;
- DPI independente em X e Y;
- dimensões físicas derivadas em milímetros;
- modo de cor e MIME type;
- origem por URI ou dados incorporados;
- transformação para posicionamento, escala, rotação e espelhamento;
- operação e referência ao objeto de origem.

Os pixels ainda não são decodificados ou rasterizados pelo núcleo. Essa escolha
permite adotar Pillow, CairoSVG ou outro backend posteriormente, mantendo o
documento e os testes estáveis. O futuro pipeline deverá separar decodificação,
composição, conversão para escala de cinza, dithering e geração das linhas de
varredura.

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
legado. Geometria com coordenada Z relevante é rejeitada em vez de ser projetada
silenciosamente no plano da máquina.

Falhas inesperadas do leitor moderno interrompem a abertura com uma mensagem de
erro. O parser antigo só pode ser usado quando o importador declarar
explicitamente uma incompatibilidade segura para fallback.

Antes do envio físico, largura, altura e posição do trabalho — incluindo
calibração, rotativo, origem e deslocamento — são comparadas com a área útil
configurada. A geração de arquivo EGV continua permitida sem essa restrição,
pois não movimenta equipamento.
