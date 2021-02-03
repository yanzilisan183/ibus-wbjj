#!/bin/bash
# coding=utf-8
# vim:et ts=4 sts=4 sw=4
# LastModifyAt:	10:19 2021-02-03
# Author:	LI Yunfie<yanzilisan183@sina.com>
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
arc=x86_64
var=`sed -n 's/Version: //p' DEBIAN/control`
array=(${var//./ })
var_major=${array[0]}
var_minor=${array[1]}
var_revision=`expr ${array[2]}` # 跟随deb版本,不自动递增
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
vfile=./DEBIAN/ibus-wbjj.spec
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
rpmdir=/var/tmp/wbjj_rpmbuild
if [ -d "$rpmdir" ]; then
	rm -rf $tmpdir
fi
mkdir -pv $rpmdir/{BUILD,BUILDROOT,RPMS,SOURCES,SPECS,SRPMS} > /dev/null
tmpdir=$rpmdir/BUILDROOT

mkdir -p    $tmpdir/usr/libexec
chmod 755   $tmpdir/usr/libexec
cp ./DEBIAN/ibus-wbjj-engine $tmpdir/usr/libexec/
chmod 755   $tmpdir/usr/libexec/ibus-wbjj-engine
cp ./DEBIAN/ibus-wbjj-setup $tmpdir/usr/libexec/
chmod 755   $tmpdir/usr/libexec/ibus-wbjj-setup

#mkdir -p    $tmpdir/usr/lib64/pkgconfig
#chmod 755   $tmpdir/usr/lib64/pkgconfig
#cp ./DEBIAN/ibus-wbjj.pc $tmpdir/usr/lib64/pkgconfig/
#chmod 644   $tmpdir/usr/lib64/pkgconfig/ibus-wbjj.pc

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
sed -i "s/lib\/ibus/libexec/" $tmpdir/usr/share/ibus/component/ibus-wbjj.xml                    # 变更路径信息

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

# 编译py
echo " * 正在将.py编译为.pyc...."
python3 -m compileall $tmpdir/usr/share/ibus-wbjj/engine/ > /dev/null
chmod 644       $tmpdir/usr/share/ibus-wbjj/engine/__pycache__/*

# 打包
echo " * 正在打包rpm...."
rpmbuild -bb --buildroot=$tmpdir --target=$arc DEBIAN/ibus-wbjj.spec

# 签名


if [ -f $rpmdir/RPMS/$arc/ibus-wbjj-${newvar}-1.$arc.rpm ]; then
	mv $rpmdir/RPMS/$arc/ibus-wbjj-${newvar}-1.$arc.rpm ./rpm/ > /dev/null
fi

# 清理
rm -rf $rpmdir

echo " * 完成."

