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

## Ubuntu 本地运行（推荐）

采用 **Local First + GitHub Source Backup**：程序在自己的 Ubuntu 电脑运行，
GitHub 只保存源码。无需 Docker、云服务器、域名、DNS 或公网 HTTPS。

~~~bash
sudo apt update
sudo apt install -y git python3 python3-venv libgomp1 fonts-noto-cjk
git clone https://github.com/2350082187zhou-ux/PawSec.git
cd PawSec
bash scripts/start.sh
~~~

首次自动安装 Python 依赖，访问 <http://127.0.0.1:8765>。
已有源码目录请直接在其中更新，不要克隆覆盖。默认沿用原有 data/。
PDF 阅读、AI、笔记、报告、邮件和本地 SQLite 均保留。

| 操作 | 命令 |
|---|---|
| 启动 | bash scripts/start.sh |
| 停止 | 启动终端 Ctrl+C，或 bash scripts/stop.sh |
| 环境检查 | bash scripts/doctor.sh |
| 完整备份（先停止） | bash scripts/backup.sh |
| 更新（先停止，自动备份） | bash scripts/update.sh |

备份默认写到 ~/PawSec-backups/，包含 PDF、笔记、数据库和解密密钥，
不会推送到 GitHub。恢复只允许写入新目录：

~~~bash
bash scripts/restore.sh "$HOME/PawSec-backups/你的备份.tar.gz" --to "$HOME/pawsec-restored"
export PAWSEC_DATA_DIR="$HOME/pawsec-restored"
bash scripts/start.sh
~~~

Python 3.12+ 为必需；Node.js 20+ 仅可选 PPTX 导出需要。
安装 Node/npm 后运行 bash scripts/setup.sh --pptx。
自动阅读和邮件初始关闭，需要在界面配置；电脑休眠或应用停止时不能执行定时任务。

**完整的启动、停止、旧数据迁移、更新和备份恢复说明：[本地使用指南](docs/LOCAL.md)。**

## 可选 Docker 部署

现有 Docker、Compose、Caddy 和公开部署登录保护继续保留，
但它们不是本地运行的依赖，本地脚本不会启动 Docker 或配置域名。
将来确实需要部署时再参考 [部署指南](docs/DEPLOYMENT.md)。

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
python tools/audit_history.py
```

测试使用临时数据和模拟模型；不需要真实 API Key，也不发送真实邮件。每个测试模块在独立进程运行，避免全局 Flask 扩展的测试状态互相影响。

应用使用 JSON 文件、SQLite 和进程内队列协调。生产环境**只启动一个 `server.py` 进程、一个副本**；不要设置多个 WSGI worker。重启后中断的自动阅读需要手动重试，邮件不会自动重发状态不明的任务。

## 许可证与贡献

本项目采用 [GNU AGPL-3.0-only](LICENSE)，与 PyMuPDF 的开源许可兼容。修改后的版本通过网络提供服务时，应依照 AGPL 向使用者提供对应源码；部署时将 `PAWSEC_SOURCE_URL` 指向实际部署版本的公开仓库，并保留界面中的源码入口。

第三方资源保留原许可，见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。论文版权、外部模型服务和评级数据授权不因本项目开源而转移。

贡献流程见 [CONTRIBUTING.md](CONTRIBUTING.md)，安全说明见 [SECURITY.md](SECURITY.md)。
