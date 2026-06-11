# StockWise 海外版部署与域名配置指南

## 方案概述

在不影响国内网站 `https://guxiaozhi-ai.up.railway.app` 的前提下，为海外版配置独立域名。

## 方案一：子域名方式（推荐，成本最低）

### 假设您拥有域名：`guxiaozhi-ai.com`

#### 1. DNS 配置

在您的域名注册商（如阿里云、腾讯云、GoDaddy 等）管理后台，添加以下 DNS 记录：

| 记录类型 | 主机记录 | 记录值 | TTL |
|---------|---------|--------|-----|
| CNAME | `global` 或 `stockwise` | `guxiaozhi-ai.up.railway.app` | 600 |

配置完成后，访问地址为：
- `https://global.guxiaozhi-ai.com` 或
- `https://stockwise.guxiaozhi-ai.com`

#### 2. Railway 配置

1. 登录 [Railway Dashboard](https://railway.app/dashboard)
2. 选择 StockWise 海外版项目
3. 进入 Settings → Domains
4. 点击 "Custom Domain"
5. 输入您的子域名（如 `global.guxiaozhi-ai.com`）
6. Railway 会提供验证信息，按提示完成验证

#### 3. SSL 证书

Railway 会自动为自定义域名配置 SSL 证书（Let's Encrypt），无需手动操作。

---

## 方案二：独立域名方式

### 注册新域名：`stockwise-ai.com`

#### 1. 域名注册推荐平台

| 平台 | 价格（.com首年） | 特点 |
|------|----------------|------|
| Namecheap | ~$10-15 | 隐私保护免费，性价比高 |
| Cloudflare Registrar | 批发价 ~$9 | 无加价，按成本价 |
| GoDaddy | ~$12-20 | 知名度高，经常促销 |
| 阿里云 | ~¥60-80 | 国内管理方便 |

#### 2. DNS 配置

添加 CNAME 记录指向 Railway：

| 记录类型 | 主机记录 | 记录值 | TTL |
|---------|---------|--------|-----|
| CNAME | `@`（根域名）或 `www` | `guxiaozhi-ai.up.railway.app` | 600 |

**注意**：部分 DNS 服务商不支持根域名的 CNAME，可使用以下替代方案：
- 使用 `www.stockwise-ai.com` 作为主域名
- 或使用 A 记录指向 Railway 的 IP（需咨询 Railway 支持）

#### 3. Railway 配置

同方案一的步骤 2-3。

---

## 方案三：Cloudflare 代理（推荐，带 CDN 加速）

### 优势
- 免费 CDN 加速（全球节点）
- 免费 SSL 证书
- DDoS 防护
- 页面缓存优化

### 配置步骤

#### 1. 注册 Cloudflare 账号
访问 [cloudflare.com](https://cloudflare.com)，注册免费账号。

#### 2. 添加域名
1. 点击 "Add a Site"
2. 输入您的域名（如 `stockwise-ai.com`）
3. 选择 Free 计划

#### 3. 修改 DNS 服务器
Cloudflare 会提供两个 DNS 服务器地址，如：
- `lara.ns.cloudflare.com`
- `greg.ns.cloudflare.com`

在域名注册商后台，将 DNS 服务器修改为 Cloudflare 提供的地址。

#### 4. 在 Cloudflare 添加 DNS 记录

| 类型 | 名称 | 内容 | 代理状态 |
|------|------|------|---------|
| CNAME | `global` | `guxiaozhi-ai.up.railway.app` | 已代理（橙色云） |

#### 5. 开启 SSL/TLS
1. 进入 SSL/TLS 设置
2. 选择 "Full (strict)" 模式
3. 开启 "Always Use HTTPS"

#### 6. Railway 配置

同方案一的步骤 2。

---

## 部署检查清单

### 部署前准备
- [ ] 确认国内网站 `guxiaozhi-ai.up.railway.app` 正常运行
- [ ] 准备海外版代码（已完成）
- [ ] 确认 PayPal Client ID 已配置
- [ ] 确认 Yahoo Finance API 可正常访问

### 部署步骤
1. [ ] 在 Railway 创建新项目（或在国内项目下新建服务）
2. [ ] 推送海外版代码到 GitHub
3. [ ] 连接 Railway 与 GitHub 仓库
4. [ ] 设置环境变量（PORT, NODE_ENV, PAYPAL_CLIENT_ID）
5. [ ] 部署并测试
6. [ ] 配置自定义域名
7. [ ] 测试域名访问

### 验证清单
- [ ] 首页正常显示股票列表
- [ ] 搜索功能正常
- [ ] AI 分析弹窗正常
- [ ] 登录页面正常
- [ ] 定价页面正常
- [ ] PayPal 支付按钮显示（需配置 Client ID 后才能测试支付）

---

## 常见问题

### Q: 配置域名后，国内网站会受影响吗？
A: 不会。国内网站继续使用 `guxiaozhi-ai.up.railway.app`，海外版使用新域名，两者完全独立。

### Q: 可以同时访问两个版本吗？
A: 可以。国内版（中文）和海外版（英文）可以同时运行，互不干扰。

### Q: 需要备案吗？
A: 如果使用海外服务器（如 Railway）和海外域名注册商，不需要国内备案。

### Q: SSL 证书如何配置？
A: Railway 和 Cloudflare 都会自动配置免费 SSL 证书，无需手动操作。

---

## 联系方式

如有问题，请联系：
- 邮箱：support@stockwise.com
- 反馈：https://stockwise.com/feedback
