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

## Verificação sem equipamento

Os comandos abaixo não devem conectar nem enviar dados à máquina laser:

```bat
Verificar_Ambiente.bat
```

Antes de qualquer teste físico, devem existir testes de caracterização do DXF
e um modo de execução que garanta que USB não será acessado.
