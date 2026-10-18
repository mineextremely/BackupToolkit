# re/ — 分析工作区

本目录放**分析中间产物**。其中大部分内容不入库（见根 `.gitignore`），因为它们是第三方二进制或反编译代码，
体积大且能由 APK 一键重建。入库的只有 `scripts/`（我自己写的分析脚本）。

## 目录

| 路径 | 入库 | 说明 |
|---|---|---|
| `scripts/` | ✅ | 可复跑的分析脚本，见下表 |
| `tools/` | ❌ | apktool.jar / jadx（分析工具，按需下载） |
| `bin/<abi>/` | ❌ | 从 `assets/bin/<abi>.zip` 解出的 busybox 1.36.1-Magisk / zstd 1.5.5 / toolkit ELF |
| `apktool/` | ❌ | `apktool d` 结果（可读 Manifest、res、smali） |
| `jadx/` | ❌ | `jadx` 反编译的 Java 源码（480 个类） |
| `mainjar/` · `jadx_mainjar/` | ❌ | `assets/main.jar` 内的 libsu root server dex 及其反编译 |
| `evidence/` | ⚠️ 视情况 | REA 导出的 Evidence JSON（含绝对路径，体积小可留作审计） |

## scripts

| 脚本 | 作用 |
|---|---|
| `decode_xor_strings.py` | 解 `p004class.Cwhile` 的 XOR(77) 字符串表，产出签名门禁的 12 条明文（含期望 base64 摘要） |
| `probe-jadx-jar.py` | 直接以 MCP stdio 驱动 `jadx-headless-mcp-0.7.1-all.jar`（0.7.1 线，26 个工具） |
| `probe-jadx-bridge.py` | 用 REA **完全相同**的 argv（`java --class-path <jar> ReaJadxBridge.java`）验证桥身份 `rea-jadx-bridge/1` |
| `xcheck-jadx.py` | 用 JADX 独立核对 APK：`load_apk` → `class_count=656`、`get_app_info`、`list_classes`（交叉验证混淆命名） |
| `preflight-rea-mcp.py` | 预检 `npx rea-agents@6.5.0 mcp`：`serverInfo` + 207 工具是否齐全 |
| `probe-skills-manager-api.py` | 查 `http://127.0.0.1:<DSH_WEB_PORT>/api/dsh-skills-manager/state`，确认哪份 `SKILL.md` 被登记/启用 |
| `check-rea-doctor.py` | 跑 `rea doctor --client dsh --json` 并抽取 jadx provider 诊断 |

## 重建步骤

见根目录 `AGENT.md` §5「复现分析」。要点：`apktool d` + `jadx -d`，然后按 `docs/rea/` 里的路径引用定位文件。
