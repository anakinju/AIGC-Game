#!/bin/bash

echo "========================================"
echo "AIGC Game Demo 自动设置脚本"
echo "========================================"
echo

# 检查conda是否安装
if ! command -v conda &> /dev/null; then
    echo "❌ 错误：未找到conda命令"
    echo "请先安装Anaconda或Miniconda："
    echo "https://www.anaconda.com/products/distribution"
    exit 1
fi

echo "第1步：创建conda环境..."
conda create -n aigc_game python=3.10 -y
if [ $? -ne 0 ]; then
    echo "❌ 错误：创建conda环境失败"
    exit 1
fi

echo
echo "第2步：激活环境..."
source $(conda info --base)/etc/profile.d/conda.sh
conda activate aigc_game

echo
echo "第3步：安装依赖包..."
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "❌ 错误：安装依赖包失败"
    exit 1
fi

echo
echo "第4步：检查.env文件..."
if [ ! -f .env ]; then
    echo "正在创建.env文件模板..."
    cp .env.example .env
    echo
    echo "⚠️  重要提醒："
    echo "请编辑 .env 文件，添加你的API密钥："
    echo "- OPENAI_API_KEY: 在 https://platform.openai.com/ 获取"
    echo "- LANGCHAIN_API_KEY: 在 https://smith.langchain.com/ 获取"
    echo
    echo "按回车键打开.env文件进行编辑..."
    read
    
    # 尝试使用不同的编辑器
    if command -v code &> /dev/null; then
        code .env
    elif command -v nano &> /dev/null; then
        nano .env
    elif command -v vim &> /dev/null; then
        vim .env
    else
        echo "请手动编辑 .env 文件"
    fi
else
    echo "✅ .env文件已存在"
fi

echo
echo "========================================"
echo "🎉 设置完成！"
echo "========================================"
echo
echo "下一步："
echo "1. 确保.env文件中的API密钥已正确设置"
echo "2. 激活环境：conda activate aigc_game"
echo "3. 运行游戏：python run_chat.py"
echo
echo "如需启动向量数据库（可选）："
echo "docker-compose up -d"
echo