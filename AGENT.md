# AGENT.md — BackupToolkit 逆向分析 / 重构交接

> 本文件是**唯一的进度真相源**。任何 agent 接手前先读它，再按需读 `docs/rea/` 下对应文档。
> `CLAUDE.md` 通过 `@AGENT.md` 引用本文件。
> 更新规则：状态有变化就改这里（尤其是「现状」「下一步」两节），细则写进 `docs/rea/`。

---

## 1. 任务

逆向一个第三方 Android 全量备份工具（`BackupToolkit v1.1.1`，包名 `r2ixzp.toolkit`，应用名「备份工具箱」），
**搞清它怎么实现**，为**重构**做准备。

**当前阶段目标：只产出分析，不写实现代码。** 重构实现尚未开始。

约束与前提：

- 目标 APK 不随仓库分发（对方是二次分发的第三方产物，涉及再分发问题）。需要分析时把 APK 放回仓库根目录。
- 分析以**静态**为主：本机无 Android 设备/模拟器，root 行为无法实测。

---

## 2. 仓库布局

```
README.md / LICENSE          远程已有（MIT, 2026 mineextremely），不要覆盖
AGENT.md                     本文件：进度与交接
CLAUDE.md                    Claude Code 入口，@AGENT.md
docs/rea/
  README.md                  分析总览（含 REA 接入状态）
  00-REA证据台账.md           ★ 证据台账：Evidence ID、观测/推断/未知三分、环境修复记录
  01-包结构与身份.md           包信息、签名、组件、资源、依赖库、来源判定
  02-启动链与权限架构.md       双进程模型、libsu root 守护、AIDL 契约、启动时序
  03-备份恢复引擎.md          shell 引擎逐函数语义、备份/恢复/APK 安装算法
  04-数据格式与元数据.md      JSON schema、文件名规范、SharedPreferences 全键表
  05-功能清单.md              功能矩阵、三档选项语义、死代码清单
  06-混淆与防篡改.md          R8 关键字重命名、XOR 字符串表、签名自校验门禁
  07-缺陷与风险.md            正确性缺陷、安全风险、兼容性风险
  08-重构蓝图.md              ★ 目标架构、模块边界、格式 v2、恢复状态机、里程碑
  附录A-root_shrc-注释.md     ★ 内嵌 shell 引擎全文 + 逐段注释（重构最关键参考）
  assets/
    root_shrc.original.sh         内嵌脚本原始件（sha256 5744ba42…101b，8650 B）
    change_log.original.txt       作者更新日志（推断迭代史用）
re/
  README.md                  分析工作区说明（产物不入库，可重新生成）
  scripts/                   可复跑的分析脚本（入库）
    decode_xor_strings.py       解 p004class.Cwhile 的 XOR(77) 字符串表
    probe-jadx-jar.py           直接驱动 jadx-headless-mcp 的 MCP（26 工具）
    probe-jadx-bridge.py        用 REA 完全相同 argv 验证 ReaJadxBridge
    xcheck-jadx.py              用 JADX 核对 APK（class_count=656）→ 交叉验证结论
    preflight-rea-mcp.py        验证 `rea mcp` 能否出 207 工具
    probe-skills-manager-api.py 查 skills-manager 状态（哪份 SKILL.md 被登记）
    check-rea-doctor.py         跑 `rea doctor` 并提取 jadx provider 诊断
```

**不入库**（`.gitignore`）：`*.apk`、`re/tools/`、`re/bin/`、`re/apktool/`、`re/jadx/`、`re/mainjar/`、`re/jadx_mainjar/`
—— 原因：体积 / 第三方二进制与反编译代码 / 可由 APK 一键重建。

---

## 3. 现状（截至本次提交）

| 维度 | 状态 | 主要依据 |
|---|---|---|
| 身份与打包 | ✅ 完成 | `01`、REA `decode_android_resources` / `inspect_artifact` |
| 组件 / 权限边界 | ✅ 完成 | `01` |
| 权限架构（root 守护 + AIDL + root shell） | ✅ 完成 | `02` |
| 启动链 7 步 | ✅ 完成 | `02` |
| 备份 / 恢复引擎（shell 逐函数） | ✅ 完成 | `03`、`附录A` |
| 数据格式与偏好键 | ✅ 完成 | `04` |
| 功能清单 / 死代码 | ✅ 完成 | `05` |
| 混淆 / 防篡改 | ✅ 完成（含门禁绕过点） | `06` |
| 缺陷与风险 | ✅ 完成（12 条） | `07` |
| 重构蓝图（架构/模块/格式 v2/状态机） | ✅ 完成（设计层） | `08` |
| 格式 v2 清单 schema + 恢复状态迁移表 + 错误码表 | ⬜ **待细化**（下一步） | `08` §4/§5/§7 还偏概览 |
| 代码级 REA Evidence 化 | ✅ 关键链路完成 | `00` §8：门禁/启动/root 部署/AIDL/命令已产出 Evidence ID（JADX 0.7.1，class_count=656）；UI 死代码等未逐条重跑 |
| 原生二进制（`assets/bin/*`） | ✅ 完成 | 2026-10-19 静态检查：无 `lib/*.so`；12 个 ELF 中 `toolkit` 已完整还原，`busybox`/`zstd` 为第三方已知构建 |
| 动态验证（真机 root 行为） | ⚠️ 缺设备 | `07` §4 |
| 重构实现 | ⬜ 未开始 | — |

---

## 4. 关键结论速查（重构必读）

1. **它不是自提权工具**：完全依赖设备已 root。用 **libsu 5.x**（被 R8 混淆）经 `app_process -Xnoimage-dex2oat --nice-name=<pkg>:root:daemon` + 内置 `assets/main.jar`（内含 `com.topjohnwu.superuser.internal.RootServerMain`）拉起 **root 身份常驻守护进程**，在其中跑自己的 `RootService` 实现，对外暴露 `r2ixzp.toolkit.aidl.IRootManager`（13 方法）/ `IBackupManager`（2 方法）。
2. **第二通道是 root shell**：`Runtime.exec("su","--mount-master")`（退化 `su`→`sh`），启动时把 `res/raw/root_shrc.sh`（335 行）`source` 进去，之后 Java 只拼一行命令：`app_backup <pkg> <backupTime> 'apk&&user&&data'`。
3. **真正的引擎是 shell 脚本**，不是 Java。tar 用 busybox，压缩只有一个 `zstd`（靠 `--format=gzip|xz|lz4|zstd` 出四种格式），`toolkit` 是自研 5 KB ELF 只做 `st_info`（取 size/uid）。
4. **三档语义反直觉**：`apk`=安装包+obb；`user`=**内部** `/data/user*/<uid>/<pkg>`（排除 lib/oat/cache/code_cache/no_backup）；`data`=**共享存储** `Android/data/<pkg>`（排除 cache）。
5. **备份布局**：`<backup_home>/AppBackup/<pkg>/<backupTime>-{apk,apk_obb,user,user_de,data}.tar.*` + `!BackupInfo!<pkg>.json` + `!icon!<pkg>`；默认 `<sdcard>/Backups/BackupToolkit`；`.nomedia` 防扫描。
6. **恢复算法**：`mv <path> <path>_old` → `tar -xC <父目录> -o` → `chown -hR uid:uid` → `restorecon -F` + `chcon -R`（从父目录 `ls -Z` 取上下文）→ 成功才删 `_old`，失败回滚。**uid 与 SELinux 上下文都是「猜」出来的**，这是最大正确性隐患。
7. **APK 恢复**：单包 `pm install -r -t -d -i com.android.vending`；分包 `pm install-create/write/commit`；兼容模式改 `cat apk | pm install -S <size>`（为光速虚拟机等）。
8. **元数据**：fastjson2（`NotWriteDefaultValue|IgnoreNonFieldGetter`）写 `!BackupInfo!<pkg>.json`：`pkg` + `backupList[{name, versionCode, versionName, backupTime, backupTime2, note}]`；`config.json` 记 `{versionName, versionCode}`。
9. **防篡改**：`p004class.Cwhile.onBind()` 用被 XOR(77) 加密的反射串做**证书 SHA-256 → base64 比对**，常量 `3SYJFfhhlM50hIfXHeeNP9p8Hjt8lNDfA5gsBXB3CGs=` 等于**当前签名证书**的摘要（`DD260915…086B`）。失败只返回 null binder（App 弹「Root服务启动失败」），不改数据、不退出 —— 一个 `if` 就能绕。
10. **死代码/缺陷**：文件备份 UI 全无 handler（功能未实装）；日志轮转写成 `compareTo`（永不轮转）；`app_init` 的备份目录未加引号（可注入）；恢复端**不校验 tar 条目**（配合 root = 任意写）。
11. **混淆**：R8 把包/类/字段/方法名替换成 **Java 关键字**（`Service.Cthrow`、`Intent.Cnew`、`p000abstract.*`、`a.Cwhile`），jadx 只能生成 `Cthrow`/`p000…` 占位名 —— 阅读与重构都必须**按调用关系推理，不能靠名字**。

---

## 5. 复现分析（WSL2 / Linux）

```bash
# 1) 把目标 APK 放回仓库根目录（文件名需一致，或用 -p 指定）
#    sha256 = 4af201230efa6670b5b377a240c7748e58f27bf89456e3c41e845e6e1c3566f4

# 2) 反编译（需要 JDK 17+；仓库不入库反编译产物）
mkdir -p re/tools
#   apktool 3.0.3
java -jar re/tools/apktool.jar d "BackupToolkit v1.1.1.apk" -o re/apktool -f
#   jadx 1.5.6（或任意 1.5.x）
re/tools/jadx/bin/jadx -d re/jadx --show-bad-code "BackupToolkit v1.1.1.apk"

# 3) 关键文件
#   re/apktool/AndroidManifest.xml
#   re/apktool/res/raw/root_shrc.sh          ← 引擎（仓库内已有副本：docs/rea/assets/）
#   re/apktool/assets/bin/<abi>.zip          ← busybox 1.36.1-Magisk / zstd 1.5.5 / toolkit
#   re/jadx/sources/Service/Cthrow.java      ← 二进制部署 + env 注入 + source 脚本
#   re/jadx/sources/p004class/Cwhile.java    ← 签名门禁 + onBind
#   re/jadx/sources/c/Cimport.java           ← 备份/恢复编排
#   re/jadx/sources/Intent/Cnew.java         ← app_process 启动 root 守护进程

# 4) 字符串去混淆
python3 re/scripts/decode_xor_strings.py
```

---

## 6. REA（MCP）环境状态

记录于 2026-10-19，WSL2（Debian 13 / armbian trixie 用户态）。

| 项 | 状态 |
|---|---|
| skill `reverse-engineer-anything` | ✅ 已装 v42 / 207 工具，位于 `~/.claude/skills/reverse-engineer-anything/`；`doctor` 判定 `skill.state=aligned` |
| Claude Code MCP 注册 | ✅ `~/.claude.json` → `npx -y rea-agents@6.7.0 mcp`，`claude mcp list` 显示 Connected；live server `rea-agents 6.7.0` / SDK `2.3.1` / 207 tools |
| `jadx` provider | ✅ 健康：`REA_JADX_MCP_JAR=/home/via/jadx/jadx-headless-mcp-0.7.1-all.jar`（定义在 `~/.bashrc`），sha256 `6e5eacf5…ff75`；手工握手 `serverInfo={jadx-headless-mcp,0.7.1}`、26 工具；Java 21.0.12.1。live MCP 中 Android 工具 `available=true`，`inspect_android_package` 端到端成功（`r2ixzp.toolkit` 1.1.1/1113，class_count=656，resource_count=93） |
| `apktool` provider | ✅ 可用：`/usr/local/bin/apktool` **3.0.3**（`command_source=environment`），已高于 CVE-2024-21633 的修复线 2.9.2 |
| hopper / ghidra / ida / kuna / jeb / binwalk / tshark / sigrok / wabt / pwntools / wakaru | 未配置（与 APK 任务无关） |

Windows 上 REA 6.5.0 派生 JADX 子进程失败的 bug 在 Linux（POSIX owned-process boundary）**未复现**；`npx -y rea-agents@6.7.0 doctor --client claude_code --json` 返回 `healthy=true`。

**代码级 Evidence 已完成**：APK 已放回仓库根目录；`inspect_android_package` / `inspect_android_class` / `inspect_android_method` / `trace_android_references` 已产出 §8 的 Evidence 表。`apktool` 3.0.3 可用，资源/清单解码不再受阻。

证据台账与全部 Evidence ID 见 `docs/rea/00-REA证据台账.md`。

---

## 7. 下一步（按优先级）

1. **细化格式 v2 与恢复状态机**（唯一还虚的部分，见 `08` §4/§5/§7）：
   - 单次备份清单的字段表（含 `uid` / `selinuxContext` / `signerSha256` / `parts[].sha256`）；
   - 恢复状态迁移表（`Preflight→Prepare→Extract→Install→Commit→Verify→Cleanup`，每状态失败去向）；
   - 错误码表（`E_UID_UNKNOWN`、`E_ARCHIVE_UNSAFE`、`E_SPACE`、`E_INSTALL_FAILED`…）。
2. **v1→v2 只读兼容适配器**的字段映射表（`user→internal_data`、`data→external_data`）。
3. ~~（可选）Linux 下补 REA 代码级 Evidence~~ ✅ **已完成**：`onBind` 门禁（`mo8continue`）、XOR 密钥运行时派生、`root_shrc.sh` 唯一直接加载点均已产出 Evidence ID，见 `00` §8。
4. **（可选）动态验证**：真机 root 环境跑一次「备份→卸载→恢复→应用能启动」闭环，核对 `07` 里列出的 uid/SELinux 猜测风险。
5. 之后才进入实现（M0 环境自检 → M1 备份 → M2 恢复 → M3 兼容/多用户 → M4 进度/加密）。

---

## 8. 约定与禁忌

- **不要覆盖** `README.md` / `LICENSE`（远程已有）。
- **不要提交** APK、`re/tools`、`re/bin`、`re/apktool`、`re/jadx`、`re/mainjar`（体积 + 第三方内容）。
- 引用结论时**带上证据来源**：优先 `docs/rea/00` 里的 Evidence ID；次之标注 `re/jadx/...:行号`（属「静态反编译观测」，非 REA 台账内证据）。
- 区分 **观测 / 推断 / 未知**：`01` §3「来源判定」与 `06` §3 是典型的**推断**，不要把「疑似上游 DataBackup」当事实。
- 重构方案里**明确禁止照抄**：`eval` 拼 tar 参数、`alias` 依赖同一 shell 会话、uid/SELinux 猜测、`mv` 失败静默、`settings put global` 全局副作用、`pm install -i com.android.vending` 伪造来源（详见 `08` §10）。
- 提交信息用中文短句 + 影响范围，例如：`docs(rea): 细化格式 v2 清单字段表`。
