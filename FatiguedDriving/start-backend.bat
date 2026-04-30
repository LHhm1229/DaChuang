@echo off
echo 啟動後端服務器...
echo.

echo 安裝後端依賴...
call npm install express cors ws

echo.
echo 啟動後端服務器...
node server.js

pause



