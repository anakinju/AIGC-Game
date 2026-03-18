@echo off
echo ========================================
echo AIGC Game Demo 自动设置脚本
echo ========================================
echo.

echo 第1步：创建conda环境...
call conda create -n aigc_game python=3.10 -y
if errorlevel 1 (
    echo 错误：创建conda环境失败，请确保已安装Anaconda或Miniconda
    pause
    exit /b 1
)

echo.
echo 第2步：激活环境...
call conda activate aigc_game

echo.
echo 第3步：安装依赖包...
pip install -r requirements.txt
if errorlevel 1 (
    echo 错误：安装依赖包失败
    pause
    exit /b 1
)

echo.
echo 第4步：检查.env文件...
if not exist .env (
    echo 正在创建.env文件模板...
    copy .env.example .env
    echo.
    echo ⚠️  重要提醒：
    echo 请编辑 .env 文件，添加你的API密钥：
    echo - OPENAI_API_KEY: 在 https://platform.openai.com/ 获取
    echo - LANGCHAIN_API_KEY: 在 https://smith.langchain.com/ 获取
    echo.
    echo 按任意键打开.env文件进行编辑...
    pause >nul
    notepad .env
) else (
    echo ✅ .env文件已存在
)

echo.
echo ========================================
echo 🎉 设置完成！
echo ========================================
echo.
echo 下一步：
echo 1. 确保.env文件中的API密钥已正确设置
echo 2. 运行游戏：python run_chat.py
echo.
echo 如需启动向量数据库（可选）：
echo docker-compose up -d
echo.
pause