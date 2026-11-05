# Ubuntu 本地运行：Local First + GitHub Source Backup

PawSec 在自己的 Ubuntu 电脑运行，固定访问 http://127.0.0.1:8765。
GitHub 只保存程序源码和更新记录，不是论文库或凭据的备份。
不需要域名、DNS、Tunnel、HTTPS、Docker 或云服务器。
原有 PDF 阅读、AI 自动阅读、笔记、报告、邮件和 SQLite 功能均保留。

## 首次安装与启动

推荐 Ubuntu 24.04 LTS、Python 3.12+。在普通用户账户操作，不要 sudo 启动应用。

```bash
sudo apt update
sudo apt install -y git python3 python3-venv libgomp1 fonts-noto-cjk
git clone https://github.com/2350082187zhou-ux/PawSec.git
cd PawSec
bash scripts/start.sh
```

首次启动自动创建项目内 .venv 并安装 Python 依赖，需要联网。
后续启动不自动安装依赖。浏览器打开 http://127.0.0.1:8765。
启动终端保持打开。可从任意工作目录执行脚本，程序仍使用项目的数据目录。

已存在源码目录时不要覆盖或重新克隆进去，先备份并按照更新步骤操作。
本次改造不会迁移、清空或覆盖旧数据。

环境检查与重新安装依赖：

```bash
bash scripts/doctor.sh
bash scripts/setup.sh
```

PDF 导出不需要 Node.js。只有可选的 PPTX 导出需要 Node.js 20+ 和 npm，
安装它们后运行 `bash scripts/setup.sh --pptx`。

## 停止

先等待 AI 和邮件任务完成，再在启动终端按 Ctrl+C；
或在另一个终端的同一源码目录执行：

```bash
bash scripts/stop.sh
```

停止脚本只向该数据目录对应、身份校验通过的 PawSec 进程发送停止信号。
不会杀掉占用相同端口的其他程序，也不会强制终止超时进程。
正在运行的 AI 任务若被打断，重启后需要在界面中手动重试。

## 数据位置与旧数据

默认整个资料库在源码目录下的 `data/`，保持原有路径，不自动迁移。
包括 PDF、paper.json 中的笔记和摘要、报告、阅读统计 SQLite、AI 队列、
模型和邮件配置以及 `secret.key`。数据库附属文件也在完整目录备份中。

如需把资料库放到源码之外，在每个执行启动、停止、备份或更新的终端使用相同设置：

```bash
export PAWSEC_DATA_DIR="$HOME/.local/share/pawsec/data"
```

设置变量不会搬迁旧数据；指向新路径会显示新的空库。
需要迁移时用下面的完整备份和恢复，不要只复制 PDF 或数据库。
本地脚本不读取部署用的 .env；本地模式不需要它。
浏览器自身保存的面板位置等偏好不属于资料库备份，论文和笔记在资料库中。

## 完整备份

先等待任务完成并停止 PawSec（老版本 python app.py 也必须退出）：

```bash
bash scripts/stop.sh
bash scripts/backup.sh
```

默认输出到 `~/PawSec-backups/pawsec-时间戳.tar.gz`，脚本显示实际文件名。
也可以指定新文件名：

```bash
bash scripts/backup.sh --output "$HOME/PawSec-backups/before-change.tar.gz"
python3 tools/local_data.py verify "$HOME/PawSec-backups/before-change.tar.gz"
bash scripts/start.sh
```

备份拒绝正在使用的数据目录、已有输出文件、数据目录内的输出位置和符号链接。
包含每个文件的 SHA-256 校验清单，完成后自动检验可解包与内容一致性。
磁盘应预留备份包和完整解包验证所需空间。

备份包含解密密钥和邮件凭据，**压缩包本身没有加密**。
Ubuntu 上目录/文件使用私有权限；请保存到加密磁盘或私有加密备份介质，
不要上传 GitHub 或分享。源码 GitHub 备份不能替代这个资料库备份。

## 恢复（不覆盖原资料）

先停止 PawSec。恢复目标必须是一个不存在的新目录：

```bash
bash scripts/restore.sh "$HOME/PawSec-backups/before-change.tar.gz" \
  --to "$HOME/.local/share/pawsec/restored-2026"
export PAWSEC_DATA_DIR="$HOME/.local/share/pawsec/restored-2026"
bash scripts/start.sh
```

脚本验证归档路径、文件类型、大小和校验和后写入新目录；
目标已存在就拒绝，不提供覆盖参数。原资料库和备份包都保留。
检查 PDF、笔记、阅读记录、模型配置和邮件设置后再决定使用哪个资料库。
恢复会包含原先的自动 AI / 邮件开关；启动前确认你希望恢复这些定时任务。
换一个目录继续使用时，后续终端也需要设置相同的 PAWSEC_DATA_DIR。

## 更新代码

先等 AI / 邮件任务完成并停止应用：

```bash
bash scripts/stop.sh
bash scripts/update.sh
bash scripts/start.sh
```

更新器在资料库锁保护下先创建完整备份，再 `git pull --ff-only`、
安装 Python 依赖并运行隔离测试。已安装 PPTX 依赖时同步更新 npm 依赖。
本地存在未提交代码、合并冲突、网络失败或测试失败时会停止；
不会 reset、clean、删除资料或自动强制推送。失败时先处理报错再启动。
新版本测试只使用临时资料，不发送真实邮件，也不调用真实模型。
如果自己修改了源码，先单独审查并提交源码，不能用强制覆盖解决。

## Git 隐私与历史审计

```bash
python3 tools/check_release.py
python3 tools/audit_history.py
```

.gitignore 排除 data、notes、papers、secrets、备份目录、.env、
PDF、SQLite / .db 及其附属文件、加密文件、私钥和备份压缩包。
不要把私人笔记放到 docs 等源码目录，也不要强制 git add -f 私人文件；
.gitignore 无法阻止人为强制添加或源码里手写的任意格式凭据。
发布检查同时检查暂存区和工作区源码；历史审计只读检查所有已获取引用和本地 reflog。
发现疑似泄漏应先报告与轮换凭据，再决定如何处理，工具不会改写历史。
模式扫描不能证明不存在任何格式的秘密。

## 运行说明

- 关闭电脑、休眠或停止 PawSec 后，自动阅读和邮件定时任务不能继续运行。
- 统计和邮件使用 Ubuntu 系统时区；可用 `timedatectl` 检查。
- Local First 指资料在本机保存。启用 AI 时，相关原文仍会发送给你配置的模型接口；
  启用邮件时，内容会发送给配置的 SMTP 服务与收件人。
- 每个资料库只运行一个进程。旧入口 `python app.py` 也会转到统一启动器。
- Docker 文件作为可选部署方式保留，详见 [部署文档](DEPLOYMENT.md)，本地流程不执行它们。
