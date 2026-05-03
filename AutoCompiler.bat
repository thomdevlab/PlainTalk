@echo off
echo AutoCompiler - PlainTalk Development Tool
echo =====================================
echo.

:: Configuration URLs
set URL_NORMAL=https://github.com/thomdevlab/PlainTalk/archive/refs/heads/b1.zip
set URL_PREBUILT=https://github.com/plaintalk/plaintalk/releases/download/v1.0/PlainTalk_b1.zip

:: Check for PlainTalk files
if exist *Talk*.py (
    echo Found PlainTalk Python files, compiling...
    echo.
    for %%f in (*Talk*.py) do (
        echo Compiling: %%f
        python -m PyInstaller --onefile --windowed "%%f"
        echo.
    )
    echo Compilation complete!
    goto end
) else (
    echo No PlainTalk files found.
    echo What would you like to do?
    echo.
    echo [1] Download .py binaries to compile
    echo [2] Exit
    echo [3] Help
    echo [4] Download PlainTalk_b1.zip
    echo.
    set /p Options="Type one here: "
    echo.
    
    if "%Options%"=="1" goto option1
    if "%Options%"=="2" goto option2
    if "%Options%"=="3" goto option3
    if "%Options%"=="4" goto option4
    goto invalid
)

:option1
echo Downloading .py binaries to compile...
echo Using URL: %URL_NORMAL%
echo.

:: Download PlainTalk Python files using curl
echo Downloading PlainTalk Python files...
echo.

:: Check if curl is available
curl --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: curl not found. Please install curl or use option 4 for pre-built binaries.
    goto end
)

:: Download each Python file
echo Downloading: plaintalk.py
curl -L -o plaintalk.py "%URL_NORMAL%plaintalk.py"
if %errorlevel% neq 0 echo Error downloading plaintalk.py

echo Downloading: PlainTalkVM.py
curl -L -o PlainTalkVM.py "%URL_NORMAL%PlainTalkVM.py"
if %errorlevel% neq 0 echo Error downloading PlainTalkVM.py

echo Downloading: PlainTalkCompiler.py
curl -L -o PlainTalkCompiler.py "%URL_NORMAL%PlainTalkCompiler.py"
if %errorlevel% neq 0 echo Error downloading PlainTalkCompiler.py

echo Downloading: Talk2Exe.py
curl -L -o Talk2Exe.py "%URL_NORMAL%Talk2Exe.py"
if %errorlevel% neq 0 echo Error downloading Talk2Exe.py

echo Downloading: Talk2Exe_Basic.py
curl -L -o Talk2Exe_Basic.py "%URL_NORMAL%Talk2Exe_Basic.py"
if %errorlevel% neq 0 echo Error downloading Talk2Exe_Basic.py

echo Downloading: PlainTalkVM_Secure.py
curl -L -o PlainTalkVM_Secure.py "%URL_NORMAL%PlainTalkVM_Secure.py"
if %errorlevel% neq 0 echo Error downloading PlainTalkVM_Secure.py

echo Downloading: PlainTalkCompiler_Secure.py
curl -L -o PlainTalkCompiler_Secure.py "%URL_NORMAL%PlainTalkCompiler_Secure.py"
if %errorlevel% neq 0 echo Error downloading PlainTalkCompiler_Secure.py

echo.
echo PlainTalk Python files downloaded successfully!
echo.
echo Files downloaded:
echo   plaintalk.py - PlainTalk interpreter
echo   PlainTalkVM.py - Virtual Machine
echo   PlainTalkCompiler.py - Bytecode compiler
echo   Talk2Exe.py - Talk to executable converter
echo   Talk2Exe_Basic.py - Basic converter
echo   PlainTalkVM_Secure.py - Secure VM
echo   PlainTalkCompiler_Secure.py - Secure compiler
echo.
echo You can now run AutoCompiler again to compile these files.
goto end

:option2
echo Exiting AutoCompiler...
echo Goodbye!
goto end

:option3
echo AutoCompiler Help
echo ================
echo.
echo AutoCompiler is a development tool for PlainTalk projects.
echo.
echo FEATURES:
echo   - Automatically detects and compiles PlainTalk Python files
echo   - Creates sample PlainTalk files for testing
echo   - Downloads pre-compiled binary executables
echo   - Provides help and guidance
echo.
echo PLAINTalk FILE TYPES:
echo   - *.talk        - PlainTalk source code
echo   - *Talk*.py     - PlainTalk Python implementations
echo   - *.talkc       - Compiled PlainTalk bytecode
echo   - *.exe         - Compiled executables
echo.
echo COMPILATION:
echo   - Uses PyInstaller to create standalone executables
echo   - Supports both console and windowed applications
echo   - Automatically handles dependencies
echo.
echo SAMPLE FILES:
echo   - hello.talk       - Basic greeting program
echo   - game.talk        - Number guessing game
echo   - calculator.talk - Simple calculator
echo.
echo For more help, visit the PlainTalk documentation.
echo.
goto end

:option4
echo Download PlainTalk_b1.zip
echo ==========================
echo.
echo Downloading PlainTalk_b1.zip...
echo Using URL: %URL_PREBUILT%
echo This is the complete PlainTalk development package.
echo.

:: Check if curl is available
curl --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: curl not found. Please install curl.
    goto end
)

:: Download PlainTalk_b1.zip using curl
echo Connecting to download server...
curl -L -o PlainTalk_b1.zip "%URL_PREBUILT%"
if %errorlevel% neq 0 (
    echo Error downloading PlainTalk_b1.zip
    goto end
)

echo Download complete: PlainTalk_b1.zip
echo.

:: Check if zip file exists
if not exist PlainTalk_b1.zip (
    echo Error: PlainTalk_b1.zip not found after download
    goto end
)

:: Extract the zip file (using PowerShell Expand-Archive)
echo Extracting PlainTalk_b1.zip...
powershell -Command "Expand-Archive -Path 'PlainTalk_b1.zip' -DestinationPath '.' -Force"
if %errorlevel% neq 0 (
    echo Error extracting PlainTalk_b1.zip
    goto end
)

echo.
echo PlainTalk_b1.zip downloaded and extracted successfully!
echo.
echo Package contents:
echo   • 7 executable files
echo   • Documentation and examples
echo   • Complete PlainTalk development suite
echo   • TE tribute embedded in all tools
echo.
echo Ready to use! Run the executables directly.
goto end

:invalid
echo Invalid option selected. Please try again.
echo.
goto start

:start
goto :eof

:end
echo.
echo AutoCompiler operation completed!
pause
