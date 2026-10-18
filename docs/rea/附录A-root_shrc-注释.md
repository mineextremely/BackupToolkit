# 附录 A · `res/raw/root_shrc.sh` 全文注释

> 来源：`re/apktool/res/raw/root_shrc.sh`（8650 B，335 行），运行时由 `Service.Cthrow.m118abstract()`
> 通过 `openRawResource(R.raw.root_shrc)` 逐行喂进长生命周期的 root shell（`su --mount-master`）。
> 脚本体最后一行 `echo '0'` 是「加载成功」信号；若输出不是 `"0"`，App 显示「环境错误：…」。
>
> 下面逐段注释（`# ⟵` 为分析者附加，其余均为原脚本内容）。

```sh
export TMPDIR=/data/local/tmp
# ⟵ 解包 APK / 放临时文件的位置：root 与普通进程都能读写的公共目录
# ⟵ 注意：本脚本全程不清理 TMPDIR，仅在各函数里 rm -f "$TMPDIR/"*.apk

# alias 要在前面
alias zstd='zstd -T0 -qr --ultra --priority=rt'
# ⟵ -T0 用满核心；-q 静默；-r 递归；--ultra 允许 level>19；--priority=rt 实时调度优先级
# ⟵ 同一个 zstd 二进制通过 --format= 兼顾 zstd/gzip/xz/lz4 四种格式

add_busybox_applet(){
	eval "alias $1='busybox $1'"
}
# ⟵ 用别名把精简 busybox 的 applet 暴露成普通命令

add_busybox_applet unzip
add_busybox_applet tar
add_busybox_applet realpath
add_busybox_applet find
add_busybox_applet awk
alias STI='toolkit st_info'
# ⟵ 自研 ELF：STI <path> s → 字节数；STI <path> u → 属主 uid（补 busybox 缺 stat）
alias LZ='/system/bin/ls -Z'
# ⟵ 取 SELinux 上下文（用系统 ls，不用 busybox，保证 -Z 输出格式）

whence killall &>/dev/null || add_busybox_applet killall
# ⟵ 系统有 killall 就用系统的，没有才用 busybox 的
add_busybox_applet grep

SDK_INT=$(getprop ro.build.version.sdk)
if [ "$SDK_INT" -ge 34 ]; then
	alias pm_install='pm install -r -t -d -i com.android.vending --bypass-low-target-sdk-block'
	alias pm_create='pm install-create -r -t -d -i com.android.vending --bypass-low-target-sdk-block'
else
	alias pm_install='pm install -r -t -d -i com.android.vending'
	alias pm_create='pm install-create -r -t -d -i com.android.vending'
fi
# ⟵ -r 覆盖  -t 允许 test-only  -d 允许降级  -i <installer> 伪造安装来源
# ⟵ Android 14(34) 起低 targetSdk 会被拒装，故追加 --bypass-low-target-sdk-block

#1 用户ID
#2 备份目录
#3 =1?备份:恢复
#4 =1?兼容模式:默认模式
app_init(){
	sd_android=/data/media/$1/Android
	[[ $1 -eq 0 && ! -d "$sd_android" ]] && sd_android=$(realpath /sdcard)/Android
	[ ! -d "$sd_android" ] && echo '!!未找到用户存储:'$1 && return 1
	# ⟵ 多用户时直取 /data/media/<uid>/Android；0 号用户走 /sdcard 的真实路径
	# ⟵ 找不到就直接失败，终止整个批次

	if [ $1 -eq 0 ]; then
  	pm_path(){ pm path $_APP_PKG; }
	else
		pm_path(){ pm path --user $_USER_ID $_APP_PKG; }
	fi
	# ⟵ 其他用户的包必须带 --user，否则查到的是当前用户的

	if [ $3 -eq 1 ]; then
		apk(){ backup_apk && backup apk_obb; }
		data(){ backup data cache; }
		user(){ backup user lib oat cache code_cache no_backup && backup user_de lib oat cache code_cache no_backup; }
		# ⟵ 档位 → 动作 的映射（备份）
		# ⟵ apk : 安装包 + /sdcard/Android/obb/<pkg>
		# ⟵ data: /sdcard/Android/data/<pkg>，排除 cache
		# ⟵ user: /data/user/<uid>/<pkg> 与 /data/user_de/<uid>/<pkg>，
		# ⟵       排除 lib(软链) / oat / cache / code_cache / no_backup（可重建或体积大）
	else
		apk(){ restore_apk && restore apk_obb; }
		data(){ restore data; }
		user(){ restore_user && restore user_de 1; }
		# ⟵ 恢复：user_de 的第二个参数 1 = 额外恢复 SELinux 上下文
		if [ $4 -eq 1 ]; then
			if [ "$SDK_INT" -ge 23 ]; then
				install_apk(){ cat "$1" | pm_install --user $_USER_ID -S $(STI "$1" s) 2>&1; }
				# ⟵ 兼容模式 SDK>=23：把 APK 从 stdin 灌进 pm，-S 指定字节数
			else
				install_apk(){
					local session=$(pm_create --user $_USER_ID | grep -o '[0-9]*')
					[ -z $session ] && echo '!!无法创建安装会话:' >&2 && return 1
					if install_apks $session "$1" 2>&1; then
						pm install-commit $session 2>&1;
					else
						pm install-abandon $session &>/dev/null; return 1
					fi
				}
			fi
			install_apks(){ cat "$2" | pm install-write -S $(STI "$2" s) "$1" "${2##*/}" -; }
		else
			install_apk(){ pm_install --user $_USER_ID "$1" 2>&1; }
			# ⟵ 默认模式：直接把路径交给 pm
			install_apks(){ pm install-write "$1" "${2##*/}" "$2"; }
		fi
	fi

	_USER_ID=$1
	_BACKUP_HOME=$2
}
# ⟵ 注意：_BACKUP_HOME 是全局变量，后续所有函数的产物路径都依赖它
# ⟵ 注意：Java 侧传参未加引号（String.format("app_init %s %s ...")），目录含空格会出错 → 见 07 §3.3

# 只有备份时会调用
#1 压缩包后缀
#2 压缩等级1~19，默认3
compress_init(){
	local format=$(parse_ext "$1")
	[ -z $format ] && echo '!!未知备份格式:'$1 && return 1
	if [ $format = tar ]; then
		compress_to_file='-f'
	else
		local level=$2
		if [ -z "$level" ]; then
			level=3
		elif [ "$level" -gt 19 ]; then
			level=19
		elif [ "$level" -lt 1 ]; then
			level=1
		fi
		compress_to_file="| zstd -$level --format=$format -fo"
		# ⟵ 关键技巧：压缩器永远只有一个 zstd，靠 --format=gzip|xz|lz4|zstd 切换产物格式
		# ⟵ -fo <file>：先写临时文件再原子替换（zstd 的 --force + 输出到文件）
	fi
	[ ! -f "$_BACKUP_HOME/.nomedia" ] && {
		mkdir -p "$_BACKUP_HOME"
		touch "$_BACKUP_HOME/.nomedia"
	}
	# ⟵ 防止媒体扫描器把备份目录内容加进相册/音乐库
	_BACKUP_EXT=$1
}

#1 绝对路径/tar选项
#2 输出路径
#...3 tar排除
compress(){
	local file=$2
	local exclude 
	if [[ "$1" != /* ]]; then
		tar_opts=$1
		exclude=$3
	else
		local dir=${1%/*} path=${1##*/}
		tar_opts="-C '$dir' '$path'"
		shift 2
		while [ $# -ge 1 ]; do
			exclude="$exclude --exclude='$path/$1'"
			shift 1
		done
		# ⟵ 传绝对路径时：以父目录为 -C，打包子名，并把「子名/排除项」作为 --exclude
	fi
	eval "tar -c $tar_opts $exclude $compress_to_file '$file'"
	# ⟵ 用了 eval 拼参数 → 路径含引号/空格会炸（重构应改 argv）
	[ $? -ne 0 ] && echo '错误' && return 1
	echo '完成'
}

#1 压缩包路径
#2 解压路径
#3 tar选项
decompress(){
	local format=$(parse_ext "$1")
	[ -z $format ] && echo '!!未知备份格式:'$1 && return 1
	[ -d "$2" ] || mkdir -p "$2"
	if [ $format = tar ]; then
		tar $3 -xC "$2" -f "$1"
	else
		zstd --format=$format -dc "$1" | tar $3 -xC "$2"
	fi
}
# ⟵ 解包**不做任何条目校验**（../、绝对路径、symlink 逃逸）→ 见 07 §3.2

backup_apk(){
	echo_n '备份apk:'
	local tar_opts val _C dir
	for val in $(pm_path 2>/dev/null); do
		val=${val#*:}                                   # 去掉 "package:" 前缀
		[[ "$val" != /data/* && -z $(unzip -lqq "$val" classes.dex) ]] && echo "跳过" && return
		# ⟵ 不在 /data 下、且压缩包里没有 classes.dex → 判定为系统框架 APK，跳过
		dir=${val%/*}
		if [ "$_C" != "$dir" ]; then
			_C=$dir
			tar_opts="${tar_opts} -C '$dir' '${val##*/}'"
		else
			tar_opts="${tar_opts} '${val##*/}'"
		fi
		# ⟵ base.apk 与所有 split apk 一次 tar；同目录只加一次 -C
	done
	[ -n "$tar_opts" ] || { echo '!!未找到安装目录:'$_APP_PKG; return 1; }
	rm -f "${CP_prefix}apk.tar"*
	compress "$tar_opts" "${CP_prefix}apk${_BACKUP_EXT}"
}

#1 备份
#...2 tar排除
backup(){
	echo_n "备份$1:"
	eval "local path=\$app_$1_path"
	[ -d "$path" ] || { echo '跳过'; return; }
	rm -f "$CP_prefix${1}.tar"*
	# ⟵ 先删同名旧分卷，避免「换格式备份」后 .tar.zst / .tar.gz 同时存在
	local file=$CP_prefix$1$_BACKUP_EXT
	shift 1
	compress "$path" "$file" "$@"
}

restore_apk(){
	echo_n '恢复apk:'; not_file "$apk_CP" '跳过' && return
	rm -f "$TMPDIR/"*.apk
	decompress "$apk_CP" "$TMPDIR"; local S=$?
	if [ $S -eq 0 ]; then
		local out apks=$(find "$TMPDIR" -maxdepth 1 -name '*.apk' -type f)
		case $(echo "$apks" | grep -c .) in
			0) echo '没有apk！';;
			1) echo_n '安装apk:'; out=$(install_apk "$apks"); S=$?;;
			*)
				echo_n '安装split apk:'
				local session=$(pm_create --user $_USER_ID | grep -o '[0-9]*')
				[ -z $session ] && echo '!!无法创建安装会话:' && return 1
				local apk
				for apk in $apks; do
					out=$(install_apks $session "$apk" 2>&1); S=$?
					[ $S -ne 0 ] && { pm install-abandon $session &>/dev/null; break; }
				done
				[ $S -eq 0 ] && { out=$(pm install-commit $session 2>&1); S=$?; }
		;;
		esac
	fi
	[ $S -ne 0 ] && echo "错误:$out" && return 1
	stop_app(){ return; }
	# ⟵ 占位：真正实现由 app_restore 覆盖（只 force-stop 一次）
	echo '完成';
}

#1 名称
#2 -n 恢复selinux安全上下文
restore(){
	echo_n "恢复$1:"; eval "local CP=\$$1_CP";
	not_file "$CP" '跳过' && return
	get_app_uid || return 1
	stop_app
	eval "local path=\$app_$1_path"
	mv "$path" "${path}_old" 2>/dev/null
	# ⟵ 旧数据先挪走（但失败被静默忽略）
	if decompress "$CP" "${path%/*}" -o; then
		# ⟵ -o 表示解包时不尝试恢复归档里的属主
		rm -rf "${path}_old"
		chown -hR "$app_uid:$app_uid" "$path"
		# ⟵ uid 与 gid 都用 app_uid（Android 上应用 uid==gid，成立）
		[ -n "$2" ] && recon "$path"
		echo '完成'
	else
		rm -rf "$path"
		mv "${path}_old" "$path" 2>/dev/null
		echo '错误'; return 1
	fi
}

restore_user(){
	echo_n '恢复user:'; not_file "$user_CP" '跳过' && return
	get_app_uid || return 1
	stop_app
	local app_lib=$app_user_path/lib
	[ -h "$app_lib" ] && local app_libD=$(realpath "$app_lib")
	# ⟵ 记住 lib 软链的真实指向（例如 /data/app/~~x==/pkg-1/lib/arm64）
	
	local old="${app_user_path}_old"
	mv "$app_user_path" "$old" 2>/dev/null
	if decompress "$user_CP" "${app_user_path%/*}" -o; then
		rm -rf "$old"
		[ -n "$app_libD" ] && ln -s "$app_libD" "$app_lib"
		# ⟵ 解包后重建 lib 软链，否则 native so 加载失败
		chown -hR "$app_uid:$app_uid" "$app_user_path"
		# [ -n "$app_libU" ] && chown -h "$app_libU:$app_libU" "$app_lib"
		recon "$app_user_path"
		# ⟵ 内部数据**总是**刷 SELinux 上下文
		echo '完成'
	else
		rm -rf "$app_user_path"
		mv "$old" "$app_user_path" 2>/dev/null
		echo '错误'; return 1
	fi
}

#1 应用包名
#2 CPId|压缩包前缀
app_path_init(){
	echo '开始:'$1
	_APP_PKG=$1
	_CPId=$2
	app_data_path=$sd_android/data/$_APP_PKG
	app_apk_obb_path=$sd_android/obb/$_APP_PKG
	# app_media_path=$sd_android/media/$_APP_PKG
	# ⟵ media 目录被注释掉：未支持 /sdcard/Android/media

	app_user_path=/data/user/$_USER_ID/$_APP_PKG
	app_user_de_path=/data/user_de/$_USER_ID/$_APP_PKG
	save_path=$_BACKUP_HOME/AppBackup/$_APP_PKG
	CP_prefix=$save_path/$_CPId-
	# ⟵ CPId = backupTime(毫秒)，既是文件名前缀也是元数据主键
}

#1 包名
#2 CPId
#3 应用备份模式
app_backup(){
	app_path_init $1 $2
	[ -d "$save_path" ] || mkdir -p "$save_path"
	killall -s STOP "$_APP_PKG" 2>/dev/null
	# ⟵ 冻结应用，尽量拿到一致的数据快照（失败静默继续）
	eval $3
	local S=$?
	killall -s CONT "$_APP_PKG" 2>/dev/null
	# ⟵ 解冻（同样失败静默；脚本无 trap，中途被杀会留下 STOP 状态）
	[ $S -ne 0 ] && echo '备份错误' && return 1
	echo '备份完成'
}

#1 包名
#2 CPId
#3 应用恢复模式
app_restore(){
	app_path_init $1 $2

	local f n
	for f in $CP_prefix*'.tar'*; do
		n=${f##*${2}-}
		n=${n%.tar*}
		[ "$n" = '*' ] || eval "${n}_CP='$f'"
	done
	# ⟵ 用 glob 把磁盘上存在的分卷登记成 <part>_CP 变量
	# ⟵ 例如 apk_CP / user_CP / user_de_CP / data_CP / apk_obb_CP
	[ "$n" = '*' ] && echo '!!未找到备份:'$_CPId && return 1

	stop_app(){
		am force-stop --user "$_USER_ID" "$_APP_PKG"
		stop_app(){ return; }
	}
	# ⟵ 只停一次（恢复多个 part 时避免重复 force-stop）

	eval $3
	local S=$?
	unset app_uid apk_CP apk_obb_CP user_CP user_de_CP data_CP
	rm -f "$TMPDIR/"*.apk
	[ $S -ne 0 ] && echo '恢复错误' && return 1
	echo '恢复完成'
}

get_app_uid(){
	[ -n "$app_uid" ] && return
	app_uid=$(STI "$app_user_path" u) && return
	app_uid=$(cat /config/sdcardfs/$_APP_PKG/appid 2>/dev/null) \
		&& app_uid=$_USER_ID$app_uid && return
	app_uid=$(grep -o "^$_APP_PKG [0-9]*" /data/system/packages.list 2>/dev/null) \
		&& app_uid=$_USER_ID${app_uid#* } && return
	echo '!!应用uid获取失败:'$_APP_PKG; return 1
}
# ⟵ 三级回退：现目录属主 → sdcardfs 映射 → packages.list
# ⟵ 这是恢复正确性的最大隐患（见 07 §2.1）

whence echo_n &>/dev/null || echo_n(){ echo -n $*; }
parse_ext(){
	case "$1" in
		*'.tar') echo 'tar';;
		*'.tar.gz') echo 'gzip';;
		*'.tar.xz') echo 'xz';;
		*'.tar.zst') echo 'zstd';;
		*'.tar.lz4') echo 'lz4';;
		*);;
	esac
}
# ⟵ 仅按扩展名判断格式；扩展名不认 → 返回空 → 上层报「未知备份格式」
recon(){
	restorecon -F "$1" 2>/dev/null
	local ctx=$(LZ -d "$1" 2>/dev/null | awk '{print $1}')
	[ -n "$ctx" ] && /system/bin/chcon -R "${ctx%:c*}" "$1" 2>/dev/null
}
# ⟵ 先让系统按策略打默认标签，再用父目录的上下文整树覆盖；
# ⟵ ${ctx%:c*} 去掉 MLS 类别后缀（:c512,c768 之类）
not_file(){
	[ ! -f "$1" ] && { [ $# -lt 2 ] || echo $2; }
}
# is_ok(){
	# [ $? -eq 0 ] && { [ $# -lt 1 ] || echo $1; }
# }
# not_ok(){
	# [ $? -ne 0 ] && { [ $# -lt 1 ] || echo $1; }
# }
echo '0'
# ⟵ 加载完成的哨兵输出；Java 侧比较 TextUtils.join("\n", output) == "0"
```

---

## 函数契约速查

| 函数 | 调用方 | 参数 | 语义 |
|---|---|---|---|
| `app_init` | `c.Cimport.m436finally` | `uid backupHome isBackup compatMode` | 初始化存储根、定义档位动作、安装方式 |
| `compress_init` | `c.Cimport.m436finally` | `ext level` | 设定压缩器与产物后缀；建 `.nomedia` |
| `app_backup` | `c.Cimport.m435extends` | `pkg cpId 'modes'` | 冻结 → `eval modes` → 解冻 |
| `app_restore` | `c.Cimport.m437package` | `pkg cpId 'modes'` | 登记分卷 → `eval modes` → 清理 tmp |
| `backup_apk` / `backup` | 档位函数 | 见上 | 打包单 part |
| `restore_apk` / `restore` / `restore_user` | 档位函数 | 见上 | 解包 + 属性恢复（+ 回滚）|
| `get_app_uid` | restore* | — | 推断目标 uid（三级回退）|
| `recon` | restore_user / restore(x,1) | 路径 | SELinux 上下文恢复 |
| `parse_ext` | compress_init / decompress | 扩展名 | 扩展名 → zstd `--format` |
| `not_file` / `echo_n` | 内部 | — | 判定/输出辅助 |

## 与原 Java 侧的对应关系

| Java 调用点 | 生成的命令行 |
|---|---|
| `c.Cimport.m436finally(z, log)` | `app_init <uid> <backupHome> <1|0> <1|0>`，备份时再跟一条 `test $? -eq 0 && compress_init <ext> <level>` |
| `c.Cimport.m435extends(pkg, ts, modes, log)` | `app_backup <pkg> <ts> '<modes>'` |
| `c.Cimport.m437package(pkg, ts, modes, log)` | `app_restore <pkg> <ts> '<modes>'` |
| `c.Cimport.m438private()`（备份自身） | `test -d '<home>' && { rm -f '<home>'/*.apk*; echo '<label>'; cp '<自身APK>' '<home>/!app!.apk'; }` |
| `b.Cswitch.run()` | `settings put global verifier_verify_adb_installs 0` 等三条（首次加载时） |
| `AppInfoActivity` | `pm grant <pkg> android.permission.INTERACT_ACROSS_USERS` |
| `p029super.Cstatic` | `pm clear --user`、`am force-stop --user`、`pm uninstall --user` |
| `LogsActivity` | `rm -rf '<日志目录>'` |
| `RunCmdActivity` | 用户手输命令（**非 root** shell，flags=9） |
