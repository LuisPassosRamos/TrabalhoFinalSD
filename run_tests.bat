@echo off
echo Executando testes do SISD...
timeout /t 1 >nul
python src\demo_test.py %* 
if %errorlevel% neq 0 (
  echo Teste falhou com código de erro %errorlevel%
)
echo Teste concluído.
