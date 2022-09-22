#!/bin/bash
# coding=utf-8
# vim:et ts=4 sts=4 sw=4
# LastModifyAt:	15:43 2022-09-21
# Author:       LI Yunfie <yanzilisan183@sina.com>
# Discription:	复制相关文件到本机安装目录进行测试

u=`whoami`
if [ "$u" == "root" ]; then
	echo " * 请勿使用root执行此脚本"
	exit 1
fi

# 停止ibus-wbjj主进程
sudo pkill -2 -f /ibus-wbjj/engine/main.py >/dev/null 2>&1

# 提取当前脚本所在路径
cupath=$(readlink -f $0 | sed -n "s/$(basename $0)//"p)
cd "$cupath"

# 提取 DEBIAN/control 中的架构和版本号
arc=`sed -n 's/Architecture: //p' DEBIAN/control`
var=`sed -n 's/Version: //p' DEBIAN/control`
array=(${var//./ })  
var_major=${array[0]}
var_minor=${array[1]}
var_revision=${array[2]}     # install模式下不自动递增版本号 var_revision=`expr ${array[2]} + 1`
var_date=`date "+%Y%m%d"`
var_dtst=`date "+%F %T %z"`
newvar="${var_major}.${var_minor}.${var_revision}.${var_date}"
year=`date "+%Y"`

# 更新版本号
echo ""
echo " * 正在更新版本号...."
vfile=./DEBIAN/control
str_o=`grep -e "Version: [0-9\.]\+$" ${vfile} | md5sum`
str_n=`grep -e "Version: ${newvar}$" ${vfile} | md5sum`
if [ "$str_o" != "$str_n" ]; then
	sed -i "s/Version: [0-9\.]\+$/Version: ${newvar}/" ${vfile}
fi
vfile=./DEBIAN/ibus-wbjj.pc
str_o=`grep -e "Version: [0-9\.]\+$" ${vfile} | md5sum`
str_n=`grep -e "Version: ${newvar}$" ${vfile} | md5sum`
if [ "$str_o" != "$str_n" ]; then
	sed -i "s/Version: [0-9\.]\+$/Version: ${newvar}/" ${vfile}
fi
vfile=./DEBIAN/ibus-wbjj.xml
str_o=`grep -e "<version>[0-9\.]\+<\/version>" ${vfile} | md5sum`
str_n=`grep -e "<version>${newvar}<\/version>" ${vfile} | md5sum`
if [ "$str_o" != "$str_n" ]; then
	sed -i "s/<version>[0-9\.]\+<\/version>/<version>${newvar}<\/version>/" ${vfile}
fi
vfile=./engine/wbjj.py
str_o=`grep -e "^version\s\+=\s\+\"[0-9\.]\+\"$" ${vfile} | md5sum`
str_n=`grep -e "^version\s\+=\s\+\"${var_major}.${var_minor}.${var_revision}\"$" ${vfile} | md5sum`
if [ "$str_o" != "$str_n" ]; then
	sed -i "s/^version\s\+=\s\+\"[0-9\.]\+\"$/version       = \"${var_major}.${var_minor}.${var_revision}\"/" ${vfile}
fi
vfile=./engine/wbjj.py
str_o=`grep -e "^date\s\+=\s\+\"[0-9]\+\"$" ${vfile} | md5sum`
str_n=`grep -e "^date\s\+=\s\+\"${var_date}\"$" ${vfile} | md5sum`
if [ "$str_o" != "$str_n" ]; then
	sed -i "s/^date\s\+=\s\+\"[0-9]\+\"$/date          = \"${var_date}\"/" ${vfile}
fi

# 更新版权年份
crl_file_str="./DEBIAN/ibus-wbjj-engine ./DEBIAN/ibus-wbjj-setup ./DEBIAN/ibus-wbjj.rtupdate ./engine/factory.py ./engine/main.py ./engine/setup.py ./engine/setup.ui ./engine/tabdict.py ./engine/table.py ./engine/tabsqlitedb.py ./engine/wbjj.py"
crl_file_arr=($crl_file_str)
for onefile in ${crl_file_arr[@]}
do
	str_o=`grep -e "2013-[0-9]\+ LI Yunfei" ${onefile} | md5sum`
	str_n=`grep -e "2013-${year} LI Yunfei" ${onefile} | md5sum`
	if [ "$str_o" != "$str_n" ]; then
		sed -i "s/2013-[0-9]\+ LI Yunfei/2013-${year} LI Yunfei/" ${onefile}
	fi
done
# 更新打包时间(仅打包时更新)
# sed -i "s/<yanzilisan183@sina.com> on .\+$/<yanzilisan183@sina.com> on ${var_dtst}/" ./usr/share/doc/ibus-wbjj/copyright

# 关闭ibus中文输入法,切换到英文模式
ibus engine xkb:us::eng >/dev/null 2>&1

echo " * 正在复制文件和配置文件权限...."
if [ ! -d "/usr/lib/ibus" ]; then
	sudo mkdir -p    /usr/lib/ibus
	sudo chown root:root /usr/lib/ibus
	sudo chmod 755   /usr/lib/ibus
fi
sudo cp ./DEBIAN/ibus-wbjj-engine /usr/lib/ibus/
sudo chown root:root /usr/lib/ibus/ibus-wbjj-engine
sudo chmod 755       /usr/lib/ibus/ibus-wbjj-engine
sudo cp ./DEBIAN/ibus-wbjj-setup /usr/lib/ibus/
sudo chown root:root /usr/lib/ibus/ibus-wbjj-setup
sudo chmod 755       /usr/lib/ibus/ibus-wbjj-setup
if [ ! -d "/usr/lib/pkgconfig" ]; then
	sudo mkdir -p    /usr/lib/pkgconfig
	sudo chown root:root /usr/lib/pkgconfig
	sudo chmod 755   /usr/lib/pkgconfig
fi
sudo cp ./DEBIAN/ibus-wbjj.pc /usr/lib/pkgconfig/
sudo chown root:root /usr/lib/pkgconfig/ibus-wbjj.pc
sudo chmod 644       /usr/lib/pkgconfig/ibus-wbjj.pc
if [ ! -d "/usr/share/applications" ]; then
	sudo mkdir -p    /usr/share/applications
	sudo chown root:root /usr/share/applications
	sudo chmod 755   /usr/share/applications
fi
sudo cp ./DEBIAN/ibus-setup-ibus-wbjj.desktop /usr/share/applications/
sudo chown root:root /usr/share/applications/ibus-setup-ibus-wbjj.desktop
sudo chmod 644       /usr/share/applications/ibus-setup-ibus-wbjj.desktop
if [ ! -d "/usr/share/doc/ibus-wbjj" ]; then
	sudo mkdir -p    /usr/share/doc/ibus-wbjj
	sudo chown root:root /usr/share/doc/ibus-wbjj
	sudo chmod 755   /usr/share/doc/ibus-wbjj
fi
sudo cp ./DEBIAN/copyright /usr/share/doc/ibus-wbjj/
sudo chown root:root /usr/share/doc/ibus-wbjj/copyright
sudo chmod 644		 /usr/share/doc/ibus-wbjj/copyright
if [ ! -d "/usr/share/glib-2.0/schemas" ]; then
	sudo mkdir -p    /usr/share/glib-2.0/schemas
	sudo chown root:root /usr/share/glib-2.0/schemas
	sudo chmod 755   /usr/share/glib-2.0/schemas
fi
sudo cp ./org.freedesktop.ibus.ibus-wbjj.gschema.xml /usr/share/glib-2.0/schemas
sudo chown root:root /usr/share/glib-2.0/schemas/org.freedesktop.ibus.ibus-wbjj.gschema.xml
sudo chmod 644       /usr/share/glib-2.0/schemas/org.freedesktop.ibus.ibus-wbjj.gschema.xml
if [ ! -d "/usr/share/ibus/component" ]; then
	sudo mkdir -p    /usr/share/ibus/component
	sudo chown root:root /usr/share/ibus/component
	sudo chmod 755   /usr/share/ibus/component
fi
sudo cp ./DEBIAN/ibus-wbjj.xml /usr/share/ibus/component
sudo chown root:root /usr/share/ibus/component/ibus-wbjj.xml
sudo chmod 644       /usr/share/ibus/component/ibus-wbjj.xml
if [ ! -d "/usr/share/ibus/ibus-wbjj" ]; then
	sudo mkdir -p    /usr/share/ibus/ibus-wbjj
	sudo chown root:root /usr/share/ibus/ibus-wbjj
	sudo chmod 755   /usr/share/ibus/ibus-wbjj
fi
sudo cp -R ./data/ /usr/share/ibus-wbjj/
sudo chmod 644       /usr/share/ibus-wbjj/data/*
sudo cp -R ./docs/ /usr/share/ibus-wbjj/
sudo chmod 644       /usr/share/ibus-wbjj/docs/*
sudo cp -R ./engine/ /usr/share/ibus-wbjj/
sudo chmod 644       /usr/share/ibus-wbjj/engine/*
sudo cp -R ./icons/ /usr/share/ibus-wbjj/
sudo chmod 644       /usr/share/ibus-wbjj/icons/*
sudo cp -R ./tables/ /usr/share/ibus-wbjj/
sudo chmod 644       /usr/share/ibus-wbjj/tables/*
sudo chown -R root:root /usr/share/ibus-wbjj
if [ ! -d "/usr/share/python3/runtime.d" ]; then
	sudo mkdir -p    /usr/share/python3/runtime.d
	sudo chown root:root /usr/share/python3/runtime.d
	sudo chmod 755   /usr/share/python3/runtime.d
fi
sudo cp ./DEBIAN/ibus-wbjj.rtupdate /usr/share/python3/runtime.d/
sudo chmod 755       /usr/share/python3/runtime.d/ibus-wbjj.rtupdate

# 开启调试参数(非ibus-daemon子进程,可能导至IBus.Bus.get_connection()返回None)
# sudo sed -i "s/ --ibus<\/exec>/ --ibus --debug<\/exec>/" /usr/share/ibus/component/ibus-wbjj.xml

echo " * 正在更新gsettings...."
sudo glib-compile-schemas /usr/share/glib-2.0/schemas

echo " * 正在重启IBus...."
ibus engine xkb:us::eng
# -r:替换当前进程, -x:运行XIM Server, -v:输出更多信息, -d:转入后台以daemon方式运行,不加此参数则可将更多错误信息输出到终端
#ibus-daemon -rxvd
ibus-daemon -rxv &
# ibus engine ibus-wbjj >/dev/null 2>&1

echo " * 完成."

