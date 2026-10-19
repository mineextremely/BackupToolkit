# BackupToolkit v1.1.1（备份工具箱）逆向分析总览

> 目标：搞清楚这个第三方「全量备份工具」是怎么实现的，为后续重构提供依据。
> **本阶段只产出分析文档，未编写任何业务代码。**

---

## 0. REA 接入状态（WSL2 实测，2026-10-19）

REA MCP 已在本会话可用，代码级结论已产出 Evidence ID；环境细节与完整台账见 `00-REA证据台账.md` §8。

| 项 | 状态 |
|---|---|
| REA MCP | ✅ `rea-agents 6.7.0`（`npx -y rea-agents@6.7.0 mcp`），SDK 2.3.1，207 tools；`claude mcp list` 显示 Connected |
| skill | ✅ `reverse-engineer-anything` v42 / 207，`state=aligned`（`~/.claude/skills/`） |
| `jadx` provider | ✅ `jadx-headless-mcp 0.7.1`，JAR sha256 `6e5eacf5…ff75`；端到端 `inspect_android_package` 成功（`class_count=656`） |
| `apktool` provider | ✅ `/usr/local/bin/apktool` 3.0.3 |
| 宿主 | WSL2 Debian 13；OpenJDK 21.0.12.1 |
| Ghidra / Hopper / IDA / Kuna | 未配置；经评估本 APK **不需要**（唯一自研原生程序 `toolkit` 已用 `objdump` 完整还原） |

证据分层：

1. **REA 原生 Evidence**：包/类/方法/引用（`inspect_android_package`、`inspect_android_class`、`inspect_android_method`、`trace_android_references`）→ 台账 §8；
2. **直接反编译/反汇编观测**：jadx CLI、apktool、`readelf`/`objdump`（含 `assets/bin/*`）→ 文中标注路径/哈希；
3. **动态验证**：仍未执行（无设备/模拟器）。

> `09-格式v2规范.md` 与 `10-恢复状态机与错误码.md` 是**设计规范（D）**，不是对 v1 的观测；
> 引用时不要把 v2 字段当成「原 App 的行为」。v1 的观测证据仍以 `00`–`07` 与 `附录A` 为准。

历史 Windows/DSH 接入过程保留在 `00-REA证据台账.md` §1–§7。

---

## 1. 一句话结论

它是一个 **「Java 壳 + 常驻 root 守护进程 + 内嵌 shell 脚本引擎」** 的 root 备份工具：

- **权限模型**：不自带 native root 提权，完全依赖设备已 root；用 **libsu 5.x**（被 R8 混淆）通过 `app_process` + 内置 `assets/main.jar` 拉起 **root 身份常驻进程**，再由该进程提供 AIDL 服务（包管理/IPC 文件 IO）；
- **备份引擎**：真正的备份逻辑**不在 Java 里，而在 `res/raw/root_shrc.sh` 这个 335 行 shell 脚本里**。App 启动时把它 `source` 进 root shell，之后 Java 只负责「拼一行命令」：`app_backup <pkg> <时间戳> 'apk&&user&&data'`；
- **数据面**：`busybox tar` 打包 + `zstd` 压缩（也支持 gz/xz/lz4，因为全交给 zstd 的 `--format=` 处理），自定义 `toolkit` 小 ELF 只提供 `stat` 能力（取 size/uid）；
- **元数据**：fastjson2 写的 `!BackupInfo!<pkg>.json`（备份列表）+ `config.json`（备份根目录版本）；图标存 `!icon!<pkg>`；
- **UI 进程零存储权限**：连 `!BackupInfo!.json` 都是通过 root 服务的 `IFileSystemService` 读写的，因此 Manifest 里只声明了 `INTERACT_ACROSS_USERS` 一个权限，没有 `MANAGE_EXTERNAL_STORAGE`；
- **来源**：包名 `r2ixzp.toolkit`、签名 `CN=r2ixzp`、图标是 Android 默认图标、资源全中文、更新日志自 1.0.0 起为中文手写 —— 这是对一个开源/第三方备份工具**重新签名的二次分发构建**（改动点见 `01-包结构与身份.md`）。

---

## 2. 文档索引

| 文档 | 内容 |
|---|---|
| `00-REA证据台账.md` | **REA 接入状态、Evidence ID 台账、观测/推断/未知三分、缺口与下一步探针** |
| `01-包结构与身份.md` | 包信息、签名、组件清单、DEX/资源/资产结构、依赖库清单、来源判定 |
| `02-启动链与权限架构.md` | 双进程模型、libsu root 守护进程、AIDL 契约全表、启动时序、环境部署 |
| `03-备份恢复引擎.md` | `root_shrc.sh` 逐函数语义、备份/恢复/APK 安装算法、文件布局 |
| `04-数据格式与元数据.md` | JSON schema、文件名规范、SharedPreferences 全键表、日志 |
| `05-功能清单.md` | 字符串级功能矩阵、三档备份选项语义、多用户/存储/云备份实现 |
| `06-混淆与防篡改.md` | R8 关键字重命名、XOR 字符串表、签名自校验门禁、破解点 |
| `07-缺陷与风险.md` | 功能死代码、算法缺陷、安全与稳定性风险清单 |
| `08-重构蓝图.md` | 目标架构、模块边界、格式 v2 概览、迁移策略、验证方案 |
| `09-格式v2规范.md` | **格式细化**：目录布局、manifest schema、字段表、哈希/原子写协议、v1 只读适配与迁移 |
| `10-恢复状态机与错误码.md` | **恢复细化**：状态迁移、失败矩阵、Commit/Rollback、journal、归档校验、稳定错误码 |
| `11-v2审查与决策记录.md` | **审查与决策**：08/09/10/schema 交叉一致性审查（blocker/major/minor）、U1–U10 决策表（已拍板 2026-10-19）、已修正/已拍板清单 |
| `附录A-root_shrc-注释.md` | 内嵌 shell 引擎全文 + 逐段中文注释（重构最核心的参考件） |

## 3. 分析产物位置

```
BackupToolkit v1.1.1.apk        原始文件
docs/rea/                       本次分析文档
docs/rea/assets/                原始件副本 + format-v2.schema.json（v2 清单的 JSON Schema 草案）
re/
  apktool/                      apktool 3.0.3 解码结果（资源可读、smali 完整）
  jadx/                         jadx 1.5.6 反编译的 Java 源码（480 个类）
  jadx_mainjar/                 assets/main.jar 内 root server dex 的反编译结果
  bin/<abi>/                    从 assets/bin/*.zip 解出的 busybox / toolkit / zstd
  tools/                        apktool.jar、jadx（本次下载的分析工具）
```

## 4. 复现命令

```powershell
# 资源/Manifest 解码
java -jar re\tools\apktool.jar d "BackupToolkit v1.1.1.apk" -o re\apktool -f

# DEX 反编译（480 类，18 处 jadx 报错，不影响主体）
re\tools\jadx\bin\jadx.bat -d re\jadx --show-bad-code "BackupToolkit v1.1.1.apk"

# 内置 root server 单独反编译
re\tools\jadx\bin\jadx.bat -d re\jadx_mainjar .\re\mainjar

# 签名证书
keytool -printcert -jarfile "BackupToolkit v1.1.1.apk"

# 资产解包（busybox/zstd/toolkit、main.jar）
python - <<'PY'
import zipfile
zipfile.ZipFile("re/apktool/assets/main.jar").extractall("re/mainjar")
for abi in ["arm64-v8a","armeabi-v7a","x86_64","x86"]:
    zipfile.ZipFile(f"re/apktool/assets/bin/{abi}.zip").extractall(f"re/bin/{abi}")
PY
```

## 5. 复刻所需的最小知识集（如果你只想看 5 分钟）

1. 备份就是 `tar -c <路径> --exclude=... | zstd -3 --format=zstd -fo <时间戳>-<part>.tar.zst`；
2. 三个备份档位是 `apk`（安装包+obb）/ `user`（`/data/user*/<uid>/<pkg>`，排除 lib/oat/cache/code_cache/no_backup）/ `data`（`/sdcard/Android/data/<pkg>`，排除 cache）；
3. 恢复是「先 `mv` 成 `_old` → 解包 → `chown -hR uid:uid` → `restorecon/chcon` → 成功才删 `_old`，失败回滚」；
4. APK 恢复走 `pm install-create/write/commit` 会话（分包），兼容模式改用 stdin 管道 `cat apk | pm install -S <size>`；
5. 备份期间用 `killall -s STOP` / `-s CONT` 冻结被备份应用，恢复前 `am force-stop`；
6. 元数据是一个 per-package 的 JSON，文件名即备份时间戳；
7. 全部能力建立在**已 root** 的前提上，没有任何绕过或自提权。
