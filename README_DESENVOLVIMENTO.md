# Desenvolvimento do K40 Whisperer

## Ambiente Python no Windows

Execute `Preparar_Ambiente.bat` na primeira utilização em cada computador.
O script cria uma instância isolada em `.venv-<NOME_DO_PC>` e instala as
versões registradas em `requirements.txt`.

Ambientes virtuais Python não são portáveis: eles contêm binários e caminhos
absolutos da máquina onde foram criados. O nome por computador impede que uma
instância sincronizada pelo OneDrive substitua a instância válida de outro PC.
As pastas `.venv-*` não fazem parte do repositório Git.

Para iniciar o programa, execute `Executar_K40_Whisperer.bat`. O launcher
verifica o ambiente correspondente ao computador e chama automaticamente a
preparação quando ele estiver ausente ou incompleto.

## Escopo atual

O desenvolvimento está concentrado no suporte DXF. A dependência `ezdxf` está
fixada para a futura integração do importador moderno. SVG e G-code existentes
continuam preservados para compatibilidade; 3DM, DWG e novos formatos não fazem
parte da etapa ativa.

O pacote `k40core` contém o modelo canônico independente de interface e
hardware. Toda geometria é normalizada para milímetros, enquanto unidade,
camada, identificador, tipo e atributos originais permanecem rastreáveis. O
modelo admite caminhos vetoriais e imagens raster posicionadas fisicamente.

## Projetos de produção

O formato `.k40p` é um arquivo ZIP versionado e autocontido. Ele guarda o
documento canônico, curvas analíticas, arrays procedurais, imagens e máscaras,
alinhamento, posição na mesa, parâmetros dos processos e coordenadas já
calculadas. O manifesto usa JSON e os bitmaps são incorporados como PNG; não há
desserialização executável por `pickle`.

As opções **Novo**, **Abrir**, **Salvar** e **Salvar como** ficam no menu
Arquivo. Preferências globais da máquina continuam no arquivo de configuração
do aplicativo e apenas os parâmetros ligados à produção são restaurados por um
projeto.

Raster de preenchimentos DXF e imagens anexadas a peças com múltiplas cópias
permanecem como um único bitmap fonte. A prévia reutiliza essa imagem e as
rotas raster são calculadas uma vez, depois instanciadas pelos deslocamentos do
array. Assim, a memória de pixels não cresce com o número de peças e o
grayscale continua alinhado aos vetores. Posições podem ser ignoradas ou
reativadas com um clique na prévia do array, sem explodir as instâncias.

## Verificação sem equipamento

Os comandos abaixo não devem conectar nem enviar dados à máquina laser:

```bat
Verificar_Ambiente.bat
```

Antes de qualquer teste físico, devem existir testes de caracterização do DXF
e um modo de execução que garanta que USB não será acessado.

## Instalador para Windows

O empacotamento não depende de Python no computador de destino. O PyInstaller
gera a aplicação e o Inno Setup cria o instalador tradicional com atalhos e
desinstalador.

1. Instale o Inno Setup 6 uma vez no computador de desenvolvimento:
   `winget install --id JRSoftware.InnoSetup -e`
2. Execute `Construir_Instalador.bat`.
3. O instalador e o pacote portátil ZIP serão criados na pasta `Output`, ao
   lado do repositório.

O script instala a versão fixada do PyInstaller no ambiente virtual local,
executa todos os testes e interrompe o build se qualquer teste falhar.
Os arquivos intermediários são produzidos na pasta temporária do Windows para
evitar bloqueios de sincronização quando o projeto estiver dentro do OneDrive.

O instalador empacota a aplicação, mas não altera o driver USB da controladora.
O computador de destino ainda precisa ter um driver libUSB compatível com a
placa K40, como já ocorre na distribuição padrão do K40 Whisperer.
