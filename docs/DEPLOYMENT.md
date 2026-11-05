# 域名部署与运维

> 可选高级部署。当前推荐 [Ubuntu 本地运行](LOCAL.md)，不需要 Docker、域名或 HTTPS。

## 部署模型

```text
浏览器 → https://papers.zhouzedong.top → Caddy（证书、HTTPS）
                                      ↓ 内部 Docker 网络
                                PawSec / Waitress
                                      ↓
                          数据卷 + AI 队列 + 定时邮件
```

当前版本只提供一个所有者工作空间。HTTP Basic 登录保护所有页面、静态文件和 API。浏览器可能在关闭标签后保留凭据；在共享电脑上请使用隐私窗口并关闭整个隐私会话。更换密码哈希并重启应用可使旧密码失效。

## 服务器和 DNS

- 起步可使用 2 核、2 GB 内存，磁盘按 PDF 数量预留。大型 PDF/OCR 需要更多内存。
- 安装 Docker Engine 和 Compose 插件。
- 子域名 A/AAAA 指向服务器，放行 80/TCP、443/TCP。443/UDP 用于 HTTP/3，可选。
- 如果域名启用了 CDN 代理，首次签发证书先使用 DNS-only 更易排查；确认 HTTPS 正常后再开启代理。不要使用回源 HTTP 的 Flexible 模式。
- 服务器已有网站占用 80/443 时，不要直接启动第二个代理。将 PawSec 接入现有反向代理，并保持应用端口仅内网可达。

## 首次启动

在服务器的源码目录运行：

```bash
cp .env.example .env
# 编辑 .env：域名、公开源码 URL、管理员用户名和 TZ
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python tools/create_admin.py
docker compose config --quiet
docker compose up -d --build
docker compose logs --tail=80 pawsec caddy
```

密码工具在终端中隐藏输入，要求至少 16 个字符，仅生成 scrypt 哈希；不会输出明文密码。不要将 `secrets/` 或 `.env` 提交到 Git。Linux 上密码工具将 `secrets/` 目录设为 0700，目录内哈希设为 0644，使 Docker 非 root 进程能够读取只读挂载的哈希，而其他主机用户无法穿过私有目录。

浏览器打开 HTTPS 域名，输入管理员账号和密码，再配置自己的模型。自动阅读、检索、邮件使用服务端网络。自动阅读和邮件默认关闭，新部署不会继承开发者配置。

## 验证

1. 未登录访问主页、`/api/papers`、`/api/models/profiles` 都应返回 401；错误域名或跨站请求应被拒绝。
2. 登录后导入一份不敏感的测试 PDF，检查阅读、笔记保存、PDF 下载。
3. 设置模型，运行一篇自动阅读，等待队列完成，核对页码与原句。
4. 邮件先预览，再发送一封测试邮件；确认收件后再启用定时发送。
5. `docker compose restart pawsec` 后确认书架和设置保留。正在进行的请求可能中断，升级应等任务完成。

## API 客户端

浏览器通过同源 fetch 自动携带认证。命令行 API 写操作需要认证与 `Origin: https://你的域名`。不允许跨域调用，不启用通配 CORS。密码不应直接出现在命令行历史中。

## 数据与备份

Compose 使用 `pawsec_data` 命名卷保存 `/data`。不要执行 `docker compose down -v`，它会删除数据卷。

先等待 AI 与邮件任务完成，再停止应用取得一致备份：

```bash
mkdir -p ../pawsec-private-backups
docker compose stop pawsec
docker compose run --rm --no-deps --entrypoint tar pawsec -C /data -czf - . > ../pawsec-private-backups/pawsec-data.tar.gz
docker compose start pawsec
```

备份包含论文、邮件配置和解密密钥，应加密、限制访问并保存到私有位置。不要把 `private-backups/` 放入源码目录或提交到 Git。

迁移本机数据时，完整复制自己的 `data/`（包含 `secret.key`），不要只复制加密配置。先保留原始备份，在服务器停止状态下导入私有数据卷，修正属主为容器 UID `10001`。首次部署默认为空库；本仓库不会替你上传个人论文。

## 升级

1. 备份数据和 `.env`、密码哈希。
2. 等正在执行的 AI / 邮件任务结束。
3. 拉取新版本，确认 `PAWSEC_SOURCE_URL` 指向公开的对应版本。
4. `docker compose up -d --build`，检查日志和功能。

只有一个应用进程可以使用同一个数据目录。禁止横向扩容或多个 worker，以免定时邮件重复和 JSON 写入冲突。

## 限制

- 当前部署配置需要持续运行的主机，不适合直接放在 GitHub Pages、纯静态托管或短生命周期函数中。
- 本地 JSON/SQLite 存储和单进程队列适合个人使用；多人公开服务需要账户、隔离、配额、分布式任务和进一步安全设计。
- 依赖版本设定范围，更新依赖后应重新测试。CI 包含 Linux 测试与容器构建；未通过 CI 的版本不要作为已验证发布。
- 统计和邮件时刻使用服务器 `TZ`，迁移前检查时区。
