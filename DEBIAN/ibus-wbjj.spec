%define _topdir /var/tmp/wbjj_rpmbuild

Name:    ibus-wbjj
Version: 0.3.40.20210203
Release: 1%{?dist}
Summary: ibus-wbjj rpm package
Group:   Unspecified
License: LGPL
URL:     https://github.com/yanzilisan183/ibus-wbjj
Packager: LI Yunfei <yanzilisan183@sina.com>
BuildRoot: %_topdir/BUILDROOT
Prefix:  /usr/share/ibus-wbjj
#BuildRequires: gcc,make
Requires: ibus >= 1.5.0, python3 >= 3.6.5
 
# 软件的描述
%description
wbjjplus for ibus
 

%install
#rm -rf %{buildroot}
#make install DESTDIR=%{buildroot}
 
# 安装前执行的脚本，语法和shell脚本的语法相同
%pre

# 安装后执行的脚本
%post
 
# 卸载前执行的脚本，如停止进程
%preun
    MSG=`ps -aux | grep "/ibus-wbjj/engine/main.py" | grep -v "grep"`
    if [ -z "$MSG" ];then
        pkill -2 -f /ibus-wbjj/engine/main.py >/dev/null 2>&1
    fi
 
# 卸载完成后执行的脚本
%postun
    rm -rf %{prefix}
    rm -f /usr/libexec/ibus-wbjj-engine
    rm -f /usr/libexec/ibus-wbjj-setup
    rm -f /usr/lib64/pkgconfig/ibus-wbjj.pc
    rm -f /usr/share/applications/ibus-setup-ibus-wbjj.desktop
    rm -f /usr/share/doc/ibus-wbjj/copyright
    rm -f /usr/share/glib-2.0/schemas/org.freedesktop.ibus.ibus-wbjj.gschema.xml
    rm -f /usr/share/ibus/component/ibus-wbjj.xml
    
    
# 清理阶段，在制作完成后删除安装的内容
%clean
rm -rf %{buildroot}
 
#指定要包含的文件
%files
%defattr(-,root,root,0755)
/usr/

%changelog


