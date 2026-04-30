echo 安裝 Python 後端依賴...
pip install -r requirements.txt

echo.
echo 啟動後端 Flask 服務器...
REM 直接使用當前目錄，避免在新 cmd 中使用 %~dp0 導致“當前目錄無效”
start "後端 Flask 服務器" cmd /k "call venv\Scripts\activate.bat && python app.py"

echo 等待後端服務器啟動...
timeout /t 3 /nobreak >nul

echo 啟動前端開發服務器...
REM 新開的 cmd 會繼承當前目錄，無需再次 cd /d "%~dp0"
start "前端服務器" cmd /k "npm run dev"