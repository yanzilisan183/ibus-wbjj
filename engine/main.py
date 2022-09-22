# coding=utf-8
# vim:et st=4 sts=4 sw=4
#
# ibus-wbjj - 五笔加加Plus for IBus
#
# Copyright (C) 2013-2022 LI Yunfei <yanzilisan183@sina.com>
#
# This library is free software; you can redistribute it and/or modify it under the terms 
# of the GNU Lesser General Public License as published by the Free Software Foundation;
# either version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; 
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License along with this library;
# if not, write to the Free Software Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

import os
import re
import sys
import optparse
from signal import signal, SIGTERM, SIGINT
from gi import require_version
require_version('IBus', '1.0')
from gi.repository import IBus
from gi.repository import GLib
import factory
import tabsqlitedb
import wbjj


opt = optparse.OptionParser()
opt.set_usage('%prog --table a_table.db')
opt.add_option('--table', '-t',
        action='store', type='string', dest='db', default=wbjj.db,
        help='Set the IME table file, default: %default')
opt.add_option('--daemon', '-d',
        action='store_true', dest='daemon', default=False,
        help='Run as daemon, default: %default')
opt.add_option('--ibus', '-i',
        action='store_true', dest='ibus', default=False,
        help='Set the IME icon file, default: %default')
opt.add_option('--xml', '-x',
        action='store_true', dest='xml', default=False,
        help='Output the engines xml part, default: %default')
opt.add_option('--nolog', '-n',
        action='store_false', dest='log', default=True,
        help='Redirect stdout and stderr to ' + wbjj.log + ', default: %default')
opt.add_option('--debug', '-e',
        action='store_true', dest='debug', default=False,
        help='Debug mode, default: %default')
(wbjj.options, args) = opt.parse_args()

class IMApp:
    def __init__(self, dbfile, exec_by_ibus):
        self.__mainloop = GLib.MainLoop()
        self.__bus = IBus.Bus()
        self.__bus.connect("disconnected", self.__bus_destroy_cb)
        self.__factory = factory.EngineFactory(self.__bus, dbfile)
        self.destroyed = False
        if exec_by_ibus:
            self.__bus.request_name(wbjj.requestpath, 0)
        else:
            self.__component = IBus.Component(
                name=wbjj.requestpath,
                description=wbjj.description_short,
                version=wbjj.version,
                license=wbjj.license,
                author=wbjj.author,
                homepage=wbjj.homepage,
                textdomain='ibus-wbjj')
            # now we get IME info from wbjj.py
            engine = IBus.EngineDesc(
                name=wbjj.name(),
                longname=wbjj.longname(),
                description=wbjj.description_short,
                language=wbjj.language,
                license=wbjj.license,
                author=wbjj.author,
                icon=wbjj.icon,
                layout=wbjj.layout)
            self.__component.add_engine(engine)
            self.__bus.register_component(self.__component)
            

    def run(self):
        self.__mainloop.run()
        self.__bus_destroy_cb()

    def quit(self):
        self.__bus_destroy_cb()

    def __bus_destroy_cb(self, bus=None):
        if self.destroyed:
            return
        self.__factory.do_destroy()
        self.destroyed = True
        self.__mainloop.quit()
        print("-----  finalizing  --------------")

def cleanup(ima_ins):
    ima_ins.quit()
    sys.exit()

def indent(element, level=0):
    '''XML格式化 Use to format xml Element pretty :)'''
    i = "\n" + level*"    "
    if element:
        if not element.text or not element.text.strip():
            element.text = i + "    "
        for subelement in element:
            indent(subelement, level+1)
            if not subelement.tail or not subelement.tail.strip():
                subelement.tail = i + "    "
        if not subelement.tail or not subelement.tail.strip():
            subelement.tail = i
    else:
        if level and (not element.tail or not element.tail.strip()):
            element.tail = i

def main():
    if wbjj.options.xml:
        from xml.etree.ElementTree import Element, SubElement, tostring
        # 输出引擎XML并退出
        egs = Element('engines')
        _engine = SubElement(egs, 'engine')
        # 引擎名节点(去掉.db的数据库名)
        _name = SubElement(_engine, 'name')
        _name.text = wbjj.sysname
        # 长名称节点(数据库中的输入法名,对应当前系统语言)
        _longname = SubElement(_engine, 'longname')
        _longname.text = wbjj.name()
        # 语言节点(忽略区域,只保留语言 we ignore the place)
        _language = SubElement(_engine, 'language')
        _language.text = wbjj.language
        # 许可节点
        _license = SubElement(_engine, 'license')
        _license.text = wbjj.license
        # 作者节点
        _author = SubElement(_engine, 'author')
        _author.text = wbjj.author
        # 图标节点
        _icon = SubElement(_engine, 'icon')
        _icon.text = wbjj.trayicon
        _icon_prop_key = SubElement(_engine, 'icon_prop_key')
        _icon_prop_key.text = "InputMode"
        # UI文字节点
        _symbol = SubElement(_engine, 'symbol')
        _symbol.text = wbjj.symbol
        # 键盘布局节点
        _layout = SubElement(_engine, 'layout')
        _layout.text = wbjj.layout
        # 描述节点
        _desc = SubElement(_engine, 'description')
        _desc.text = wbjj.description_short
        # 配置节点
        _setup = SubElement(_engine, 'setup')
        _setup.text = wbjj.setup
        # 
        _textdomain = SubElement(_engine, 'textdomain')
        _textdomain.text = wbjj.sysname
        # 格式化输出
        indent(egs)
        egsout = tostring(egs, encoding='utf-8').decode('utf-8')
        patt = re.compile(r'<\?.*\?>\n')
        egsout = patt.sub('', egsout)
        # Always write xml output in UTF-8 encoding, not in the
        # encoding of the current locale, otherwise it might fail
        # if conversion into the encoding of the current locale is
        # not possible:
        #print(egsout)  # 系统XML输出,并非调试输出
        if sys.version_info >= (3, 0, 0):
            sys.stdout.buffer.write((egsout+'\n').encode('utf-8'))
        else:
            sys.stdout.write((egsout+'\n').encode('utf-8'))
        return 0
    else:
        wbjj.check_dir()    # 验证目录
        if wbjj.options.log and (not wbjj.options.debug):
            sys.stdout = open(wbjj.log, 'a', buffering=1)
            sys.stderr = open(wbjj.log, 'a', buffering=1)
        from time import strftime
        print('\n\n----- %s  ibus-wbjj start with IBus v%s.%s.%s -----' % (strftime('%Y-%m-%d %H:%M:%S'), IBus.MAJOR_VERSION, IBus.MINOR_VERSION, IBus.MICRO_VERSION))

    if wbjj.options.daemon:
        if os.fork():
            sys.exit()

    if wbjj.options.db:
        wbjj.check_dir()    # 验证目录
        if os.access(wbjj.options.db, os.F_OK):
            db = wbjj.options.db
        else:
            db = wbjj.db
    else:
        db = ""
    ima = IMApp(db, wbjj.options.ibus)
    signal(SIGTERM, lambda signum, stack_frame: cleanup(ima))
    signal(SIGINT, lambda signum, stack_frame: cleanup(ima))
    try:
        ima.run()
    except KeyboardInterrupt:
        ima.quit()
        #import traceback
        #traceback.print_exc()


if __name__ == "__main__":
    main()

