@echo off
cd /d D:\Objects\VulnScope\frontend

echo [VulnScope Frontend] 正在安装依赖...
call npm install

if %ERRORLEVEL% NEQ 0 (
    echo [VulnScope Frontend] 依赖安装失败，请手动执行 npm install
    pause
    exit /b 1
)

echo [VulnScope Frontend] 启动开发服务器...
echo [VulnScope Frontend] 地址: http://127.0.0.1:5173
echo.

call npm run dev

pause