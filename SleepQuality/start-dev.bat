@echo off
echo 啟動疲勞駕駛監測系統...
echo.

echo 正在安裝後端依賴...
cd /d "%~dp0"
if not exist "node_modules" (
    echo 安裝前端依賴...
    call npm install
)

echo 安裝後端依賴...
if not exist "server-node_modules" (
    call npm install --prefix . --package-lock-only --package-lock=server-package.json
    call npm install --prefix . --package-lock=server-package.json
)

echo.
echo 啟動後端服務器...
start "後端服務器" cmd /k "node server.js"

echo 等待後端服務器啟動...
timeout /t 3 /nobreak >nul

echo 啟動前端開發服務器...
start "前端服務器" cmd /k "npm run dev"

echo.
echo 系統已啟動！
echo 後端服務器: http://localhost:3001
echo 前端服務器: http://localhost:3000
echo.
echo 按任意鍵關閉此窗口...
pause >nul



