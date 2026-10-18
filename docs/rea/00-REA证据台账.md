# 00 · REA 证据台账（Evidence Ledger）

> 本文件按 REA 规程记录：**观测（observed）/ 推断（inference）/ 未知（unknown）三分**，每条结论都挂 Evidence ID 或明确标注「证据来源不在 REA 台账内」。

## 1. 会话与环境（实测）

| 项 | 值 | 来源 |
|---|---|---|
| REA CLI | `rea@6.5.0`（`npx -y rea-agents@latest`） | `doctor --json` identity |
| REA skill | `installed_version=42`、`installed_tool_count=207`、`state=aligned` | `doctor --json` |
| skill 安装位置 | `C:\Users\NANO\.agents\skills\reverse-engineer-anything\`（另有 `.claude\`、`.codex\`、`.cc-switch\` 副本） | 文件系统 |
| MCP 工具目录 | `mcp_tools=207`、`mcp_prompts=6`、`cli_commands=153` | `doctor --json` identity.catalog |
| Node / 宿主 | `24.17.0` / `win32 x64` | `doctor --json` scope_checks |
| Java | Corretto `jdk25.0.4_10`（`JAVA_HOME` 已设） | 环境变量 |
| apktool provider | `3.0.3`，通过 `REA_APKTOOL_COMMAND=D:\GITS\BackupToolkit-REA\re\tools\apktool.cmd` 指向已有 `apktool.jar` | `inspect-apktool-client` |

### 1.1 阻塞诊断（`doctor --json`，未修改任何配置）

| 检查 | 状态 | 分类 | 处置 |
|---|---|---|---|
| `registration:dsh` | ❌ `missing` | `config_drift` | `C:\Users\NANO\AppData\Roaming\dsh-desktop\harness\cordis.patch.yml` 无 REA 注册 → **REA 工具不出现在本会话**，只能走 CLI |
| `jadx` | ❌ `not_configured` | `missing_analysis_engine` | 需 `REA_JADX_MCP_JAR` 指向 **caller-supplied `jadx-headless-mcp 0.7.1` JAR**（REA 明确不代为下载）→ **Android 代码类工具全部不可用** |
| `hopper` / `ghidra` / `ida` | ❌ | `missing_analysis_engine` | 与 APK 任务无关，忽略 |
| `claude_code` / `codex` / `copilot_cli` / `vscode` 注册 | ✅ `aligned` | — | 说明 skill+CLI 侧是好的，只有 DSH 这条没配上 |

只读修复计划（已生成、**未执行**，`setup --client dsh --dry-run --json`）：

```
operation: create
target: C:\Users\NANO\AppData\Roaming\dsh-desktop\harness\cordis.patch.yml
command: "cmd.exe" "/d" "/c" "npx" "-y" "rea-agents@6.5.0" "mcp"
外部安装: 无（external=false，不装 Hopper）
说明: 保留无关配置；执行后用 --yes 施加同一 scope，然后重启客户端才会出现 MCP 工具
```

## 2. 本次实际取得的 REA Evidence

| Evidence ID | 操作 | provider | 覆盖 | 关键事实 |
|---|---|---|---|---|
| `ev_13f5650df0d714557174b7d4c9f6aac5a78ef816e2a735793348caf253bf9a5a` | `inspect_apktool_client` | apktool 3.0.3 | — | 客户端命令来自环境变量，版本 3.0.3 |
| `ev_dcd60afc36b78ad1e1d3b8352c13564a9434567062bbd429e0e8b7afa6644e6a` | `decode_android_resources` | apktool 3.0.3 | **complete**（110 个解码文件） | 解码后的 `AndroidManifest.xml` 全文 + **116 条字符串资源**，`coverage=complete` |
| `ev_98a4c07da3b4ec4ea0e03df693e05ecdcab25b380a21c33f3e099b763cfb0cc9`（同一 artifact 重跑会得到新 ID，身份以下面两个 sha256 为准） | `inspect-artifact` | 内置 ZIP 清单 | complete（container-entries） | `root_sha256=4af201230efa6670b5b377a240c7748e58f27bf89456e3c41e845e6e1c3566f4`，`graph_sha256=ef5f3870…0d9d`，节点 91 / 出现 94 / 边 93 |

REA 明示的限制（照抄，不当成结论）：

- `decode_android_resources`：**跳过 smali（`--no-src`）**，Java 源码恢复属于 JADX 家族 → 代码级结论不能由这条 Evidence 支撑；
- `inspect_artifact`：ZIP 清单**只列中央目录条目**，APK Signing Block 等非条目字节不算 occurrence → 签名方案无法由此判定；
- 两条均 `confidence=observed`、`authority=shipped-artifact`。

落盘：`re/evidence/decode-android-resources.json`、`re/evidence/inspect-artifact.json`

## 3. 结论 → 证据 映射

分级：**O** = REA 台账内观测；**D** = 静态反编译观测（jadx 1.5.6，**不在** REA 台账内，可复核路径/行号）；**I** = 推断；**U** = 未知。

### 3.1 由 REA Evidence 直接支撑（O）

| 结论 | 证据 |
|---|---|
| 包名 `r2ixzp.toolkit`，`compileSdkVersion=34`，versionName 1.1.1 / versionCode 1113 | `ev_dcd60afc…`（manifest + metadata） |
| Manifest **只声明** `android.permission.INTERACT_ACROSS_USERS` | `ev_dcd60afc…`（manifest 全文） |
| **无** `service` / `receiver` / `provider` 声明；11 个 activity，其中 `CrashActivity` 在 `:crash` 进程 | 同上 |
| `android:icon=@android:drawable/sym_def_app_icon`（系统默认图标） | 同上 |
| 应用名 `备份工具箱`，共 116 条字符串资源（全中文、含赞助/更新日志文案） | 同上 |
| APK 共 94 个 occurrence（91 个成员节点 + 根节点，等于 93 个中央目录条目 + 根）、根 sha256 = `4af2012…3566f4` | `ev_98a4c07d…` |
| `assets/main.jar`、`assets/bin/{arm64-v8a,armeabi-v7a,x86,x86_64}.zip`、`assets/dexopt/*` 存在 | 同上（成员清单） |

### 3.2 静态反编译观测（D，路径可复核）

| 结论 | 位置 |
|---|---|
| libsu root 服务通道：`app_process <64> -Xnoimage-dex2oat --nice-name=<pkg>:root:daemon … RootServerMain '<component>' <uid> daemon` | `re/jadx/sources/Intent/Cnew.java` |
| root shell 用 `Runtime.exec("su","--mount-master")`，退化 `su`→`sh`；主 shell flags=10、timeout=11s | `Intent/Cimport.java`、`p009else/Cimport.java` |
| AIDL `r2ixzp.toolkit.aidl.IRootManager`（13 方法）/ `IBackupManager`（2 方法） | `p032this/Cswitch.java`、`p032this/Cpublic.java`、`p004class/Cnative.java`、`p004class/Cthrow.java` |
| 启动时解 `assets/bin/<abi>.zip` → `filesDir/bin`，再 `source res/raw/root_shrc.sh`，成功标志 `echo '0'` | `Service/Cthrow.java`、`p012final/Creturn.java` |
| 备份引擎 = `root_shrc.sh`（tar + zstd，`--format=` 兼容 gz/xz/lz4；`.nomedia`；killall STOP/CONT；chown -hR；restorecon+chcon；`pm install-create/write/commit`） | `re/apktool/res/raw/root_shrc.sh`（全文见附录A） |
| 备份布局 `AppBackup/<pkg>/<backupTime>-{apk,apk_obb,user,user_de,data}.tar.*` + `!BackupInfo!<pkg>.json` + `!icon!<pkg>` | `c/Cimport.java`、`c/Creturn.java`、`p003catch/Cthrow.java` |
| 元数据模型字段 `pkg/backupList[{name,versionCode,versionName,backupTime,backupTime2,note}]`；fastjson2 `NotWriteDefaultValue\|IgnoreNonFieldGetter` | `c/Cwhile.java`、`c/Cthrow.java`、`c/Cfinally.java`、`p003catch/Cthrow.java` |
| 签名自校验门禁：SHA-256(证书 DER)→Base64 与常量 `3SYJFfhh…CGs=` 比对，失败则 `onBind` 返回 null | `p004class/Cwhile.java`（字符串解密见 `re/scripts/decode_xor_strings.py`） |
| 现场证书 SHA-256（base64）= 上述常量 | `keytool -printcert -jarfile`：`DD260915…077086B` → base64 `3SYJFfhh…CGs=` |
| 文件备份/恢复 UI 为死代码（按钮无 handler，无 shell 调用） | `r2ixzp/toolkit/ui/File/FileBackupRestoreActivity.java` |
| 日志轮转写成 `compareTo`（永不轮转） | `p003catch/Cwhile.java` |
| `settings put global verifier_verify_adb_installs 0` 等全局副作用 | `b/Cswitch.java` |
| 「检查更新」仅 `ACTION_VIEW` 打开 `https://backuptoolkit-update.r2ixzp.cf`，无 INTERNET 权限 | `p012final/Cthrow.java` |

### 3.3 推断（I）

| 推断 | 依据 | 反驳条件 |
|---|---|---|
| 上游可能是 `XayahSuSuSu/DataBackup` 一类开源实现 | 组件名/目录名/shell 引擎结构高度一致 | dex 中无 `com.xayah.*`、`databackup`、`xayah` 任何字符串（已核），故**无直接证据** |
| libsu 为 5.x | 存在 `IFileSystemService`、`IRootServiceManager`、`libsu-<pkg>` daemon 命名 | 若为 4.x 后的过渡版则版本判断需修正 |
| 本包为「重签名二次分发」 | 签名主体 `CN=r2ixzp` 与包名前缀一致、默认图标、全中文私有文案、签名常量等于自身证书 | 若原始项目本身就叫 r2ixzp 则不成立（但更新日志 1.0.0→1.1.1 全中文自述，倾向于分发者自建迭代） |

### 3.4 未知 / 未覆盖（U）

| 项 | 原因 |
|---|---|
| 代码级 REA 证据（`inspect_android_package`、`search_android_classes`、`inspect_android_method`、`trace_android_references`） | `jadx` provider 未配置（缺 caller-supplied `jadx-headless-mcp 0.7.1` JAR）→ 本次以「直接 jadx 1.5.6 反编译」替代，结论可复核但不在 REA 台账内 |
| APK 签名方案（v2/v3 块完整性） | `inspect_artifact` 只覆盖 ZIP 中央目录；v1/v2 判定用的 `keytool` 输出属外部工具观测 |
| 运行时行为（root shell 实际执行、`killall -STOP` 在某些 ROM 的表现、libsu 11s 超时语义） | 无设备/模拟器（`adb devices` 为空），REA 也明示静态分析不代表执行 |
| 94 个条目中 `res/*.xml|*.png` 的混淆命名与资源的精确对应 | `decode_android_resources` 已解出 manifest/strings，但布局-类绑定未逐一核对 |

## 4. 下一步探针（Next probes）

1. **（需批准）** 把 REA MCP 注册进 DSH：按 §1.1 的只读计划执行 `rea setup --client dsh --yes`，重启客户端 → 207 个工具进入会话；
2. **（需提供）** 放入 `jadx-headless-mcp 0.7.1` JAR 并设 `REA_JADX_MCP_JAR`，然后跑：
   `inspect_android_package` → `search_android_classes`（定位 `p004class.Cwhile` / `Cimport`）→ `inspect_android_method`（备份编排、`onBind` 门禁）→ `trace_android_references`（确认 `root_shrc.sh` 的唯一加载点）；
3. （可选）接入设备后：`list-adb-packages` / `pull-adb-package` 验证多用户路径，`read-adb-logcat` 观察 root shell 回显；
4. （可选）`compare-application-versions`：若能取得 v1.1.0 APK，可与本版做版本差异，验证「备份目录结构迁移」的实际改动范围。

## 5. 与其他文档的关系

`01`–`08` 与 `附录A` 的内容**全部来自 §3.2 的静态反编译观测与 §3.1 的 REA 观测**；本文档提供其证据索引与置信度分级。若后续补齐 JADX provider，应把 §3.2 的每条结论升级为 REA Evidence 引用，并复核是否出现矛盾（当前 `contradictions: []`）。

---

## 6. 附：技能通道（skill manager）的实测状态

REA 的能力分两条**互相独立**的通道交付，必须分清：

| 通道 | 载体 | 谁负责投递 | 本机实测 |
|---|---|---|---|
| **技能（说明文档）** | `~/.agents/skills/reverse-engineer-anything/SKILL.md`（v42） | `@michengai/dsh-skills-manager` 插件 → DSH 的 `ctx.skills` 子系统 | ✅ **已扫描、已启用** |
| **工具（207 个 MCP 工具）** | `rea-agents@6.5.0 mcp` 这个 MCP server | 客户端 MCP 注册（`harness\cordis.patch.yml`） | ❌ **未注册**（`doctor`：`registration:dsh = missing`） |

技能通道的实测证据（只读查询 `http://127.0.0.1:43129/api/dsh-skills-manager/state`，脚本 `re/scripts/probe-skills-manager-api.py`）：

```
root "agents"   path=C:\Users\NANO\.agents\skills   exists=True  enabled=True  skills=1
  * reverse-engineer-anything   enabled=True
    path=C:\Users\NANO\.agents\skills\reverse-engineer-anything\SKILL.md
root "ccswitch" / "claude"   各 1 份同名副本（重复登记，同一 skill 被列 3 次）
root "dsh"      path=%DSH_HOME%\skills              exists=False  skills=0
```

插件代码也印证它确实接入了 harness 的 skill 子系统：`lib/index.js:312`
`ctx.skills.registerProvider((control) => externalSkillProvider(control, invalidators))`；
日志 `%DSH_HOME%\dsh-skills-manager.log` 记录 `source-enable agents: C:\Users\NANO\.agents\skills`。

**但技能正文并未进入本会话上下文**：本会话工具表里没有 `skill` 工具，`%DSH_HOME%\sessions` 下 17 个会话文件中检索不到 `reverse-engineer-anything`（唯一命中是用户消息文本本身）。因此本次只能由 agent 主动 `read` 该 SKILL.md 路径来遵循规程 —— 这也解释了第一轮为什么我按自己的流程走并误判「REA 未安装」。

**结论**：skill manager 工作正常；它决定「我是否知道该按 REA 的规程做事」，**决定不了「我手里有没有 REA 的 207 个工具」**。后者只能通过 MCP 注册修复，且需要重启客户端才会注入本会话。

---

## 7. MCP 注册修复记录（已执行，2026-10-18 14:30）

### 7.1 变更

前置状态：`C:\Users\NANO\AppData\Roaming\dsh-desktop\harness\cordis.patch.yml` **不存在**（`Test-Path=False`）。

执行（用户已授权）：`npx -y rea-agents@latest setup --client dsh --yes --json`
→ `appliedActions: ["configured_dsh"]`、`clients.dsh.status=configured`、`doctor.healthy=true`

生成文件（278 B，`sha256=B65CE5F6F130E519CFF5C05B80BF10FEEE19231246F1B9E2219ADB9670E1EA06`）：

```yaml
- insert:
    - id: rea-mcp
      name: "@deepseek-ai/dsh-mcp-client"
      config:
        serverName: rea
        transport: stdio
        command: cmd.exe
        args: [/d, /c, npx, -y, rea-agents@6.5.0, mcp]
```

未安装任何外部依赖（`external=false`，未装 Hopper），未改动其它客户端配置。

### 7.2 预检（证明配置里的命令真的能出工具）

`re/scripts/preflight-rea-mcp.py` 用**与配置完全相同的命令行**走 MCP stdio JSON-RPC：

```
serverInfo: {'name': 'rea', 'version': '6.5.0'}
protocolVersion: 2024-11-05
capability keys: ['completions', 'prompts', 'tools']
TOOL COUNT: 207
  open_binary                present
  inspect_android_package     present
  inspect_android_method      present
  trace_android_references    present
  inspect_artifact            present
  decode_android_resources    present
  binary_session              present
  close_binary                present
```

⇒ 命令、包版本、工具目录均正确；剩余唯一变量是 DSH 是否在**重启后**加载该 plugin。

### 7.3 附带修复：apktool provider 的稳定路径

原先 apktool 只在项目目录里（`re\tools\apktool.cmd`），MCP 子进程的工作目录不可控。改为：

```
C:\Users\NANO\AppData\Local\rea-tools\apktool.cmd   （包装 java -jar apktool.jar，冒烟测试输出 3.0.3）
C:\Users\NANO\AppData\Local\rea-tools\apktool.jar   （caller-supplied，非 REA 安装）
setx REA_APKTOOL_COMMAND "C:\Users\NANO\AppData\Local\rea-tools\apktool.cmd"   → User 作用域，已回读确认
```

DSH 的 MCP stdio 子进程使用 `scrubbedParentEnv`（仅剔除凭据形态与陈旧 `DSH_*` 变量），因此该普通变量会被继承。

### 7.4 修复后状态

```
healthy: True | environment_healthy: False
  node  ok=True   host ok=True
  hopper/ghidra/ida-registration  ok=False  missing_analysis_engine（与 APK 无关）
  jadx  ok=False  missing_analysis_engine   ← 唯一仍缺的 APK 相关 provider
dsh registration: state=aligned, remediation=null
```

### 7.5 重启后的验证步骤（待执行）

1. **完全退出并重启 DSH 桌面端**（不是刷新窗口）——`cordis.patch.yml` 只在启动时作为 patch 应用；
2. 新会话里让 agent 调 `binary_session`（`{}`）确认 provider/工具可用性；或看工具表里是否出现 `open_binary` / `inspect_android_package` 等；
3. 若仍无工具：先查 DSH 的 MCP 启动错误（plugin 名 `rea-mcp`），不要重复 `setup`；
4. 之后补 `jadx-headless-mcp 0.7.1` JAR → `setx REA_JADX_MCP_JAR <jar>` → 重启，即可把 `01`–`08` 的代码级结论升级为 REA Evidence。

### 7.6 重启后验证结果（已通过，2026-10-18 06:36 起的新会话）

用户重启整机后，REA MCP 在会话内**确认挂载成功**：

`binary_session({})` → `server_identity`：

```
package: rea-agents 6.5.0        server: rea 6.5.0   started_at 2026-10-18T06:36:30Z
client:  dsh-mcp-client 0.0.1    negotiated protocol 2026-07-28
skill:   reverse-engineer-anything (expected_version 42)
catalog: mcp_tools 207, mcp_prompts 6, tools_sha256 805433f1…38ded
```

工具可用性（同一响应）：

| 组 | 状态 |
|---|---|
| `open_binary` / `binary_session` / `close_binary` / `inspect_analysis_view` / `export_evidence_bundle` | ✅ available |
| `decode_android_resources`（apktool-provider） | ✅ available |
| `inspect_artifact` / `extract_artifact` | ✅ available（`target_required`，需先 `open_binary`） |
| `inspect_android_package` / `inspect_android_class` / `inspect_android_method` / `search_android_classes` / `trace_android_references`（android-provider） | ❌ `provider_missing` → 需 `REA_JADX_MCP_JAR` |
| macOS-only（`inspect_macho`/`inspect_signature`/native UI/calls） | ❌ `unsupported_host`（win32，预期） |
| ghidra / ida / jeb / binwalk / tshark / sigrok / wabt / pwntools / wakaru | ❌ `provider_missing`（与 APK 任务无关） |

环境变量继承已验证生效：

| Evidence ID | 观测 |
|---|---|
| `ev_47ca735c181a168eacd09c32c0ef1476e43847dd924912a72bc0ea1140c96193` | `inspect_apktool_client` → `command=C:\Users\NANO\AppData\Local\rea-tools\apktool.cmd`、**`command_source=environment`**、apktool 3.0.3 ⇒ §7.3 的 `setx` 被 MCP 子进程继承 |

端到端跑通（本次会话新产生的 Evidence）：

| Evidence ID | 操作 | 结果 |
|---|---|---|
| `ev_1191df5804322a15db126ac2e08cf43abe4ae5034d40695126669c70f73510f2` | `inspect_artifact`（父记录） | 全量清单已保留 |
| `ev_5296fddff835dc4ceb3f2664dec7949241f0fc71bef297bda6dc95584c17f4aa` | `inspect_analysis_view`（summary） | 91 节点 / 94 occurrence / 93 边，**integrity_contradictions = 0**，`source_complete=true`，覆盖 278/278 |
| `ev_c893ee754a469d0b2aed16be0c2223751a1a4af6623599009086fd7906d82696` | `decode_android_resources`（`include_strings=false`） | versionName 1.1.1 / versionCode 1113 / minSdk 21 / targetSdk 34 / package `r2ixzp.toolkit`；manifest 全文；`decoded_file_count=110`；`coverage=complete` |

`open_binary` 确认目标身份：`kind=archive`、`format=apk`、`sha256=4af201230efa6670b5b377a240c7748e58f27bf89456e3c41e845e6e1c3566f4`（与 §3.1/§7.2 一致，无矛盾）。

### 7.7 仍未解决：JADX provider（唯一 APK 相关缺口）

REA 6.5.0 要求 **`jadx-headless-mcp 0.7.1` 的 JAR**（`REA_JADX_MCP_JAR`）。本次排查结论：

| 渠道 | 结果 |
|---|---|
| npm `jadx-headless-mcp` | 只有 **0.7.0**，且包内只有 `cli.js / package.json / README / LICENSE`（**46 KB，无 JAR**）→ 不是 REA 需要的产物 |
| GitHub Releases（`Samael-Z/jadx-headless-mcp`） | tag 有 `v0.7.0 v1.0.1 v1.1.0 v1.1.1 v1.4.0`；`v1.1.0+` 各带 **`jadx-headless-mcp-v2.jar`**（约 68 MB，Maven shaded fat jar，Java 17 target）；**没有名为 0.7.1 的 tag** |
| GitHub API | 触发速率限制（403），已改用 releases 页面 + `expanded_assets` 片段确认 |

⇒ 版本号存在错配：REA 期望 `0.7.1`，上游实际的“v2 协议”JAR 从 `v1.1.0` 起才有。**未擅自下载安装第三方 68 MB 二进制**，等待用户决定：可先试 `v1.4.0` 的 `jadx-headless-mcp-v2.jar`（若 REA 仅校验工具面而非精确版本号，则可直接接通），否则需向 REA 上游确认 0.7.1 的来源。

### 7.8 JADX 落地结果（用户授权后执行）

**① 找到 REA 认可的准确产物**（REA 包内 `dist/android/JadxRelease.js` 写死审计信息，不必再猜）：

```js
version  0.7.1
revision 5844800a486d2248fa949b74c9896285f5b54de2
sha256   6e5eacf500b64292bfb73c49797c1958f6ee44646e43e868039ae7feb573ff75
url      https://github.com/1013503897/jadx-headless-mcp/releases/download/v0.7.1/jadx-headless-mcp-0.7.1-all.jar
```

**② 下载并校验**：`C:\Users\NANO\AppData\Local\rea-tools\jadx-headless-mcp-0.7.1-all.jar`，40.6 MB（42,619,858 B），sha256 = `6e5eacf5…ff75` **与审计值完全一致**；`Main-Class: com.atxx.jhmcp.MainKt`，22,340 个 class，含 `com/atxx/jhmcp/*` 与 MCP Kotlin SDK；已 `setx REA_JADX_MCP_JAR` 持久化。

（先前误下的 `v1.4.0 jadx-headless-mcp-v2.jar` 被 REA 拒绝：`does not contain the required metadata bridge classes` —— REA 要的是带 `com.atxx.jhmcp` 的 0.7.1 线，而不是 v2 线。已删除该文件。）

**③ 各层独立验证**：

| 层 | 方法 | 结果 |
|---|---|---|
| JAR 自身 MCP | `python re/scripts/probe-jadx-jar.py`（`java -jar` + MCP stdio） | ✅ `serverInfo {jadx-headless-mcp, 0.7.1}`，26 个工具 |
| REA 的 Java 桥 | `python re/scripts/probe-jadx-bridge.py`（用 REA 完全相同的 argv：`java --class-path <jar> ReaJadxBridge.java`） | ✅ `serverInfo {name: "rea-jadx-bridge", version: "1"}` —— 正是 REA 期望的桥身份 |
| provider 注册 | `rea doctor --client dsh --json` | ✅ `jadx ok=True available=True`：`JADX MCP bridge JAR validated …` |
| **REA 实际执行** | `rea inspect-android-package …` | ❌ `execution_failure`：`diagnostics: {reason: "Unexpected end of JSON input", stderr: ""}` |

**④ 结论与归因**：JAR / Java25(含 `jdk.compiler`) / 桥 / provider 校验全部通过，唯独 REA 自己派生该进程时拿不到任何 stdout（stderr 也为空，而手工同参数运行会输出 151 行日志 + 正常握手）⇒ 故障点在 **REA 6.5.0 在 Windows 上的 provider 进程派生/管道边界**，非本机配置。已排除的因素：JAR 版本与摘要、缺类、JAVA_HOME/PATH、jdk.compiler、Windows 原生插件加载（`rea-windows-x64.node` 可 `require` 成功，导出 `call`）。

**⑤ 变通验证（不依赖 REA 派生）**：改用 JAR 自带 MCP 直接核对 APK（`re/scripts/xcheck-jadx.py`），结果与既有静态分析一致：

```
load_apk → state=LOADED, class_count=656, raw_class_count=656, resource_count=93, load_duration_ms=999
get_app_info → package=r2ixzp.toolkit, version 1.1.1/1113, minSdk 21, targetSdk 34,
               permissions=[android.permission.INTERACT_ACROSS_USERS]
list_classes → 共 656 条，含 Activity.Cthrow / Intent.Cnew / Intent.Cimport / Service.Cthrow
               / p000abstract.* / a.Cwhile / b.Cswitch / c.Cimport …
```

⇒ **独立佐证**：DEX 中真实类名就是 `Service.Cthrow`、`Intent.Cnew`、`p000abstract.*` 这类「包名/类名被替换成关键字或系统类名」的形态，与 `06-混淆与防篡改.md` 的判断一致（jadx 1.5.6 与 JADX MCP 两条独立工具链给出相同命名）。

**后续**：待 REA 修复 Windows 派生问题（或换 Linux/macOS 宿主）后，`inspect_android_package` / `inspect_android_method` / `trace_android_references` 即可直接产出带 Evidence ID 的代码级记录；在此之前，代码级结论仍以 §3.2 的「静态反编译观测」标注，并由上述 `xcheck-jadx.py` 交叉核对。
