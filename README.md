# PawSec 汪安

自托管的 AI 论文阅读与研究汇报工作台。导入 PDF、整理重点、回看原文证据，记录自己的阅读进展。

## 功能

- PDF 阅读、选段问答、四色高亮和笔记；引用页码可跳转原文。
- 自动 AI 阅读：导入后排队，生成摘要、核心重点、方法、实验结果、局限、复现要点、关键词与术语解释。
- 原句匹配核验，显示未核实证据、文字不足页面；AI 读过不会计入人的阅读时长。
- 可编辑的日报、周报、月报，导出 PDF、Markdown 和 JSON。
- 已读论文与相关新论文的邮件简报，支持 SMTP、发送时刻、关键词和 PDF 附件。
- 多模型档案；兼容 Chat Completions、Responses 和 Claude Messages 协议。
- 中文、英语、日语、韩语界面；AI 结果语言可配置。已存笔记和原始论文不会随界面语言自动改写。
- 浮动伴读默认收起，可拖动并记忆位置，不占用问答面板高度。

## 适用范围

这是**单所有者工作台**。本机模式仅监听 `127.0.0.1:8765`。公网模式使用 HTTPS 反向代理和管理员登录，所有数据属于同一个工作空间。

它目前没有多用户数据隔离、访客额度或公开注册。不要把管理员账号分享给陌生人，也不要把它作为无需登录的公共 AI 服务。

## 本机运行

需要 Python 3.12+。PPTX 导出还需要 Node.js 20+。

```bash
python -m venv .venv
# Linux / macOS
source .venv/bin/activate
# Windows PowerShell 则使用：.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
npm ci --omit=dev
python app.py
```

访问 <http://127.0.0.1:8765>，在「模型连接」中填写自己的服务地址、模型和 API Key。自动阅读和邮件发送初始关闭，需要在界面设置。

## 部署到自己的域名

需要一台能持续运行的 Linux 服务器及 Docker Compose。推荐使用 `papers.zhouzedong.top` 这样的独立子域名。当前前端使用根路径，不支持直接挂到 `/papers/` 子路径。

1. 将子域名 A 记录指向服务器 IPv4；如使用 AAAA，确保 IPv6 也通畅。
2. 在服务器克隆代码，复制 `.env.example` 为 `.env`，填写域名、管理员用户名、公开源码地址和时区。
3. 生成管理员密码文件，然后启动：

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python tools/create_admin.py
docker compose up -d --build
```

Caddy 使用 80/443 端口签发和续期证书。浏览器访问你的域名时弹出管理员登录框。详细操作、备份和升级见 [部署指南](docs/DEPLOYMENT.md)。

公网启动缺少域名或密码哈希时会直接失败。应用端口不映射到宿主机；请勿另外开放 8765，也不要绕过代理暴露 Flask 开发服务器。

## 数据与隐私

- `data/` 或 `PAWSEC_DATA_DIR` 保存 PDF、笔记、报告、任务、邮件配置和模型密钥。
- 密钥配置经过加密，但解密密钥 `secret.key` 与数据同存。能读取完整数据目录的人也能解密配置；必须保护服务器和备份。
- AI 阅读、问答和 OCR 会把相关原文或页面图片发送给你配置的模型服务，并产生用量。
- OpenAlex 等检索服务会收到搜索关键词。邮件仅发送到自己配置的收件地址。
- 代码仓库不包含个人论文、真实密钥、SMTP 账号、浏览器会话或私有备份。

## 开发与测试

```bash
python tools/run_tests.py
python tools/check_release.py
```

测试使用临时数据和模拟模型；不需要真实 API Key，也不发送真实邮件。每个测试模块在独立进程运行，避免全局 Flask 扩展的测试状态互相影响。

应用使用 JSON 文件、SQLite 和进程内队列协调。生产环境**只启动一个 `server.py` 进程、一个副本**；不要设置多个 WSGI worker。重启后中断的自动阅读需要手动重试，邮件不会自动重发状态不明的任务。

## 许可证与贡献

本项目采用 [GNU AGPL-3.0-only](LICENSE)，与 PyMuPDF 的开源许可兼容。修改后的版本通过网络提供服务时，应依照 AGPL 向使用者提供对应源码；部署时将 `PAWSEC_SOURCE_URL` 指向实际部署版本的公开仓库，并保留界面中的源码入口。

第三方资源保留原许可，见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。论文版权、外部模型服务和评级数据授权不因本项目开源而转移。

贡献流程见 [CONTRIBUTING.md](CONTRIBUTING.md)，安全说明见 [SECURITY.md](SECURITY.md)。
