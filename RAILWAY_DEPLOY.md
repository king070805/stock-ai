# 股小智 - AI驱动的股票分析工具

## 快速部署到 Railway

### 前置条件
1. 代码推送到 GitHub 仓库
2. [Railway 账号](https://railway.app)（支持 GitHub 登录）

### 部署步骤

1. 登录 [Railway](https://railway.app)
2. 点击 **New Project** → **Deploy from GitHub repo**
3. 选择本仓库 `stock-ai`
4. Railway 会自动检测 `Procfile` 和 `requirements.txt`
5. 进入 **Variables** 标签页，添加环境变量：
   - `DEEPSEEK_API_KEY` = 你的 DeepSeek API Key
6. 进入 **Settings** → 设置端口为 `5000`
7. 部署完成后，Railway 会分配一个公网 URL

### 本地运行

```bash
pip install -r requirements.txt
export DEEPSEEK_API_KEY=your_api_key_here
python app.py
```

访问 http://localhost:5000
