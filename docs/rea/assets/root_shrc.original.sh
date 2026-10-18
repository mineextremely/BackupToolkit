export TMPDIR=/data/local/tmp

# alias 要在前面
alias zstd='zstd -T0 -qr --ultra --priority=rt'

add_busybox_applet(){
	eval "alias $1='busybox $1'"
}

add_busybox_applet unzip
add_busybox_applet tar
add_busybox_applet realpath
add_busybox_applet find
add_busybox_applet awk
alias STI='toolkit st_info'
alias LZ='/system/bin/ls -Z'

whence killall &>/dev/null || add_busybox_applet killall
add_busybox_applet grep

SDK_INT=$(getprop ro.build.version.sdk)
if [ "$SDK_INT" -ge 34 ]; then
	alias pm_install='pm install -r -t -d -i com.android.vending --bypass-low-target-sdk-block'
	alias pm_create='pm install-create -r -t -d -i com.android.vending --bypass-low-target-sdk-block'
else
	alias pm_install='pm install -r -t -d -i com.android.vending'
	alias pm_create='pm install-create -r -t -d -i com.android.vending'
fi

#1 用户ID
#2 备份目录
#3 =1?备份:恢复
#4 =1?兼容模式:默认模式
app_init(){
	sd_android=/data/media/$1/Android
	[[ $1 -eq 0 && ! -d "$sd_android" ]] && sd_android=$(realpath /sdcard)/Android
	[ ! -d "$sd_android" ] && echo '!!未找到用户存储:'$1 && return 1

	if [ $1 -eq 0 ]; then
  	pm_path(){ pm path $_APP_PKG; }
	else
		pm_path(){ pm path --user $_USER_ID $_APP_PKG; }
	fi

	if [ $3 -eq 1 ]; then
		apk(){ backup_apk && backup apk_obb; }
		data(){ backup data cache; }
		user(){ backup user lib oat cache code_cache no_backup && backup user_de lib oat cache code_cache no_backup; }
	else
		apk(){ restore_apk && restore apk_obb; }
		data(){ restore data; }
		user(){ restore_user && restore user_de 1; }
		if [ $4 -eq 1 ]; then
			if [ "$SDK_INT" -ge 23 ]; then
				install_apk(){ cat "$1" | pm_install --user $_USER_ID -S $(STI "$1" s) 2>&1; }
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
			install_apks(){ pm install-write "$1" "${2##*/}" "$2"; }
		fi
	fi

	_USER_ID=$1
	_BACKUP_HOME=$2
}

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
	fi
	[ ! -f "$_BACKUP_HOME/.nomedia" ] && {
		mkdir -p "$_BACKUP_HOME"
		touch "$_BACKUP_HOME/.nomedia"
	}
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
	fi
	eval "tar -c $tar_opts $exclude $compress_to_file '$file'"
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

backup_apk(){
	echo_n '备份apk:'
	local tar_opts val _C dir
	for val in $(pm_path 2>/dev/null); do
		val=${val#*:}
		[[ "$val" != /data/* && -z $(unzip -lqq "$val" classes.dex) ]] && echo "跳过" && return
		dir=${val%/*}
		if [ "$_C" != "$dir" ]; then
			_C=$dir
			tar_opts="${tar_opts} -C '$dir' '${val##*/}'"
		else
			tar_opts="${tar_opts} '${val##*/}'"
		fi
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
	if decompress "$CP" "${path%/*}" -o; then
		rm -rf "${path}_old"
		chown -hR "$app_uid:$app_uid" "$path"
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
	
	local old="${app_user_path}_old"
	mv "$app_user_path" "$old" 2>/dev/null
	if decompress "$user_CP" "${app_user_path%/*}" -o; then
		rm -rf "$old"
		[ -n "$app_libD" ] && ln -s "$app_libD" "$app_lib"
		chown -hR "$app_uid:$app_uid" "$app_user_path"
		# [ -n "$app_libU" ] && chown -h "$app_libU:$app_libU" "$app_lib"
		recon "$app_user_path"
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

	app_user_path=/data/user/$_USER_ID/$_APP_PKG
	app_user_de_path=/data/user_de/$_USER_ID/$_APP_PKG
	save_path=$_BACKUP_HOME/AppBackup/$_APP_PKG
	CP_prefix=$save_path/$_CPId-
}

#1 包名
#2 CPId
#3 应用备份模式
app_backup(){
	app_path_init $1 $2
	[ -d "$save_path" ] || mkdir -p "$save_path"
	killall -s STOP "$_APP_PKG" 2>/dev/null
	eval $3
	local S=$?
	killall -s CONT "$_APP_PKG" 2>/dev/null
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
	[ "$n" = '*' ] && echo '!!未找到备份:'$_CPId && return 1

	stop_app(){
		am force-stop --user "$_USER_ID" "$_APP_PKG"
		stop_app(){ return; }
	}

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
recon(){
	restorecon -F "$1" 2>/dev/null
	local ctx=$(LZ -d "$1" 2>/dev/null | awk '{print $1}')
	[ -n "$ctx" ] && /system/bin/chcon -R "${ctx%:c*}" "$1" 2>/dev/null
}
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
