#!/bin/bash
# coding=utf-8
# vim:et ts=4 sts=4 sw=4
# LastModifyAt:	22:30 2021-02-19
# Author:   	LI Yunfie <yanzilisan183@sina.com>
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
# 更新打包时间
sed -i "s/<yanzilisan183@sina.com> on .\+$/<yanzilisan183@sina.com> on ${var_dtst}/" ./DEBIAN/copyright

# 创建(或清空)临时目录,复制文件
echo " * 正在复制文件和配置文件权限...."
tmpdir=/var/tmp/wbjjdeb
if [ -d "$tmpdir" ]; then
	rm -rf $tmpdir
fi
mkdir -p    $tmpdir/usr/lib/ibus
chmod 755   $tmpdir/usr/lib/ibus
cp ./DEBIAN/ibus-wbjj-engine $tmpdir/usr/lib/ibus/
chmod 755   $tmpdir/usr/lib/ibus/ibus-wbjj-engine
cp ./DEBIAN/ibus-wbjj-setup $tmpdir/usr/lib/ibus/
chmod 755   $tmpdir/usr/lib/ibus/ibus-wbjj-setup

mkdir -p    $tmpdir/usr/lib/pkgconfig
chmod 755   $tmpdir/usr/lib/pkgconfig
cp ./DEBIAN/ibus-wbjj.pc $tmpdir/usr/lib/pkgconfig/
chmod 644   $tmpdir/usr/lib/pkgconfig/ibus-wbjj.pc

mkdir -p    $tmpdir/usr/share/applications
chmod 755   $tmpdir/usr/share/applications
cp ./DEBIAN/ibus-setup-ibus-wbjj.desktop $tmpdir/usr/share/applications/
chmod 644   $tmpdir/usr/share/applications/ibus-setup-ibus-wbjj.desktop

mkdir -p    $tmpdir/usr/share/doc/ibus-wbjj
chmod 755   /usr/share/doc/ibus-wbjj
cp ./DEBIAN/copyright $tmpdir/usr/share/doc/ibus-wbjj/
chmod 644	 $tmpdir/usr/share/doc/ibus-wbjj/copyright

mkdir -p    $tmpdir/usr/share/glib-2.0/schemas
chmod 755   $tmpdir/usr/share/glib-2.0/schemas
cp ./org.freedesktop.ibus.ibus-wbjj.gschema.xml $tmpdir/usr/share/glib-2.0/schemas
chmod 644   $tmpdir/usr/share/glib-2.0/schemas/org.freedesktop.ibus.ibus-wbjj.gschema.xml

mkdir -p    $tmpdir/usr/share/ibus/component
chmod 755   $tmpdir/usr/share/ibus/component
cp ./DEBIAN/ibus-wbjj.xml $tmpdir/usr/share/ibus/component
chmod 644   $tmpdir/usr/share/ibus/component/ibus-wbjj.xml
sed -i "s/ --debug//" $tmpdir/usr/share/ibus/component/ibus-wbjj.xml                            # 关闭调试参数

mkdir -p        $tmpdir/usr/share/ibus-wbjj
chmod 755       $tmpdir/usr/share/ibus-wbjj
cp -R ./data/   $tmpdir/usr/share/ibus-wbjj/
chmod 644       $tmpdir/usr/share/ibus-wbjj/data/*
cp -R ./docs/   $tmpdir/usr/share/ibus-wbjj/
chmod 644       $tmpdir/usr/share/ibus-wbjj/docs/*
cp -R ./engine/ $tmpdir/usr/share/ibus-wbjj/
chmod 644       $tmpdir/usr/share/ibus-wbjj/engine/*
cp -R ./icons/  $tmpdir/usr/share/ibus-wbjj/
chmod 644       $tmpdir/usr/share/ibus-wbjj/icons/*
cp -R ./tables/ $tmpdir/usr/share/ibus-wbjj/
chmod 644       $tmpdir/usr/share/ibus-wbjj/tables/*
sed -i "s/    print(\"DEBUG:/    # print(\"DEBUG:/" $tmpdir/usr/share/ibus-wbjj/engine/*.py     # 注释调试语句

mkdir -p    $tmpdir/usr/share/python3/runtime.d
chmod 755   $tmpdir/usr/share/python3/runtime.d
cp ./DEBIAN/ibus-wbjj.rtupdate $tmpdir/usr/share/python3/runtime.d/
chmod 755   $tmpdir/usr/share/python3/runtime.d/ibus-wbjj.rtupdate

mkdir -p    $tmpdir/DEBIAN
chmod 755   $tmpdir/DEBIAN
cp ./DEBIAN/control  $tmpdir/DEBIAN/
chmod 644   $tmpdir/DEBIAN/control
cp ./DEBIAN/prerm    $tmpdir/DEBIAN/
chmod 755   $tmpdir/DEBIAN/prerm
cp ./DEBIAN/postinst $tmpdir/DEBIAN/
chmod 755   $tmpdir/DEBIAN/postinst


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
if [ -f ./deb/ibus-wbjj-${newvar}-${arc}.deb ]; then
	rm ./deb/ibus-wbjj-${newvar}-${arc}.deb > /dev/null
fi
echo -n "   "
dpkg -b $tmpdir/ ./deb/ibus-wbjj-${newvar}-${arc}.deb

# 清理
rm -rf $tmpdir

echo " * 完成."

