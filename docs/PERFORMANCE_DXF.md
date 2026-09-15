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

O cancelamento não consegue interromper o interior de `ezdxf.readfile`; ele é
aplicado assim que essa chamada retorna. A interface, porém, continua responsiva.

## Próximos benchmarks

- arquivo real grande fornecido por operador;
- blocos repetidos e aninhados;
- círculos, elipses e splines com diferentes tolerâncias;
- comparação futura entre geometria achatada e curvas nativas;
- arrays procedurais referenciando uma única geometria-base.
