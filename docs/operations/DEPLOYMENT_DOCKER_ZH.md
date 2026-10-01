# PestKG Docker 离线部署教程

## 交付内容

部署目标：Linux x86_64（amd64）单台服务器。首次访问默认英文，可切换中文。
数据版本固定为 `PestKG_A_Data_Release_v1.0`，保留 main 的 Java / DuckDB /
Parquet 架构。图谱按辖区、官方来源网站、独立参考网站分别查询。

压缩包包含：

- `images.tar`：API、前端、Caddy 三个完整镜像，可直接 `docker load`。
- `docker-compose.yml`、`Caddyfile`、`.env.example`。
- `data/releases/PestKG_A_Data_Release_v1.0/`：七个原始 Parquet 表及版本元数据。
- `data/reference-graphs/`：已提交的独立参考子图，不包括中断导入目录。
- `manifest.json`：代码提交、镜像 ID、平台和数据版本。
- `SHA256SUMS` 和本教程；包外还有 `.tar.gz.sha256`。

服务器不需要 Git、Node、Java、Maven、Neo4j，不需要从镜像仓库拉取镜像。
包中的 Compose 设置 `pull_policy: never`。HTTP 部署可离线运行；申请及续期
公开 HTTPS 证书需要联网。

## 1. 服务器准备

建议为初始研究审核部署准备 4 个 CPU、16 GB 内存、30 GB 空闲磁盘。此配置
是起步建议，不是并发容量或性能承诺。ARM64 服务器不能直接使用此 amd64 包。

需要 Docker Engine 27+、Docker Compose 插件 2.24+。已有 Docker 时先检查：

```bash
uname -m
docker version
docker compose version
df -h
```

Ubuntu 22.04 / 24.04 可按 Docker 官方软件仓库安装（需联网、sudo 权限；
已经安装 Docker 的机器跳过此段，其他发行版使用相应官方安装说明）：

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
. /etc/os-release
printf 'deb [arch=%s signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu %s stable\n' \
  "$(dpkg --print-architecture)" "$VERSION_CODENAME" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker
```

以下命令假设当前账户可使用 Docker。否则为 `docker` 命令加 `sudo`。
加入 `docker` 用户组等同授予管理员权限，应由服务器管理员决定。

## 2. 上传并校验

将交付的 `.tar.gz` 和同名 `.tar.gz.sha256` 一起上传到 `/srv/pestkg/`。
下面文件名中的 `TAG` 要替换为实际交付文件名中的标签：

```bash
cd /srv/pestkg
sha256sum -c pestkg-server-TAG-linux-amd64.tar.gz.sha256
tar -xzf pestkg-server-TAG-linux-amd64.tar.gz
cd pestkg-server-TAG-linux-amd64
sha256sum -c SHA256SUMS
docker load -i images.tar
cp .env.example .env
chmod 600 .env
```

两个校验均须全部显示 `OK`。镜像标签已写入 `.env.example`，不要自行改成
`latest`。`manifest.json` 的镜像 ID 可与 `docker image inspect` 对照。

## 3. 启动 HTTP 研究审核站点

本包默认适配已有反向代理的服务器：Caddy 容器内部使用 `80`，宿主机绑定
`127.0.0.1:18088`，HTTPS 备用端口为 `127.0.0.1:18443`。外层 Nginx、
Caddy 或云负载均衡转发到 `http://127.0.0.1:18088`，不会占用宿主机的
`80/443`。不要把 `SITE_ADDRESS` 改成 `http://:18088`，它描述的是
Caddy 容器内部监听地址，不是宿主机映射端口。

若需要直接从公网暴露 Caddy，再将 `PESTKG_BIND_ADDRESS` 改为 `0.0.0.0`，
并把 `PESTKG_HTTP_PORT` / `PESTKG_HTTPS_PORT` 改成未被占用的宿主机端口。
不要改变 Compose 右侧的容器端口 `:80`、`:443`。

```bash
docker compose config --quiet
docker compose up -d --wait --wait-timeout 300
docker compose ps
curl --fail http://127.0.0.1:18088/health/ready
curl --fail http://127.0.0.1:18088/api/v1/graph/catalog
```

浏览器通过外层反向代理访问正式域名；在服务器本机可直接打开
`http://127.0.0.1:18088/graph` 做验收。
首次查询会读取 Parquet，冷启动较慢；就绪检查与首次大查询应预留时间。

仅 Caddy 发布端口；API 的 18088 和前端容器的 80 不直接暴露到公网。
该版本为匿名只读站点，不含登录认证。审核尚未结束时，应在网络层限定
审核人员访问范围，例如 VPN / 防火墙白名单。Docker 发布端口的防火墙
规则应由管理员核实，不能仅依赖 UFW 的默认入站策略。

## 4. 验证类别搜索和数据版本

```bash
curl --fail http://127.0.0.1:18088/api/v1/graph/query \
  -H 'Content-Type: application/json' \
  -d '{"scope":"jurisdiction:AU","type":"PesticideProduct","query":"","limit":60,"provenance":true}'
```

人工验收：打开 `/graph`，默认语言为英文；主搜索框搜索 `products`，
类别应变成 `Pesticide products`；侧边搜索 `crop` 并选择 `Crops`；切换
台湾地区、ChEBI、AGROVOC 的范围；点击节点核对编号、来源及快照属性。
手机上使用侧边筛选图标展开类别列表。

界面显示的是有节点上限的查询结果，不是完整图谱规模。独立参考子图
与监管主图暂不通过未经审核的同名实体强行合并。参考包的历史导入、
有界采集、权利状态等限制仍由界面和 manifest 保留。公开发布前应完成
相应的数据分发权利审核；本次包交付不代表这些限制已消除。

## 5. 使用域名和 HTTPS

域名 DNS 指向服务器，放通 TCP 80 / 443，保持服务器可访问公开证书服务。
在 `.env` 改为实际域名，例如 `SITE_ADDRESS=pestkg.example.org`，通常保留
主机端口 80 / 443。随后：

```bash
docker compose up -d --wait --wait-timeout 300
docker compose logs --tail 100 caddy
curl --fail https://pestkg.example.org/health/ready
```

Caddy 自动处理证书。完全离线的内网环境继续使用 HTTP，或由运维人员
配置已受信任的内部证书；不要期待离线环境自动申请公网证书。

## 6. 日志、停止与备份

```bash
docker compose logs --since 30m --tail 200 api web caddy
docker stats --no-stream
docker compose restart api
docker compose down
```

`down` 不会删除数据目录或命名卷。不要使用 `down -v` 做日常停止或回滚。
Parquet 以只读方式挂载；API 导出缓存、状态、Caddy 证书均存放在命名卷。
保留完整交付包、校验文件和 `.env`。需要备份运行状态时，停止服务后使用
已加载的 Caddy 镜像读取命名卷，不会额外拉取备份镜像：

```bash
docker compose down
mkdir -p backups
for volume in api_state api_exports caddy_data caddy_config; do
  docker run --rm --pull=never --entrypoint sh \
    -v "pestkg-server_${volume}:/source:ro" -v "$PWD/backups:/backup" \
    caddy:2.11.4-alpine \
    -c "tar -czf /backup/${volume}.tar.gz -C /source ."
done
docker compose up -d --wait --wait-timeout 300
```

备份中包含 TLS 私钥等敏感信息，应控制权限并另存到受保护的位置。
以上卷名基于包中的固定 Compose 项目名 `pestkg-server`；不要随意更改项目名。

## 7. 替换部署（已有旧包时）

不要在旧目录上直接覆盖解压，也不要让新旧两套 Compose 同时启动。新旧包
固定使用同一个 Compose 项目名 `pestkg-server`，需要先停止旧容器，再启动
新目录中的容器；命名卷会被保留，`down` 不会删除卷。

```bash
cd /srv/pestkg
sha256sum -c pestkg-server-NEW_TAG-linux-amd64.tar.gz.sha256
tar -xzf pestkg-server-NEW_TAG-linux-amd64.tar.gz
cd pestkg-server-NEW_TAG-linux-amd64
sha256sum -c SHA256SUMS
docker load -i images.tar
cp .env.example .env
chmod 600 .env
```

记录旧包目录后停止旧版本：

```bash
cd /srv/pestkg/pestkg-server-OLD_TAG-linux-amd64
docker compose ps
docker compose down
```

启动新版本并验证：

```bash
cd /srv/pestkg/pestkg-server-NEW_TAG-linux-amd64
docker compose up -d --wait --wait-timeout 300
docker compose ps
curl --fail http://127.0.0.1:18088/health/ready
curl --fail http://127.0.0.1:18088/api/v1/graph/catalog
```

确认外层反向代理仍指向 `http://127.0.0.1:18088` 后，再访问正式域名。
若新版本异常，执行 `docker compose down`，回到旧目录运行同样的
`docker compose up -d --wait --wait-timeout 300` 即可回滚。日常停止和回滚
不要使用 `docker compose down -v`。

## 8. 升级和回滚

升级前记录旧目录、旧镜像标签和 `.env`，备份状态。校验并解压新包到
另一个目录，执行 `docker load`；停止旧目录下的服务，把域名、端口和
访问设置同步到新目录的 `.env`，在新目录启动并重复验收。
Compose 项目名保持一致，避免两套服务争抢端口。

回滚时停止新目录下的服务，切回旧目录，使用旧 `.env` 启动。不要删除
旧镜像、旧数据或命名卷。未来若涉及状态格式或数据版本迁移，还须按相应
版本迁移说明处理，不能仅换镜像标签。

旧教程中的 `pestkg-release`、`release.sh --full` 和 Neo4j 导入流程不适用
这个 Java/Parquet 离线包。

## 9. 常见故障

- `image not found`：执行 `docker load -i images.tar`，检查 `.env` 的镜像标签。
- 端口占用：更改 `.env` 的主机端口，再执行 `up -d`。
- API 不健康：查看 API 日志，核对 `data/releases` 是否完整且权限可读，检查内存。
- 参考子图缺失：核对 `data/reference-graphs/index.json` 及其指向的已发布包目录。
- HTTPS 失败：检查 DNS、80 / 443、出站连接和 Caddy 日志。
- 外网不能访问：检查云安全组、服务器防火墙、监听地址和端口映射。
- `exec format error`：确认服务器为 x86_64，ARM64 需另行构建对应平台。
