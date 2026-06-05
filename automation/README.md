# 股小智 · n8n 自动化中心

> 本地 Docker 部署的 n8n 工作流集群，覆盖每日简报、异动预警、数据看板、代码自动修复四大场景。

---

## 目录结构

```
automation/
├── docker-compose.yml          # Docker 一键启动
├── .env.example                # 环境变量模板
├── README.md                   # 本文档
├── workflows/                  # 工作流 JSON（可直接导入 n8n）
│   ├── daily-briefing.json     # 每日简报 → 小红书
│   ├── stock-alert.json        # 异动预警 → 微信/邮件
│   ├── dashboard-update.json   # 看板更新 → HTML报告
│   └── auto-fix.json           # 错误监听 → Codex修复 → GitHub PR
└── scripts/                    # 辅助脚本
    └── import-workflows.sh     # 批量导入工作流
```

---

## 快速开始

### 1. 安装 Docker

```bash
# Windows/Mac: 下载 Docker Desktop
# Linux:
curl -fsSL https://get.docker.com | sh
```

### 2. 配置环境变量

```bash
cd automation
cp .env.example .env
# 用编辑器打开 .env，填入所有真实值
```

### 3. 启动 n8n

```bash
docker-compose up -d
```

### 4. 访问控制台

打开 http://localhost:5678  
用户名/密码：见 `.env` 中的 `N8N_USER` / `N8N_PASSWORD`

### 5. 导入工作流

**方式A：手动导入**
- 进入 n8n → Workflows → Import from File
- 依次导入 `workflows/` 目录下的4个 JSON 文件

**方式B：脚本导入（推荐）**
```bash
# 先获取 n8n API Key（在 n8n Settings 中生成）
export N8N_API_KEY=your_api_key
bash scripts/import-workflows.sh
```

---

## 四大工作流说明

### 1. 每日简报自动化 `daily-briefing.json`

| 节点 | 功能 |
|------|------|
| 每日早9点触发 | cron 定时器 |
| 获取TOP10涨跌股 | 调用 `/api/stocks?sort=change` |
| 获取TOP10成交额 | 调用 `/api/stocks?sort=amount` |
| 生成AI市场简报 | 调用 `/api/briefing` |
| 组装小红书文案 | JS代码节点拼接文案+话题标签 |
| 发布到小红书 | HTTP请求第三方发布API |
| 通知Slack/飞书 | 发送执行结果通知 |

**触发时间**：每天上午9:00（北京时间）

---

### 2. 用户异动预警 `stock-alert.json`

| 节点 | 功能 |
|------|------|
| 每30分钟巡检 | 高频定时器 |
| 获取全市场数据 | 拉取前100只股票 |
| 筛选异动股票 | JS代码：涨跌幅>5% 或 量比>3 |
| 获取用户关注清单 | 读取所有用户自选股 |
| 匹配用户关注 | 交集计算，生成个性化通知 |
| 推送微信通知 | 飞书/企业微信机器人 |
| 发送邮件备份 | SMTP邮件告警 |

**预警规则**：
- 涨跌幅绝对值 > 5%
- 成交量比 > 3（放量异动）

---

### 3. 数据看板更新 `dashboard-update.json`

| 节点 | 功能 |
|------|------|
| 每5分钟刷新 | 高频定时器 |
| 获取统计数据 | 调用 `/api/stats` |
| 获取热门股票 | 调用 `/api/stocks?sort=amount&size=5` |
| 组装看板数据 | JS代码聚合数据 |
| 推送看板更新 | POST到项目API |
| 生成HTML报告 | 生成独立HTML文件 |
| 保存看板报告 | 写入 `/data/dashboard-reports/` |

**输出**：`dashboard-YYYY-MM-DD.html` 可独立打开查看

---

### 4. 代码自动修复 `auto-fix.json`

| 节点 | 功能 |
|------|------|
| 监听工作流错误 | Error Trigger 节点 |
| 提取错误信息 | JS代码格式化错误报告 |
| Codex分析修复 | 调用 Codex API 分析堆栈 |
| 提取修复代码 | 从AI回复中解析代码块 |
| 创建GitHub PR | 自动创建 Issue/PR |
| 通知开发团队 | Slack通知修复摘要 |

**触发条件**：其他工作流执行失败时自动触发

---

## 环境变量清单

| 变量 | 必填 | 说明 |
|------|------|------|
| `N8N_USER` | ✅ | n8n登录用户名 |
| `N8N_PASSWORD` | ✅ | n8n登录密码 |
| `STOCK_API_URL` | ✅ | 股小智项目API地址 |
| `XIAOHONGSHU_API_URL` | ⚠️ | 小红书发布API（需自行接入） |
| `WECHAT_WEBHOOK_URL` | ⚠️ | 飞书/企业微信机器人Webhook |
| `SMTP_HOST` | ⚠️ | 邮件服务器（告警用） |
| `CODEX_API_URL` | ⚠️ | Codex API地址（自动修复用） |
| `GITHUB_TOKEN` | ⚠️ | GitHub Personal Access Token |
| `SLACK_WEBHOOK_URL` | ❌ | Slack通知（可选） |

---

## 故障排查

### n8n 启动失败

```bash
# 查看日志
docker-compose logs -f n8n

# 常见原因：端口被占用
# 解决：修改 docker-compose.yml 中的 ports 映射
```

### 工作流执行失败

1. 检查 `.env` 中的 API 地址是否正确
2. 确认股小智项目正在运行（`python app.py`）
3. 在 n8n 中查看 Execution 日志定位具体节点

### 小红书发布失败

- 小红书无官方开放API，需通过第三方SaaS或RPA工具接入
- 临时方案：改为生成 Markdown 文件，手动复制发布

### 微信通知收不到

- 确认飞书/企业微信机器人Webhook地址正确
- 检查机器人是否有发送权限

---

## 进阶配置

### 接入 PostgreSQL（生产推荐）

取消 `docker-compose.yml` 中 postgres 部分的注释，n8n 数据将持久化到数据库而非 SQLite。

### HTTPS 部署

使用 Nginx 反向代理 + Let's Encrypt 证书：

```nginx
server {
    listen 443 ssl;
    server_name n8n.yourdomain.com;
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    location / {
        proxy_pass http://localhost:5678;
        proxy_set_header Host $host;
    }
}
```

### 备份工作流

```bash
# 导出所有工作流
docker exec guxiaozhi-n8n n8n export:workflow --all --output=/backup/workflows/
```

---

## 更新日志

| 日期 | 版本 | 说明 |
|------|------|------|
| 2026-06-04 | v1.0 | 初始版本，4条核心工作流 |

---

*Powered by n8n + 股小智*