@echo off
chcp 65001 >nul
echo 正在安装 Python 后端依赖...
pip install -r requirements.txt

echo.
echo 正在启动后端 Flask 服务器...
set VENV_PATH=
if exist ".venv\Scripts\activate.bat" (
    set VENV_PATH=.venv
) else if exist "venv\Scripts\activate.bat" (
    set VENV_PATH=venv
) else if exist "env\Scripts\activate.bat" (
    set VENV_PATH=env
)

if defined VENV_PATH (
    start "Flask_Backend" cmd /k "call %VENV_PATH%\Scripts\activate.bat && python app.py"
) else (
    echo [错误] 找不到虚拟环境 .venv 或 venv
    pause
    exit
)

echo 等待后端服务器启动...
timeout /t 3 /nobreak >nul

echo 正在启动前端开发服务器...
start "Frontend_Vite" cmd /k "npm run dev"