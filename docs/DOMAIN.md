# papers.zhouzedong.top 部署记录

已确认（2026-11-04）：
- 主域名 zhouzedong.top 的 DNS 由 launch1.spaceship.net / launch2.spaceship.net 管理。
- 主站指向 GitHub Pages；现有主页保持原样。
- papers.zhouzedong.top 尚无 A 记录。
- 公开仓库：https://github.com/2350082187zhou-ux/PawSec（代码已发布）。

## 下一步

1. GitHub Public 仓库 PawSec 已创建，干净的源码已推送。
2. 后续更新只从这份干净源码目录提交。推送前运行 python tools/check_release.py，不要提交运行数据、token、API Key 或密码。
3. 准备持续运行的 Linux 服务器（推荐 Ubuntu 24.04，2核/2GB起，安装 Docker Compose）。服务器公网 IP 确定前不要随便填 DNS。
4. Spaceship 域名管理中打开 zhouzedong.top 的 DNS / Advanced DNS，新增 A 记录：Host= papers，Value=服务器公网IPv4，TTL=默认。不要改动 @、www 或现有主页记录。未配置IPv6服务器时不要新增AAAA。
5. 在服务器克隆仓库，按照 DEPLOYMENT.md 配置 .env、管理员密码并运行 docker compose up -d --build。
6. 验证 HTTPS、未登录拒绝访问、登录后空书架、导入测试文献和数据持久化。

## 当前状态与隐私

当前源码准备的是单所有者登录版；多人注册没有实现，不应开放共享注册。若本次需要多人版，必须先增加账户、独立数据目录、权限检查和队列隔离。

开源目录不包含你的 API 密钥、真实模型配置、论文、笔记、邮件配置或备份。新服务器以空库启动；私有数据迁移必须另行明确处理。
