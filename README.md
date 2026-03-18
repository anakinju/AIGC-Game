# AIGC Game Demo 运行指南

这是一个基于AI的互动游戏演示，玩家可以与NPC进行对话，体验沉浸式的故事情节。

## 🎯 系统要求

- Windows 10/11 或 macOS 或 Linux
- Python 3.8 或更高版本
- Git
- 网络连接（用于下载依赖和API调用）

## 📦 第一步：安装必要软件

### 1. 安装Git
如果你还没有安装Git：
- Windows: 访问 https://git-scm.com/download/win 下载并安装
- macOS: 在终端运行 `xcode-select --install` 或访问 https://git-scm.com/download/mac
- Linux: 运行 `sudo apt-get install git` (Ubuntu/Debian) 或 `sudo yum install git` (CentOS/RHEL)

### 2. 安装Anaconda或Miniconda
推荐使用Anaconda来管理Python环境：
- 访问 https://www.anaconda.com/products/distribution 下载Anaconda
- 或访问 https://docs.conda.io/en/latest/miniconda.html 下载更轻量的Miniconda
- 安装完成后重启终端

## 🚀 第二步：下载项目代码

1. 打开终端（Windows用户可以使用Git Bash、PowerShell或命令提示符）

2. 选择一个目录来存放项目，例如桌面：
```bash
cd Desktop
```

3. 克隆项目代码：
```bash
git clone https://github.com/your-username/aigc_game.git
```
> 注意：请将上面的URL替换为实际的GitHub仓库地址

4. 进入项目目录：
```bash
cd aigc_game/aigc_game
```

## 🐍 第三步：创建Python环境

1. 创建新的conda环境：
```bash
conda create -n aigc_game python=3.10 -y
```

2. 激活环境：
```bash
conda activate aigc_game
```

## 📚 第四步：安装依赖包

在激活的环境中安装所需的Python包：


```bash
pip install --upgrade pip
pip install -r requirements.txt  # 如果项目提供了requirements.txt文件
```

## 🔑 第五步：设置API密钥

### 1. 创建环境变量文件
在项目根目录（`aigc_game/aigc_game/`）创建一个名为 `.env` 的文件：

```bash
# Windows
echo. > .env

# macOS/Linux
touch .env
```

### 2. 编辑.env文件
用文本编辑器打开 `.env` 文件，添加以下内容：

```env
# OpenAI API设置
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_BASE_URL=https://api.openai.com/v1

# LangSmith设置（用于监控NPC对话）
LANGCHAIN_TRACING_V2=true
LANGCHAIN_ENDPOINT=https://api.smith.langchain.com
LANGCHAIN_API_KEY=your_langsmith_api_key_here
LANGCHAIN_PROJECT=aigc_game_demo

```

### 3. 获取API密钥

#### OpenAI API密钥：
1. 访问 https://platform.openai.com/
2. 登录或注册账户
3. 点击右上角头像 → "View API keys"
4. 点击 "Create new secret key"
5. 复制生成的密钥，替换 `.env` 文件中的 `your_openai_api_key_here`

#### LangSmith API密钥（用于查看NPC的prompt和对话过程）：
1. 访问 https://smith.langchain.com/
2. 登录或注册账户
3. 点击左侧菜单的 "Settings"
4. 在 "API Keys" 部分点击 "Create API Key"
5. 复制生成的密钥，替换 `.env` 文件中的 `your_langsmith_api_key_here`

> **重要提示**: 
> - 请妥善保管你的API密钥，不要分享给他人
> - `.env` 文件已被添加到 `.gitignore`，不会被上传到GitHub

## 🗄️ 第六步：启动数据库（可选）

如果需要使用向量数据库功能，需要启动Milvus：

### 使用Docker启动Milvus：
1. 确保已安装Docker Desktop
2. 在项目目录运行：
```bash
docker-compose up -d
```

3. 等待几分钟让服务完全启动

如果不使用向量数据库功能，可以跳过这一步，游戏仍然可以正常运行。

## 🎮 第七步：运行游戏

1. 确保conda环境已激活：
```bash
conda activate aigc_game
```

2. 运行游戏：
```bash
python run_chat.py
```

3. 按照屏幕提示选择场景并开始游戏！

## 🎯 游戏操作说明

### 基本操作：
- 游戏启动后，会显示可用的场景列表
- 输入数字选择场景（例如输入 `0` 选择第一个场景）
- 输入 `q` 退出程序
- 在游戏中输入 `exit` 可以退出当前场景，返回场景选择

### 游戏玩法：
- 与NPC对话：直接输入你想说的话
- 查看环境：输入类似 "看看周围" 或 "观察环境" 的指令
- 执行动作：输入你想要执行的动作，如 "拿起文件" 或 "走向茶馆"

## 📊 监控NPC对话过程（LangSmith）

如果你设置了LangSmith API密钥，可以实时查看NPC的思考过程：

1. 访问 https://smith.langchain.com/
2. 登录你的账户
3. 选择项目 "aigc_game_demo"
4. 在这里你可以看到：
   - NPC接收到的prompt
   - NPC的思考过程
   - 生成的回复
   - 对话的完整链路

这对于理解NPC如何工作非常有帮助！

## 🔧 故障排除

### 常见问题：

#### 1. 导入错误 (ImportError)
```bash
# 重新安装依赖
pip install --force-reinstall langchain langchain-openai langgraph
```

#### 2. API密钥错误
- 检查 `.env` 文件是否存在且格式正确
- 确认API密钥没有多余的空格或引号
- 验证API密钥是否有效且有足够的额度

#### 3. 网络连接问题
- 确保网络连接正常
- 如果在中国大陆，可能需要配置代理

#### 4. Python环境问题
```bash
# 重新创建环境
conda deactivate
conda remove -n aigc_game --all
conda create -n aigc_game python=3.10 -y
conda activate aigc_game
# 重新安装依赖...
```

#### 5. 数据库连接问题
- 检查Docker是否正常运行
- 确认端口19530没有被其他程序占用
- 如果不需要向量数据库功能，可以忽略相关错误

### 获取帮助：
如果遇到其他问题，请：
1. 检查终端输出的错误信息
2. 确认所有步骤都已正确执行
3. 联系技术支持或查看项目文档

## 📝 项目结构

```
aigc_game/
├── run_chat.py          # 主程序入口
├── .env                 # 环境变量配置（需要自己创建）
├── docker-compose.yml   # Docker配置文件
├── npc/                 # NPC相关代码
│   ├── data/
│   │   └── demo.json    # 演示场景数据
│   ├── multi_npc/       # 多NPC系统
│   └── single_npc/      # 单NPC系统
├── memory/              # 记忆系统
└── main/                # 主要运行逻辑
```

## 🎉 开始体验

现在你已经完成了所有设置！运行 `python run_chat.py` 开始你的AI游戏之旅吧！

游戏中你将体验到：
- 智能NPC对话
- 沉浸式故事情节
- 动态环境互动
- 个性化游戏体验

祝你游戏愉快！ 🎮✨

---

## 📞 技术支持

如果在设置过程中遇到任何问题，请：
- 仔细检查每个步骤是否正确执行
- 查看终端输出的错误信息
- 确认API密钥设置正确
- 联系开发团队获取帮助

**重要提醒**: 请确保你的OpenAI账户有足够的API使用额度，否则游戏将无法正常运行。