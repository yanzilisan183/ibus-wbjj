#!/bin/bash
# coding=utf-8
# vim:et sts=4 sw=4
# LastModifyAt:	11:23 2021-01-12
# Author:		LI Yunfie<yanzilisan183@sina.com>
# Description:	deb格式打包

u=`whoami`
if [ "$u" != "root" ]; then
	echo " * 正在使用 sudo 重新调用该脚本...."
	sudo $0
	exit $?
fi

# 提取当前脚本所在路径
cupath=$(readlink -f $0 | sed -n "s/$(basename $0)//"p)
cd "$cupath"

# 提取 DEBIAN/control 中的架构和版本号
arc=`sed -n 's/Architecture: //p' DEBIAN/control`
var=`sed -n 's/Version: //p' DEBIAN/control`
array=(${var//./ })  
var_major=${array[0]}
var_minor=${array[1]}
var_revision=`expr ${array[2]} + 1`
var_date=`date "+%Y%m%d"`
var_dtst=`date "+%F %T %z"`
newvar="${var_major}.${var_minor}.${var_revision}.${var_date}"
year=`date "+%Y"`

# 更新版本号
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
crl_file_str="./DEBIAN/ibus-wbjj-engine ./DEBIAN/ibus-wbjj-setup ./engine/factory.py ./engine/main.py ./engine/setup.py ./engine/setup.ui ./engine/tabdict.py ./engine/table.py ./engine/tabsqlitedb.py ./engine/wbjj.py"
crl_file_arr=($crl_file_str)
for onefile in ${crl_file_arr[@]}
do
	str_o=`grep -e "2013-[0-9]\+ LI Yunfei" ${onefile} | md5sum`
	str_n=`grep -e "2013-${year} LI Yunfei" ${onefile} | md5sum`
	if [ "$str_o" != "$str_n" ]; then
		sed -i "s/2013-[0-9]\+ LI Yunfei/2013-${year} LI Yunfei/" ${onefile}
	fi
done
# 更新打包时间
sed -i "s/<yanzilisan183@sina.com> on .\+$/<yanzilisan183@sina.com> on ${var_dtst}/" ./DEBIAN/copyright

# 创建(或清空)临时目录,复制文件
echo " * 正在复制文件和配置文件权限...."
tmpdir=/var/tmp/wbjjdeb
if [ -d "$tmpdir" ]; then
	rm -rf $tmpdir
fi
sudo mkdir -p    $tmpdir/usr/lib/ibus
sudo chmod 755   $tmpdir/usr/lib/ibus
sudo cp ./DEBIAN/ibus-wbjj-engine $tmpdir/usr/lib/ibus/
sudo chmod 755   $tmpdir/usr/lib/ibus/ibus-wbjj-engine
sudo cp ./DEBIAN/ibus-wbjj-setup $tmpdir/usr/lib/ibus/
sudo chmod 755   $tmpdir/usr/lib/ibus/ibus-wbjj-setup

sudo mkdir -p    $tmpdir/usr/lib/pkgconfig
sudo chmod 755   $tmpdir/usr/lib/pkgconfig
sudo cp ./DEBIAN/ibus-wbjj.pc $tmpdir/usr/lib/pkgconfig/
sudo chmod 644   $tmpdir/usr/lib/pkgconfig/ibus-wbjj.pc

sudo mkdir -p    $tmpdir/usr/share/applications
sudo chmod 755   $tmpdir/usr/share/applications
sudo cp ./DEBIAN/ibus-setup-ibus-wbjj.desktop $tmpdir/usr/share/applications/
sudo chmod 644   $tmpdir/usr/share/applications/ibus-setup-ibus-wbjj.desktop

sudo mkdir -p    $tmpdir/usr/share/doc/ibus-wbjj
sudo chmod 755   /usr/share/doc/ibus-wbjj
sudo cp ./DEBIAN/copyright $tmpdir/usr/share/doc/ibus-wbjj/
sudo chmod 644	 $tmpdir/usr/share/doc/ibus-wbjj/copyright

sudo mkdir -p    $tmpdir/usr/share/glib-2.0/schemas
sudo chmod 755   $tmpdir/usr/share/glib-2.0/schemas
sudo cp ./org.freedesktop.ibus.ibus-wbjj.gschema.xml $tmpdir/usr/share/glib-2.0/schemas
sudo chmod 644   $tmpdir/usr/share/glib-2.0/schemas/org.freedesktop.ibus.ibus-wbjj.gschema.xml

sudo mkdir -p    $tmpdir/usr/share/ibus/component
sudo chmod 755   $tmpdir/usr/share/ibus/component
sudo cp ./DEBIAN/ibus-wbjj.xml $tmpdir/usr/share/ibus/component
sudo chmod 644   $tmpdir/usr/share/ibus/component/ibus-wbjj.xml
sed -i "s/ --debug//" $tmpdir/usr/share/ibus/component/ibus-wbjj.xml        # 关闭调试参数

sudo mkdir -p        $tmpdir/usr/share/ibus-wbjj
sudo chmod 755       $tmpdir/usr/share/ibus-wbjj
sudo cp -R ./data/   $tmpdir/usr/share/ibus-wbjj/
sudo chmod 644       $tmpdir/usr/share/ibus-wbjj/data/*
sudo cp -R ./docs/   $tmpdir/usr/share/ibus-wbjj/
sudo chmod 644       $tmpdir/usr/share/ibus-wbjj/docs/*
sudo cp -R ./engine/ $tmpdir/usr/share/ibus-wbjj/
sudo chmod 644       $tmpdir/usr/share/ibus-wbjj/engine/*
sudo cp -R ./icons/  $tmpdir/usr/share/ibus-wbjj/
sudo chmod 644       $tmpdir/usr/share/ibus-wbjj/icons/*
sudo cp -R ./tables/ $tmpdir/usr/share/ibus-wbjj/
sudo chmod 644       $tmpdir/usr/share/ibus-wbjj/tables/*

sudo mkdir -p    $tmpdir/usr/share/python3/runtime.d
sudo chmod 755   $tmpdir/usr/share/python3/runtime.d
sudo cp ./DEBIAN/ibus-wbjj.rtupdate $tmpdir/usr/share/python3/runtime.d/
sudo chmod 755   $tmpdir/usr/share/python3/runtime.d/ibus-wbjj.rtupdate

sudo mkdir -p    $tmpdir/DEBIAN
sudo chmod 755   $tmpdir/DEBIAN
sudo cp ./DEBIAN/control $tmpdir/DEBIAN/
sudo chmod 644   $tmpdir/DEBIAN/control

# 统计解包大小并写入 DEBIAN/control 的 Installed-Size: 
echo " * 正在写 DEBIAN/control 的 Installed-Size ...."
size=`du -s $tmpdir/usr/ | sed -n 's/\t.*$//p'`
sed -i "s/Installed-Size:.*$/Installed-Size: ${size}/" $tmpdir/DEBIAN/control

# 写MD5校验文件
echo " * 正在写 DEBIAN/md5sums 校验文件...."
cd $tmpdir
md5sum `find usr -type f` > $tmpdir/DEBIAN/md5sums
cd - > /dev/null

# 设置权限,解决安装时报"软件报质量欠佳"问题
echo " * 正在重置 owner 和 group ...."
chown -R 0 $tmpdir
chgrp -R 0 $tmpdir

# 打包
echo " * 正在打包deb...."
if [ -f ./deb/wbjjplus_for_ibus_${newvar}_${arc}.deb ]; then
	rm ./deb/wbjjplus_for_ibus_${newvar}_${arc}.deb > /dev/null
fi
echo -n "   "
dpkg -b $tmpdir/ ./deb/wbjjplus_for_ibus_${newvar}_${arc}.deb

# 清理
rm -rf $tmpdir

echo " * 完成."

