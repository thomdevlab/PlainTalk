@echo off
echo AutoCompiler - PlainTalk Development Tool (thomdevlab)
echo =====================================================
echo.

:: Configuração de URLs (Organização: thomdevlab | Branch: b1)
set URL_NORMAL=https://raw.githubusercontent.com/thomdevlab/PlainTalk/b1/src/
set URL_PREBUILT=https://github.com/thomdevlab/PlainTalk/releases/download/prebuiltb1/PlainTalk_b1.zip


:: Verifica se existem arquivos PlainTalk localmente
if exist *Talk*.py (
    echo Arquivos Python do PlainTalk encontrados, compilando...
    echo.
    for %%f in (*Talk*.py) do (
        echo Compilando: %%f
        python -m PyInstaller --onefile --windowed "%%f"
        echo.
    )
    echo Compilacao concluida!
    goto end
) else (
    echo Nenhum arquivo PlainTalk encontrado.
    echo O que voce gostaria de fazer?
    echo.
    echo [1] Baixar arquivos .py (Branch b1) para compilar
    echo [2] Sair
    echo [3] Ajuda
    echo [4] Baixar PlainTalk_b1.zip (Release prebuiltb1)
    echo.
    set /p Options="Escolha uma opcao: "
    echo.
    
    if "%Options%"=="1" goto option1
    if "%Options%"=="2" goto option2
    if "%Options%"=="3" goto option3
    if "%Options%"=="4" goto option4
    goto invalid
)

:option1
echo Baixando binarios .py da branch b1...
echo Fonte: %URL_NORMAL%
echo.

:: Verifica se o curl esta instalado
curl --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Erro: curl nao encontrado. Instale o curl ou use a opcao 4.
    goto end
)

:: Lista Restrita de Downloads (Os 4 principais)
echo Baixando arquivos essenciais da pasta /src/...

set files=plaintalk.py PlainTalkVM.py PlainTalkCompiler.py Talk2Exe.py

for %%a in (%files%) do (
    echo Baixando: %%a
    curl -L -o "%%a" "%URL_NORMAL%%%a"
    if %errorlevel% neq 0 echo [!] Erro ao baixar %%a
)

echo.
echo Arquivos core baixados com sucesso!
echo Voce pode rodar o AutoCompiler novamente para compilar estes arquivos.
goto end

:option2
echo Saindo do AutoCompiler...
goto end

:option3
echo AutoCompiler Help
echo ================
echo.
echo Esta ferramenta gerencia o nucleo do PlainTalk:
echo    - plaintalk.py: Interpretador principal.
echo    - PlainTalkVM.py: Maquina Virtual.
echo    - PlainTalkCompiler.py: Compilador de bytecode.
echo    - Talk2Exe.py: Conversor para executavel.
echo.
goto end

:option4
echo Baixando Release prebuiltb1...
echo URL: %URL_PREBUILT%
echo.

curl -L -o PlainTalk_b1.zip "%URL_PREBUILT%"
if %errorlevel% neq 0 (
    echo Erro ao baixar o arquivo ZIP. Verifique se a release existe.
    goto end
)

echo Extraindo arquivos...
powershell -Command "Expand-Archive -Path 'PlainTalk_b1.zip' -DestinationPath '.' -Force"

echo.
echo Pacote core baixado e extraido com sucesso!
goto end

:invalid
echo Opcao invalida.
goto end

:end
echo.
echo Operacao finalizada!
pause
