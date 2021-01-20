# coding=utf-8
# vim:et sts=4 sw=4
#
# ibus-wbjj - 五笔加加Plus for IBus
#
# Copyright (C) 2013-2021 LI Yunfei <yanzilisan183@gmail.com>
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
import sys
from gi import require_version
require_version('Gio', '2.0')
from gi.repository import Gio
require_version('Gtk', '3.0')
from gi.repository import Gtk
require_version('Gdk', '3.0')
from gi.repository import Gdk
require_version('GLib', '2.0')
from gi.repository import GLib
GLib.set_application_name('ibus-wbjj Setup')
GLib.set_prgname('ibus-setup-wbjj')
from gi import require_version
require_version('IBus', '1.0')
from gi.repository import IBus

import time
import locale
import sqlite3
import tabdict
import wbjj
from xdg import BaseDirectory


class PreferencesDialog:
    def __init__(self):
        def __dialog_response_cb(widget, value):
            widget.destroy()
        wbjj.check_dir()    # 验证目录
        self.__bus = IBus.Bus()
        self.__cfg = Gio.Settings(schema=wbjj.requestpath.lower(), path='/' + wbjj.requestpath.lower().replace('.','/') + '/')
        self.__builder = Gtk.Builder()
        self.__builder.set_translation_domain("ibus-wbjj")
        self.__builder.add_from_file(wbjj.enginepath + "setup.ui")
        self.__dialog = self.__builder.get_object("dialog")
        self.__dialog.set_modal(True)
        self.__dialog.set_icon_from_file(wbjj.icon)
        self.__dialog.set_keep_above(True)
        self.__init_pages()
        self.__init_general()
        self.__init_advanced()
        self.__init_custom()
        self.__init_dictionary()
        self.__init_about()
        self.__pages.set_current_page(0)
        self.__dialog.connect("response", __dialog_response_cb)

    def __init_pages(self):
        self.__pages = self.__builder.get_object("pages")
        self.__page_general = self.__builder.get_object("pageGeneral")
        self.__page_advanced = self.__builder.get_object("pageAdvanced")
        self.__page_custom = self.__builder.get_object("pageCustom")
        self.__page_dictionary = self.__builder.get_object("pageDictionary")
        self.__page_about = self.__builder.get_object("pageAbout")
        self.__page_general.hide()
        self.__page_advanced.hide()
        self.__page_custom.hide()
        self.__page_dictionary.hide()
        self.__page_about.hide()

    def __init_general(self):
        self.__page_general.show()
        
        key = "init-english"
        self.__init_english = [self.__builder.get_object(key), self.__builder.get_object(key+"_False")]
        self.__init_english[int(not self.__get_boolean(key, False))].set_active(True)
        self.__init_english[0].connect("toggled", self.__toggled_cb, key)

        key = "chinese-mode"
        self.__chinese_mode = self.__builder.get_object(key)
        self.__chinese_mode.set_active(self.__get_enum(key, 0))	# 简体
        self.__chinese_mode.connect("changed", self.__selected_cb, key)

        key = "full-width-letter"
        self.__fullwidth_letter = [self.__builder.get_object(key), self.__builder.get_object(key+"_False")]
        self.__fullwidth_letter[int(not self.__get_boolean(key, False))].set_active(True)
        self.__fullwidth_letter[0].connect("toggled", self.__toggled_cb, key)

        key = "full-width-punct"
        self.__fullwidth_punct = [self.__builder.get_object(key), self.__builder.get_object(key+"_False")]
        self.__fullwidth_punct[int(not self.__get_boolean(key, False))].set_active(True)
        self.__fullwidth_punct[0].connect("toggled", self.__toggled_cb, key)

        key = "one-char"
        self.__onechar = [self.__builder.get_object(key), self.__builder.get_object(key+"_False")]
        self.__onechar[int(not self.__get_boolean(key, False))].set_active(True)
        self.__onechar[0].connect("toggled", self.__toggled_cb, key)

        key = "auto-commit"
        self.__autocommit = [self.__builder.get_object(key), self.__builder.get_object(key+"_False")]
        self.__autocommit[int(not self.__get_boolean(key, False))].set_active(True)
        self.__autocommit[0].connect("toggled", self.__toggled_cb, key)

        key = "chinese-digital"
        self.__chinese_digital = [self.__builder.get_object(key), self.__builder.get_object(key+"_False")]
        self.__chinese_digital[int(not self.__get_boolean(key, False))].set_active(True)
        self.__chinese_digital[0].connect("toggled", self.__toggled_cb, key)

        key = "dynamic-adjust"
        self.__dynamic_adjust = [self.__builder.get_object(key), self.__builder.get_object(key+"_False")]
        self.__dynamic_adjust[int(not self.__get_boolean(key, False))].set_active(True)
        self.__dynamic_adjust[0].connect("toggled", self.__toggled_cb, key)

        key = "pinyin-fuzzy-tone"
        self.__pinyin_fuzzytone = [self.__builder.get_object(key), self.__builder.get_object(key+"_False")]
        self.__pinyin_fuzzytone[int(not self.__get_boolean(key, False))].set_active(True)
        self.__pinyin_fuzzytone[0].connect("toggled", self.__toggled_cb, key)

        key = "pinyin-requery"
        self.__pinyin_requery = [self.__builder.get_object(key), self.__builder.get_object(key+"_False")]
        self.__pinyin_requery[int(not self.__get_boolean(key, False))].set_active(True)
        self.__pinyin_requery[0].connect("toggled", self.__toggled_cb, key)


    def __init_advanced(self):
        #def __english_switch_changed_cb(widget, name):
        #    self.__set_boolean(name, self.__englist_switch_list[widget.get_active()])

        def __lookuptable_pagesize_changed_cb(widget, name):
            self.__set_int(name, int(widget.get_value()))

        self.__page_advanced.show()
        
        key = "en-switch-key"
        self.__english_switch = self.__builder.get_object(key)
        #t_list = self.__builder.get_object("liststoreEnSwitchKey")
        #self.__englist_switch_list = map(lambda x: t_list[x][0], range(len(t_list)))
        self.__english_switch.set_active(self.__get_enum(key, 0))	# Control_L
        self.__english_switch.connect("changed", self.__selected_cb, key)

        key = "numeric-key-selection"
        self.__numeric_selection = self.__builder.get_object(key)
        self.__numeric_selection.set_active(self.__get_boolean(key, False))
        self.__numeric_selection.connect("toggled", self.__toggled_cb, key)

        key = "shift-selection"
        self.__shift_selection = self.__builder.get_object(key)
        self.__shift_selection.set_active(self.__get_boolean(key, False))
        self.__shift_selection.connect("toggled", self.__toggled_cb, key)

        key = "semicolon-selection"
        self.__semicolon_selection = self.__builder.get_object(key)
        self.__semicolon_selection.set_active(self.__get_boolean(key, False))
        self.__semicolon_selection.connect("toggled", self.__toggled_cb, key)

        key = "setup-hotkey"
        self.__setup_hotkey = self.__builder.get_object(key)
        self.__setup_hotkey.set_active(self.__get_boolean(key, False))
        self.__setup_hotkey.connect("toggled", self.__toggled_cb, key)

        key = "kill-hotkey"
        self.__kill_hotkey = self.__builder.get_object(key)
        self.__kill_hotkey.set_active(self.__get_boolean(key, False))
        self.__kill_hotkey.connect("toggled", self.__toggled_cb, key)

        key = "equal-key-pagedown"
        self.__equal_pagedown = self.__builder.get_object(key)
        self.__equal_pagedown.set_active(self.__get_boolean(key, False))
        self.__equal_pagedown.connect("toggled", self.__toggled_cb, key)

        key = "arrow-key-pagedown"
        self.__arrow_pagedown = self.__builder.get_object(key)
        self.__arrow_pagedown.set_active(self.__get_boolean(key, False))
        self.__arrow_pagedown.connect("toggled", self.__toggled_cb, key)

        key = "tab-key-pagedown"
        self.__tab_pagedown = self.__builder.get_object(key)
        self.__tab_pagedown.set_active(self.__get_boolean(key, False))
        self.__tab_pagedown.connect("toggled", self.__toggled_cb, key)

        key = "period-key-pagedown"
        self.__period_pagedown = self.__builder.get_object(key)
        self.__period_pagedown.set_active(self.__get_boolean(key, False))
        self.__period_pagedown.connect("toggled", self.__toggled_cb, key)

        key = "lookup-table-orientation"
        self.__lookuptable_orientation = self.__builder.get_object(key)
        self.__lookuptable_orientation.set_active(self.__get_enum(key, 2))	# 系统默认
        self.__lookuptable_orientation.connect("changed", self.__selected_cb, key)

        key = "lookup-table-pagesize"
        self.__lookuptable_pagesize = self.__builder.get_object(key)
        self.__lookuptable_pagesize.set_value(self.__get_int("lookup-table-pagesize", 5))
        self.__lookuptable_pagesize.connect("value-changed", __lookuptable_pagesize_changed_cb, key)

    def __init_custom(self):

        def __default_color_clicked_ed(widget):
            rgba = Gdk.RGBA(0)
            key = "lookup-table-background-color"
            rgba.parse(self.__get_default_string(key))
            self.__custom_bgcolor.set_rgba(rgba)
            self.__colorset_cb(self.__custom_bgcolor, key)

            key = "lookup-table-border-color"
            rgba.parse(self.__get_default_string(key))
            self.__custom_bdcolor.set_rgba(rgba)
            self.__colorset_cb(self.__custom_bdcolor, key)

            key = "lookup-table-font-color"
            rgba.parse(self.__get_default_string(key))
            self.__custom_fontcolor.set_rgba(rgba)
            self.__colorset_cb(self.__custom_fontcolor, key)

            key = "lookup-table-highlight-color"
            rgba.parse(self.__get_default_string(key))
            self.__custom_highcolor.set_rgba(rgba)
            self.__colorset_cb(self.__custom_highcolor, key)

            key = "lookup-table-code-color"
            rgba.parse(self.__get_default_string(key))
            self.__custom_codecolor.set_rgba(rgba)
            self.__colorset_cb(self.__custom_codecolor, key)

            key = "lookup-table-code2-color"
            rgba.parse(self.__get_default_string(key))
            self.__custom_code2color.set_rgba(rgba)
            self.__colorset_cb(self.__custom_code2color, key)

            key = "precommit-font-color"
            rgba.parse(self.__get_default_string(key))
            self.__custom_precommitcolor.set_rgba(rgba)
            self.__colorset_cb(self.__custom_precommitcolor, key)
            #Gdk.RGBA.free(rgba)
            
        self.__page_custom.show()
        rgba = Gdk.RGBA()

        key = "lookup-table-background-color"
        self.__custom_bgcolor = self.__builder.get_object(key)
        rgba.parse(self.__get_string(key, self.__get_default_string(key)))
        Gtk.ColorChooser.set_rgba(self.__custom_bgcolor, rgba)
        self.__custom_bgcolor.connect("color-set", self.__colorset_cb, key)

        key = "lookup-table-border-color"
        self.__custom_bdcolor = self.__builder.get_object(key)
        rgba.parse(self.__get_string(key, self.__get_default_string(key)))
        Gtk.ColorChooser.set_rgba(self.__custom_bdcolor, rgba)
        self.__custom_bdcolor.connect("color-set", self.__colorset_cb, key)

        key = "lookup-table-font-color"
        self.__custom_fontcolor = self.__builder.get_object(key)
        rgba.parse(self.__get_string(key, self.__get_default_string(key)))
        Gtk.ColorChooser.set_rgba(self.__custom_fontcolor, rgba)
        self.__custom_fontcolor.connect("color-set", self.__colorset_cb, key)

        key = "lookup-table-highlight-color"
        self.__custom_highcolor = self.__builder.get_object(key)
        rgba.parse(self.__get_string(key, self.__get_default_string(key)))
        Gtk.ColorChooser.set_rgba(self.__custom_highcolor, rgba)
        self.__custom_highcolor.connect("color-set", self.__colorset_cb, key)

        key = "lookup-table-code-color"
        self.__custom_codecolor = self.__builder.get_object(key)
        rgba.parse(self.__get_string(key, self.__get_default_string(key)))
        Gtk.ColorChooser.set_rgba(self.__custom_codecolor, rgba)
        self.__custom_codecolor.connect("color-set", self.__colorset_cb, key)

        key = "lookup-table-code2-color"
        self.__custom_code2color = self.__builder.get_object(key)
        rgba.parse(self.__get_string(key, self.__get_default_string(key)))
        Gtk.ColorChooser.set_rgba(self.__custom_code2color, rgba)
        self.__custom_code2color.connect("color-set", self.__colorset_cb, key)

        key = "precommit-font-color"
        self.__custom_precommitcolor = self.__builder.get_object(key)
        rgba.parse(self.__get_string(key, self.__get_default_string(key)))
        Gtk.ColorChooser.set_rgba(self.__custom_precommitcolor, rgba)
        self.__custom_precommitcolor.connect("color-set", self.__colorset_cb, key)

        key = "custom-default-color"
        self.__custom_defaultcolor = self.__builder.get_object(key)
        self.__custom_defaultcolor.connect("clicked", __default_color_clicked_ed)

    def __init_dictionary(self):
        def __edit_user_phrases_clicked_cb(widget):
            from xdg import BaseDirectory
            import shutil
            path = os.path.join(wbjj.user, "usrword.txt")
            if not os.path.exists(path):
                shutil.copyfile(wbjj.datapath + "usrword_Templet.txt", path)
            os.system("xdg-open %s" % path)

        def __import_phrases_clicked_cb(widget):
            if not self.__import_file.get_filename():
                return
            if self.__import_tosysdb.get_active():
                self.__process_dbfile = wbjj.db
                # 只在系统码表中查重
                self.__process_sql = 'SELECT * FROM %(table)s WHERE word IN (\'\'%(sub_sql)s);'
            else:
                self.__process_dbfile = wbjj.userdb
                # 在系统码表和用户码表中查重
                self.__process_sql = '''SELECT * FROM (
                         SELECT * FROM main.%(table)s WHERE word IN (\'\'%(sub_sql)s)
                         UNION ALL SELECT * FROM sys_db.%(table)s WHERE word IN (\'\'%(sub_sql)s)
                     )'''
            self.__process_start()
            self.__process_timer = GLib.timeout_add(100, self.__import_words, self.__process_dbfile)

        def __code2_button_clicked_cb(widget):
            if self.__code2_tosysdb.get_active():
                self.__process_group = ['main.wubi3','main.pinyin3','sys_db.wubi3','sys_db.pinyin3']
            else:
                self.__process_group = ['main.wubi3','main.pinyin3']
            if self.__code2_all.get_active():
                self.__process_sql = 'SELECT id,word FROM %(table)s WHERE id > %(id)s ORDER BY id LIMIT 50 OFFSET 0;'
            else:
                self.__process_sql = 'SELECT id,word FROM %(table)s WHERE id > %(id)s AND code2 IS NULL ORDER BY id LIMIT 50 OFFSET 0;'
            self.__process_dbfile = wbjj.userdb
            self.__process_start()
            self.__process_timer = GLib.timeout_add(100, self.__update_code2)

        def __user_phrases_toggled_cb(widget, key):
            self.__toggled_cb(widget, key)
            self.__edit_user_phrases.set_sensitive(self.__user_phrases.get_active())

        self.__page_dictionary.show()
    
        key = "user-defined-phrases"
        self.__user_phrases = self.__builder.get_object(key)
        self.__user_phrases.set_active(self.__get_boolean(key, True))
        self.__user_phrases.connect("toggled", __user_phrases_toggled_cb, key)

        key = "EditUserDefinedPhrases"
        self.__edit_user_phrases = self.__builder.get_object(key)
        self.__edit_user_phrases.connect("clicked", __edit_user_phrases_clicked_cb)
        self.__edit_user_phrases.set_sensitive(self.__user_phrases.get_active())

        key = "ImportPhrasesButton"
        self.__import_phrases = self.__builder.get_object(key)
        self.__import_phrases.connect("clicked", __import_phrases_clicked_cb)
        self.__import_file = self.__builder.get_object("ImportPhrasesFile")
        self.__import_check = self.__builder.get_object("ImportCheck")
        self.__import_tosysdb = self.__builder.get_object("ImportToSysdb")
        if not os.access(wbjj.db, os.W_OK) or not os.access(wbjj.dbpath, os.W_OK):
            self.__import_tosysdb.set_sensitive(False)
        self.__tools_phrases = self.__builder.get_object("ToolsProgress")
        self.__tools_phrases.set_visible(False)
        self.__tools_separator = self.__builder.get_object("ToolsHSeparator")
        self.__tools_separator.set_visible(True)

        key = "Code2Button"
        self.__code2_button = self.__builder.get_object(key)
        self.__code2_button.connect("clicked", __code2_button_clicked_cb)
        self.__code2_all = self.__builder.get_object("Code2All")
        self.__code2_tosysdb = self.__builder.get_object("Code2ToSysdb")
        if not os.access(wbjj.db, os.W_OK) or not os.access(wbjj.dbpath, os.W_OK):
            self.__code2_tosysdb.set_sensitive(False)

    def __init_about(self):
        self.__page_about.show()
        self.__about_version = self.__builder.get_object("NameVersion")
        self.__about_version.set_markup(u"<big><b>五笔加加Plus For IBus<br>%s</b></big>" % wbjj.version + '.' + wbjj.date)
        self.__about_image = self.__builder.get_object("imageAbout")
        self.__about_image.set_from_file(wbjj.icon)

    def __import_words(self, dbfile):
        '''导入码表'''
        if self.__process_step == -2:
            # 处理完成,恢复UI
            GLib.source_remove(self.__process_timer)
            self.__process_stop()
        elif self.__process_step == -1:
            # 处理准完成,更新UI
            self.__tools_phrases.set_fraction(1)
            self.__tools_phrases.set_text('完成, 导入 %(successed)d / %(count)d' % {'successed':self.__process_successed, 'count':self.__process_count})
            self.__process_step = -2
            self.__process_timer = GLib.timeout_add(5000, self.__import_words, dbfile)
        elif self.__process_count == -1:
            # 处理中
            self.__import_lists = wbjj.get_txtfile_words(self.__import_file.get_filename(), 0, 0)   # 返回[五笔RecordTupleList,拼音RecordTupleList,[]]
            self.__process_count = len(self.__import_lists[0]) + len(self.__import_lists[1])
            if self.__process_count <= 0:
                self.__tools_phrases.set_fraction(1)
                self.__tools_phrases.set_text('失败, 数据无效')
                self.__process_step = -2
                self.__process_timer = GLib.timeout_add(5000, self.__import_words, dbfile)
            else:
                self.__process_timer = GLib.timeout_add(50, self.__import_words, dbfile)
        else:
            if self.__process_step < len(self.__import_lists[0]):
                _table = 'wubi3'
                i = 0
                l = len(self.__import_lists[0])
                j = self.__process_step
                if j + 50 <= l:
                    k = j + 50
                else:
                    k = l
            else:
                _table = 'pinyin3'
                i = 1
                l = len(self.__import_lists[1])
                j = self.__process_step - len(self.__import_lists[0])
                if j + 50 <= l:
                    k = j + 50
                else:
                    k = l
            # 码表分组查重
            if self.__import_check.get_active():
                _sub_sql = ''.join(map(lambda x: ',\'%(word)s\'' % {'word':x[4].replace('\'','\'\'')}, self.__import_lists[i][j:k]))
                _RecordTupleList = self.__process_db.execute(self.__process_sql % {'table':_table, 'sub_sql':_sub_sql}).fetchall()
                _CodeWordTupleList = list(map(lambda x: (x[wbjj.idx_code], x[wbjj.idx_word]), _RecordTupleList))
            else:
                _CodeWordTupleList = []
            for _RecordTuple in self.__import_lists[i][j:k]:      # 分组处理,以便于UI更新状态
                if (_RecordTuple[wbjj.idx_code], _RecordTuple[wbjj.idx_word]) not in _CodeWordTupleList:
                    if self.__insert_phrase(_RecordTuple, _table, self.__process_db):
                        self.__process_successed += 1
            self.__process_step = k
            p_n = self.__process_step / self.__process_count
            self.__tools_phrases.set_fraction(p_n)
            self.__tools_phrases.set_text(str(int(p_n * 100)) + ' %')
            self.__process_timer = GLib.timeout_add(50, self.__import_words, dbfile)
            if self.__process_step >= self.__process_count:
                self.__process_step = -1

    def __insert_phrase(self, RecordTuple, table, db):
        '''添加到指定码表'''
        _RecordList = list(RecordTuple)
        if type(_RecordList[wbjj.idx_word]) != type(u''):
            _RecordList[wbjj.idx_word] = _RecordList[wbjj.idx_word].decode('utf8')
        _RecordList[wbjj.idx_cate] = wbjj.get_category(RecordTuple[wbjj.idx_word])
        if _RecordList[wbjj.idx_clen] != len(_RecordList[wbjj.idx_code]) or len(_RecordList[wbjj.idx_code]) <= 0:
            return False
        try:
            sqlstr = 'INSERT INTO main.%(table)s (' + ', '.join(wbjj.dbfields) + ') VALUES (' + ', '.join(['?'] * len(wbjj.dbfields)) + ');'
            db.execute(sqlstr % {'table':table}, tuple(_RecordList))
            return True
        except Exception:
            import traceback
            traceback.print_exc()
            return False

    def __update_code2(self):
        '''更新反查编码(code2)'''
        if self.__process_step == -2:
            # 处理完成,恢复UI
            GLib.source_remove(self.__process_timer)
            self.__process_stop()
        elif self.__process_step == -1 or self.__process_unit >= len(self.__process_group):
            # 处理准完成,更新UI
            self.__tools_phrases.set_fraction(1)
            self.__tools_phrases.set_text('完成, 更新 %(successed)d / %(count)d' % {'successed':self.__process_successed, 'count':self.__process_count})
            self.__process_step = -2
            self.__process_timer = GLib.timeout_add(5000, self.__update_code2)
        elif self.__process_count == -1:
            # 处理开始,初始化数据
            for _table in self.__process_group:
                if self.__code2_all.get_active():
                    # 统计完整重建的行数
                    c = self.__process_db.execute('SELECT COUNT(*) FROM %(table)s;' % {'table':_table}).fetchall()
                else:
                    # 仅统计code2为NULL的行数(不包括已查找但是无结果的空字符串记录)
                    c = self.__process_db.execute('SELECT COUNT(*) FROM %(table)s WHERE code2 IS NULL;' % {'table':_table}).fetchall()
                if c:
                    self.__process_count += c[0][0]
            if self.__process_count <= 0:
                self.__tools_phrases.set_fraction(1)
                self.__tools_phrases.set_text('失败, 码表错误 或 没有需要更新的记录')
                self.__process_step = -2
                self.__process_timer = GLib.timeout_add(5000, self.__update_code2)
            else:
                self.__process_timer = GLib.timeout_add(50, self.__update_code2)
        else:
            # 处理中
            _table = self.__process_group[self.__process_unit]
            _IdWordTupleList = self.__process_db.execute(self.__process_sql % {'table':_table, 'id':self.__process_lastid}).fetchall()
            _id = 0
            _code = 0
            _word = 1
            if _IdWordTupleList:
                if _table.find('wubi3') >= 0:
                    _inverse_table = 'pinyin3'
                else:
                    _inverse_table = 'wubi3'
                _sub_sql = ''.join(map(lambda x: ',\'%(word)s\'' % {'word':x[_word].replace('\'','\'\'')}, _IdWordTupleList))
                _sql = '''SELECT code, word FROM (
                    SELECT * FROM main.%(inverse_table)s WHERE word IN (\'\'%(sub_sql)s)
                    UNION ALL SELECT * FROM sys_db.%(inverse_table)s WHERE word IN (\'\'%(sub_sql)s)
                )''' % {'inverse_table':_inverse_table, 'sub_sql':_sub_sql}
                _CodeWordTupleList = list(set(self.__process_db.execute(_sql).fetchall()))      # 通过集合(set)转换去重
                for _IdWordTuple in _IdWordTupleList:
                    _list = list(set(map(lambda x: x[0], filter(lambda y: y[1]==_IdWordTuple[_word], _CodeWordTupleList))))
                    _list.sort()
                    code2 = ','.join(_list)
                    if code2 != '':
                        self.__process_db.execute('UPDATE %(table)s SET code2 = \'%(code2)s\' WHERE id = %(id)d' % {'table':_table, 'id':_IdWordTuple[_id], 'code2':code2})
                        self.__process_successed += 1
                self.__process_lastid = _IdWordTupleList[-1][0]
            else:
                self.__process_unit += 1
                self.__process_lastid = 0
            self.__process_step += len(_IdWordTupleList)
            p_n = min(self.__process_step / self.__process_count, 1.0)
            self.__tools_phrases.set_fraction(p_n)
            self.__tools_phrases.set_text(str(int(p_n*100)) + ' %')
            self.__process_timer = GLib.timeout_add(50, self.__update_code2)
            if self.__process_step >= self.__process_count:
                self.__process_step = -1


    def __process_start(self):
        self.__import_file.set_sensitive(False)
        self.__import_phrases.set_sensitive(False)
        self.__import_check.set_sensitive(False)
        self.__import_tosysdb.set_sensitive(False)
        self.__code2_button.set_sensitive(False)
        self.__code2_all.set_sensitive(False)
        self.__code2_tosysdb.set_sensitive(False)
        self.__tools_phrases.set_fraction(0)
        self.__tools_phrases.set_text('0 %')
        self.__tools_phrases.set_visible(True)
        self.__tools_separator.set_visible(False)
        self.__process_db = sqlite3.connect(self.__process_dbfile)
        self.__process_db.execute('PRAGMA page_size = 8192;')
        self.__process_db.execute('PRAGMA cache_size = 20000;')  # 加大缓存以提速
        self.__process_db.execute('PRAGMA temp_store = MEMORY;')
        self.__process_db.execute('PRAGMA synchronous = OFF;')
        self.__process_db.execute('ATTACH DATABASE "%s" AS sys_db;' % wbjj.db)
        self.__process_count = -1
        self.__process_step = 0
        self.__process_successed = 0
        self.__process_unit = 0
        self.__process_lastid = 0

    def __process_stop(self):
        if self.__process_db != None:
            self.__process_db.commit()
        self.__import_file.set_sensitive(True)
        self.__import_phrases.set_sensitive(True)
        self.__import_check.set_sensitive(True)
        self.__code2_button.set_sensitive(True)
        self.__code2_all.set_sensitive(True)
        self.__tools_phrases.set_visible(False)
        self.__tools_separator.set_visible(True)
        if os.access(wbjj.db, os.W_OK) and os.access(wbjj.dbpath, os.W_OK):
            self.__import_tosysdb.set_sensitive(True)
            self.__code2_tosysdb.set_sensitive(True)

    def __changed_cb(self, widget, name):
        self.__set_value(name, widget.get_active())

    def __toggled_cb(self, widget, name):
        self.__set_boolean(name, widget.get_active())

    def __selected_cb(self, widget, name):
        self.__set_enum(name, int(widget.get_active()))

    def __colorset_cb(self, widget, name):
        def _rgbstr2html(rgbstr):
            if rgbstr[0:4] == 'rgb(' and rgbstr[-1:] == ')' and len(rgbstr) - len(rgbstr.replace(',','')) == 2:
                rgb = rgbstr[4:-1].split(',')
                return '#' + (str('0' + hex(int(rgb[0]))[2:])[-2:] + str('0' + hex(int(rgb[1]))[2:])[-2:] + str('0' + hex(int(rgb[2]))[2:])[-2:]).upper()
        self.__set_string(name, _rgbstr2html(Gdk.RGBA.to_string(Gtk.ColorChooser.get_rgba(widget))))

    def __get_int(self, name, defval):
        try:
            return self.__cfg.get_int(name)
        except:
            return defval

    def __get_enum(self, name, defval):
        try:
            return self.__cfg.get_enum(name)
        except:
            return defval

    def __get_boolean(self, name, defval):
        try:
            return self.__cfg.get_boolean(name)
        except:
            return defval

    def __get_string(self, name, defval):
        try:
            return self.__cfg.get_string(name)
        except:
            return defval

    def __set_int(self, name, val):
        self.__cfg.set_int(name, val)

    def __set_enum(self, name, val):
        self.__cfg.set_enum(name, val)

    def __set_boolean(self, name, val):
        self.__cfg.set_boolean(name, val)

    def __set_string(self, name, val):
        self.__cfg.set_string(name, val)
        
    def __get_default_string(self, name):
        return self.__cfg.get_default_value(name).get_string()

    def run(self):
        return self.__dialog.run()


def main():
    try:
        PreferencesDialog().run()
    except:
        import traceback
        traceback.print_exc ()

if __name__ == "__main__":
    main()

