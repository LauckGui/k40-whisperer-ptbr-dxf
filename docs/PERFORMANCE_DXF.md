# Desempenho da importação DXF

## Baseline sintético

Medição inicial em 14 de setembro de 2026, no Python 3.14, usando um DXF R2010
com 5.000 entidades `LINE`:

| Métrica | Resultado |
|---|---:|
| Objetos convertidos | 5.000 |
| Tempo total | 5,27 s |
| Pico medido por `tracemalloc` | 16,17 MiB |
| Eventos de progresso | 45 |
| Intervalo de atualização | 250 entidades |

O valor não representa arquivos reais com splines ou blocos complexos e deve ser
usado somente como baseline para detectar regressões. O custo do documento
mantido internamente pelo `ezdxf` não é inteiramente observado pelo
`tracemalloc`.

## Arquitetura atual

- leitura em worker thread para manter o Tkinter responsivo;
- diálogo e alterações de widgets exclusivamente na thread principal;
- cancelamento cooperativo entre fases e entidades;
- análise e conversão incrementais, sem reter o conjunto completo de pontos
  achatados;
- progresso por fases e lotes;
- publicação atômica: um documento incompleto nunca substitui o trabalho atual.

Curvas analíticas são discretizadas por desvio geométrico máximo, e não por uma
quantidade fixa de segmentos. Arcos calculam diretamente a maior corda permitida
pela sagita; Béziers são subdivididas até que os controles estejam dentro da
tolerância em relação à corda. A política é centralizada e compartilhável por
preview, rotas e backends. Ela permanece serial: no arquivo real de referência,
toda a adaptação legada custa cerca de 0,68 s, tornando threads ou processos mais
caros que o trabalho que tentariam acelerar.

## Preparação das linhas raster

A extração legada percorria cada pixel em Python e recalculava o casco convexo
após cada linha de varredura. Em imagens grandes, o botão de estimativa podia
parecer travado. A implementação atual detecta transições claro/escuro com NumPy,
gera somente os intervalos em que o laser fica ligado e calcula o casco uma única
vez ao final. Um bitmap sintético de 10.000 × 5.000 pixels (50 megapixels) foi
processado localmente em aproximadamente 0,47 s, produzindo 4.801 linhas de
varredura e 9.602 coordenadas.

Falhas na preparação agora retornam estado de erro ao chamador; a interface não
substitui mais uma mensagem de falha por uma confirmação incorreta de cálculo.

O cancelamento não consegue interromper o interior de `ezdxf.readfile`; ele é
aplicado assim que essa chamada retorna. A interface, porém, continua responsiva.

## Benchmark real

No `teste_Chaveiro.dxf` ASCII de aproximadamente 207 MB, o índice topológico
original mantinha em suas células as extremidades de segmentos já consumidos.
Regiões densas voltavam a examinar esses candidatos obsoletos repetidamente. A
remoção imediata das duas extremidades reduziu a composição de 30,45 s para
21,10 s (cerca de 31%), preservando os mesmos 3 objetos, 3.498 caminhos e
108.608 segmentos. O tempo total medido caiu de 138,5 s para 123,0 s.

Uma segunda tentativa de evitar a lista temporária de candidatos não apresentou
ganho mensurável e foi descartada. A leitura ASCII pelo `ezdxf`, com cerca de
80 s nesse arquivo, permanece como o custo dominante fora do controle direto do
modelo geométrico.

## Próximos benchmarks

- arquivo real grande fornecido por operador;
- blocos repetidos e aninhados;
- elipses e splines complexas com diferentes tolerâncias;
- arrays procedurais referenciando uma única geometria-base.
