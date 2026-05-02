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
    start "Flask_Backend_SleepQuality" cmd /k "call %VENV_PATH%\Scripts\activate.bat && python app.py"
) else (
    echo [提示] 未找到虚拟环境，直接使用系统 Python 启动...
    start "Flask_Backend_SleepQuality" cmd /k "python app.py"
)

echo 等待后端服务器启动...
timeout /t 3 /nobreak >nul

echo 正在启动前端开发服务器...
start "Frontend_Vite_SleepQuality" cmd /k "npm run dev"
