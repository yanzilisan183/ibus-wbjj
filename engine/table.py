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

__all__ = ("TabEngine")

import os
import re
import sys
import string
from gi import require_version
require_version('IBus', '1.0')
from gi.repository import IBus
require_version('Gio', '2.0')
from gi.repository import Gio
require_version('GLib', '2.0')
from gi.repository import GLib
from gi.repository import GObject
import tabdict
import wbjj

_  = lambda a: IBus.Text.new_from_string(a)
regLikeNum = r'^(\-|\-?[0-9]+[0-9\.]*|[0-9]{4}[0-9\.\-\/]*)$'   # 中文数字/日期输入过程,如(12., -, -1., 2020/, 2021-等不完整但尚符合中文数字日期转换的)

def ascii_ispunct(character):
    return bool(character in '''!"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~''')


def ascii_isdigit(keycode):
    return bool(chr(keycode) in '0123456789')


class KeyEvent:
    '''  '''
    def __init__(self, keyval, is_press, state):
        self.code = keyval
        self.mask = state
        if not is_press:
            self.mask |= IBus.ModifierType.RELEASE_MASK

    def __str__(self):
        return "%s 0x%08x" % (IBus.keyval_name(self.code), self.mask)


class IMEConfig():
    '''保存配置的类'''
    def __init__(self, bus, db):
        db._cfg = self                         # 把自己的引用写入db对象,以便db对象内部可以使用
        self.__db = db
        self.__gsettings = Gio.Settings(schema=wbjj.requestpath.lower(), path='/' + wbjj.requestpath.lower().replace('.','/') + '/')
        self.__gsettings.connect('changed', self.__config_changed_ed)
        self._ibus_lookup_table = None         # IBus.LookupTable对象,由外部设置
        self.refresh()

    def refresh(self):
        def colorstr2int(colorstr):
            if colorstr[0:4] == 'rgb(' and colorstr[-1:] == ')' and len(colorstr) - len(colorstr.replace(',','')) == 2:
                # rgb(r,g,b) 格式计算
                rgb = colorstr[4:-1].split(',')
                r = int(rgb[0])
                g = int(rgb[1])
                b = int(rgb[2])
            else:
                colorstr = colorstr.replace('0x','#', 1)    # 防错整理
                if colorstr[0:7] == colorstr[:]:            # 本身就是 #AABBCC 格式,直接将十六进制转换为十进制返回
                   return int(colorstr[1:], 16)
                # #AAAABBBBCCCC 格式计算
                r = int(int(colorstr[1:5], 16) / 256)
                g = int(int(colorstr[5:9], 16) / 256)
                b = int(int(colorstr[9:13], 16) / 256)
            return (r<<16) + (g<<8) + b
        self._active = True     # 活动状态(不响应配置变更)
        # LookupTable属性(_lt)
        self._ltOrientation = self.__gsettings.get_enum("lookup-table-orientation")          # 备选列表方向(0:水平,1:竖直,2:系统默认)
        self._ltPageSize = self.__gsettings.get_int("lookup-table-pagesize")                 # 每页侯选字数量
        if not self._ltPageSize in range(3,11):                                              # 如果不在允许范围(3-10个),则重设为最接近的
            self._ltPageSize = max(min(self._ltPageSize, 10), 3)
            self.__gsettings.set_int("lookup-table-pagesize", self._ltPageSize)
        self._ltBgColor = colorstr2int(self.__gsettings.get_string("lookup-table-background-color"))  # 侯选框背景色,   "#E6F0FF"
        self._ltBdColor = colorstr2int(self.__gsettings.get_string("lookup-table-border-color"))      # 侯选框边框色,   "#78A0FF"
        self._ltFontColor = colorstr2int(self.__gsettings.get_string("lookup-table-font-color"))      # 侯选字颜色,     "#000000"
        self._ltHighColor = colorstr2int(self.__gsettings.get_string("lookup-table-highlight-color")) # 侯选字高亮色,   "#F07746"
        self._ltCodeColor = colorstr2int(self.__gsettings.get_string("lookup-table-code-color"))      # 提示编码颜色,   "#1973A2"
        self._ltCode2Color = colorstr2int(self.__gsettings.get_string("lookup-table-code2-color"))    # 反查编码颜色,   "#990000"
        # Preedit, Precommit, Aux属性(_pe, _pc, _au)
        self._pcFontColor = colorstr2int(self.__gsettings.get_string("precommit-font-color"))         # 待提交文字颜色, "#EEDD00"
        # 输入法属性(_im)
        self._imMaxLength = 64                                                               # 最大编码长度
        # 状态(_st)
        self._stInitEnglish = self.__gsettings.get_boolean("init-english")                   # 初始为英文模式, False
        self._stChineseMode = self.__gsettings.get_enum("chinese-mode")                      # 中文字符集模式(0:简体, 1:繁体, 2:简体优先的大字符集, 3:繁体优先的大字符集, 4:大字符集)
        self._stFullLetter = self.__gsettings.get_boolean("full-width-letter")               # 是否全角, False
        self._stFullPunct = self.__gsettings.get_boolean("full-width-punct")                 # 是否中文标点, False
        self._stOneChar = self.__gsettings.get_boolean("one-char")                           # 是否单字模式, False
        self._stAutoCommit = self.__gsettings.get_boolean("auto-commit")                     # 是否自动提交, True
        self._stChineseDigital = self.__gsettings.get_boolean("chinese-digital")             # 是否使用中文数字, False
        self._stDynamicAdjust = self.__gsettings.get_boolean("dynamic-adjust")               # 是否动态调频, True
        self._stpyRequery = self.__gsettings.get_boolean("pinyin-requery")                   # 拼音反查五笔编码, True
        self._stpyFuzzyTone = self.__gsettings.get_boolean("pinyin-fuzzy-tone")              # 拼音模糊音(zh<->z,ch<->c,sh<->s), False
        self._stUserDefinedPhrases = self.__gsettings.get_boolean("user-defined-phrases")    # 用户自定义码表, False
        if self._stUserDefinedPhrases:
            self.__db.load_user_words(wbjj.user + 'usrword.txt')                             # 导入用户码表
        # 快捷键设置(_hk)
        self._hkEnSwitchKeyStr = self.__gsettings.get_string("en-switch-key")                # 中英文切换键(文本), "左Ctrl键"
        self._hkEnSwitchKey = wbjj.hkEnSwitchKeyEnumRev[self._hkEnSwitchKeyStr]              # 中英文切换键(键值列表)
        self._hkShiftSelection = self.__gsettings.get_boolean("shift-selection")             # 是否启用Shift选择重码, True
        self._hkSemicolonSelection = self.__gsettings.get_boolean("semicolon-selection")     # 是否启用<;><'>选择重码, False
        self._hkNumericKeySelection = self.__gsettings.get_boolean("numeric-key-selection")  # 是否启用数字键选择重码, True
        if not self._hkNumericKeySelection:                                                  # 禁用数字键选择重码时,备选只能是3
            self._ltPageSize = 3
            if (not self._hkShiftSelection) and (not self._hkSemicolonSelection):
                self._hkShiftSelection = True                                                # 如果Shift和<;><'>均禁用,则开启Shift
        self._hkSetupHotKey = self.__gsettings.get_boolean("setup-hotkey")                   # 首选项/帮助快捷键, True
        self._hkKillHotKey = self.__gsettings.get_boolean("kill-hotkey")                     # IBus重启快捷键, True
        self._hkPgDnList = [IBus.Page_Down, IBus.KP_Page_Down]                               # 上翻页快捷键表
        self._hkPgUpList = [IBus.Page_Up, IBus.KP_Page_Up]                                   # 下翻页快捷键表
        self._hkPeriodPgDn = self.__gsettings.get_boolean("period-key-pagedown")             # <,><.>翻页, False
        if self._hkPeriodPgDn:
            self._hkPgDnList.append(IBus.period)
            self._hkPgUpList.append(IBus.comma)
        self._hkEqualPgDn = self.__gsettings.get_boolean("equal-key-pagedown")               # <-><=>翻页, True
        if self._hkEqualPgDn:
            self._hkPgDnList.append(IBus.equal)
            self._hkPgUpList.append(IBus.minus)
        self._hkTabPgDn = self.__gsettings.get_boolean("tab-key-pagedown")                   # <Tab>翻页, True
        if self._hkTabPgDn:
            self._hkPgDnList.append(IBus.Tab)
            self._hkPgUpList.append(IBus.ISO_Left_Tab)
        self._hkArrowPgDn = self.__gsettings.get_boolean("arrow-key-pagedown")               # 方向键翻页, True

        if self._ibus_lookup_table != None:
            if self._ltOrientation in range(0, 1):
                self._ibus_lookup_table.set_orientation(self._ltOrientation)
            self._ibus_lookup_table.set_page_size(self._ltPageSize)
        if self._hkArrowPgDn:
            if self._ltOrientation in range(0, 1):
                runtime_orientation = self._ltOrientation
            elif self._ibus_lookup_table != None:
                runtime_orientation = self._ibus_lookup_table.get_orientation()              # 取IBus.LookupTable当前排列方式值
            else:
                runtime_orientation = 0
            if runtime_orientation == 0:
                self._hkPgDnList.append(IBus.Down)
                self._hkPgDnList.append(IBus.KP_Down)
                self._hkPgUpList.append(IBus.Up)
                self._hkPgUpList.append(IBus.KP_Up)
            else:
                self._hkPgDnList.append(IBus.Right)
                self._hkPgDnList.append(IBus.KP_Right)
                self._hkPgUpList.append(IBus.Left)
                self._hkPgUpList.append(IBus.KP_Left)
        self._active = False                                                                 # 非活动状态(响应配置变更)

    def __config_changed_ed(self, settings, name):
        if self._active:
            return
        self.refresh()

#    def __config_ibus_changed_ed(self, settings, name):
#        if name != 'lookup-table-orientation' or self._active:
#            return
#        self.refresh()

    def _set_stOneChar(self, value):
        self._stOneChar = bool(value)
        self.__gsettings.set_boolean("one-char", self._stOneChar)

    def _set_stChineseMode(self, value):
        if self._stChineseMode == -1:
            return
        if int(value) in range(0, 5):
            self._stChineseMode = int(value)
            self.__gsettings.set_enum("chinese-mode", self._stChineseMode)

    def _set_stFullLetter(self, value):
        self._stFullLetter = bool(value)
        self.__gsettings.set_boolean("full-width-letter", self._stFullLetter)

    def _set_stFullPunct(self, value):
        self._stFullPunct = bool(value)
        self.__gsettings.set_boolean("full-width-punct", self._stFullPunct)

    def _set_stAutoCommit(self, value):
        self._stAutoCommit = bool(value)
        self.__gsettings.set_boolean("auto-commit", self._stAutoCommit)

    def _set_stChineseDigital(self, value):
        self._stChineseDigital = bool(value)
        self.__gsettings.set_boolean("chinese-digital", self._stChineseDigital)


class Editor(object):
    '''保留用户输入字符和预编辑字符串,其中 self._ibus_lookup_table 为IBus原生输入框侯选字容器对象'''
    def __init__(self, cfg, database):
        self.db = database
        self._cfg = cfg
        self._ibus_lookup_table = IBus.LookupTable(page_size=self._cfg._ltPageSize, cursor_pos=0, cursor_visible=True, round=False)
        if self._cfg._ltOrientation != 2:
            self._ibus_lookup_table.set_orientation(self._cfg._ltOrientation)
        self._ibus_lookup_table.set_page_size(self._cfg._ltPageSize)
        self._cfg._ibus_lookup_table = self._ibus_lookup_table      # 供IMEConfig对象内部反向调用

        self._chars = [[],[],[]]      # 保存五笔模式下的用户输入 hold user input in table mode (有效字符集,无效字符集,prevalid)
        self._wb_char_list = []       # 保存五笔模式下的输入验证,结构为['a','b','c','d','e','f',...] hold total input for table mode for input check
        self._un_char_list = []       # 保存用户输入但不包括手选字母,按字分组,结构为[['a','b','c','d'],['e','f','g','h'],...] hold user input but not manual comitted chars
        self._query_code_str = u''    # 保存键入的编码字母(code),用于查询数据库code字段
        self._precommit_list = []     # 保存预编辑字符(在preedit中但尚未提交的字符,通常由于超过编码限长且不自动上屏时自动提交到preedit区中的,比如输入5个n)
        self._cursor = [0,0]          # 预编辑短语插入点 the caret position in preedit phrases 
        self._candidates = []         # 保存备选内容 [('${code}', '${word}', ${category}, ${code2}, ${freq}, ${user_freq}), ('wh', '个', 3, 7252, 16),...]
        self._last_candidates = []    # 最后输入的字词(供z键使用,格式同self._candidates,但最后输入的拼音candidate会转换为五笔candidate)
        self._py_mode = False         # 是否是拼音模式
        self._create_mode = False     # 是否是造词模式
        self._caret = 0               # 备选列表插入点 caret position in lookup_table
        self._word_history = [[u'','','']]*wbjj.historywords  # 输入历史(单字,结构:['单字','五笔编码字符串','拼音编码字符串'])

    def is_onlyone_candidate(self):
        '''备选列表是仅有唯一的选择'''
        return len(self._candidates) == 1

    def is_empty(self):
        return len(self._wb_char_list) == 0

    def switch_py_wb(self):
        '''切换拼音/五笔模式'''
        self._py_mode = not self._py_mode
        return True

    def clear(self):
        '''删除保留的数据'''
        if self._create_mode:
            self._create_mode = False
        self.over_input()
        self._wb_char_list = []
        self._precommit_list = []
        self._cursor = [0,0]
        self._py_mode = False
        self.update_candidates
    
    def clear_input(self):
        '''Remove input characters held for Table mode'''
        self._chars = [[],[],[]]
        self._query_code_str = u''
        self._ibus_lookup_table.clean()
        self._ibus_lookup_table.show_cursor(False)
        self._candidates = []
    
    def over_input(self):
        '''Remove input characters held for Table mode'''
        self.clear_input()
        self._un_char_list = []
    
    def add_input(self, char):
        '''将按键字母追加到输入栏 add input character'''
        print("DEBUG: in add_input() ==========================================================")
        if len(self._wb_char_list) == self._cfg._imMaxLength:
            return True
        if self._cursor[1]:
            self.split_phrase()
        # is_numeric = self._cfg._stChineseDigital and (''.join(self._chars[0]).replace('.','').replace('-','').replace('/','').isdigit() or ''.join(self._chars[0]) == '-' or (len(self._chars[0]) < 1) and char in wbjj.numValidChar)
        is_numeric = self._cfg._stChineseDigital and re.match(regLikeNum, ''.join(self._chars[0]) + char)
        if (not is_numeric) and (len(self._chars[0]) >= wbjj.wbMaxLength and not self._py_mode and not self._cfg._stFullLetter) or (len(self._chars[0]) == wbjj.pyMaxLength and self._py_mode):
            # 达到最大编码长度,自动输出到预编辑区(条件:不是数字,不是全角状态,不是拼音)
            self.auto_commit_to_preedit()
            res = self.add_input(char)
            return res
        elif self._chars[1]:
            # 之前输入包含无效字符,后续字符继续追加到无效字符self._chars[1]中
            self._chars[1].append(char)
        #elif (not self._py_mode and (char in wbjj.wbValidChar or char == u"z")) or (self._py_mode and (char in wbjj.pyValidChar)) or (is_numeric and char in wbjj.numValidChar):
        elif (not self._py_mode and (char in wbjj.wbValidChar or char == u"z")) or (self._py_mode and (char in wbjj.pyValidChar)) or is_numeric:
            # 五笔编码中出现z 或 拼音 或 self._chars[0]和当前字符都是数字
            self._query_code_str += char
            self._chars[0].append(char)
        else:
            self._chars[1].append(char)
        self._wb_char_list.append(char)
        res = self.update_candidates()
        return res

    def pop_input(self):
        '''remove and display last input char held'''
        _c =''
        if self._chars[1]:
            _c = self._chars[1].pop()
        elif self._chars[0]:
            _c = self._chars[0].pop()
            self._query_code_str = self._query_code_str[:-1]
            if (not self._chars[0]) and self._un_char_list:
                self._chars[0] = self._un_char_list.pop()
                self._chars[1] = self._chars[1][:-1]
                self._query_code_str = ''.join(self._chars[0])
                self._precommit_list.pop(self._cursor[0] - 1)
                self._cursor[0] -= 1
        self._wb_char_list.pop()
        self.update_candidates()
        return _c

    def split_phrase(self):
        '''Splite current phrase into two phrase'''
        _head = u''
        _end = u''
        try:
            _head = self._precommit_list[self._cursor[0]][:self._cursor[1]]
            _end = self._precommit_list[self._cursor[0]][self._cursor[1]:]
            self._precommit_list.pop(self._cursor[0])
            self._precommit_list.insert(self._cursor[0],_head)
            self._precommit_list.insert(self._cursor[0]+1,_end)
            self._cursor[0] +=1
            self._cursor[1] = 0
        except:
            pass
    
    def remove_before_string(self):
        '''Remove string before cursor'''
        if self._cursor[1] != 0:
            self.split_phrase()
        if self._cursor[0] > 0:
            self._precommit_list.pop(self._cursor[0]-1)
            self._cursor[0] -= 1
        else:
            pass
        # if we remove all characters in preedit string, we need to clear the self._wb_char_list
        if self._cursor == [0,0]:
            self._wb_char_list =[]
    
    def remove_after_string(self):
        '''Remove string after cursor'''
        if self._cursor[1] != 0:
            self.split_phrase()
        if self._cursor[0] >= len(self._precommit_list):
            pass
        else:
            self._precommit_list.pop(self._cursor[0])
    
    def remove_before_char(self):
        '''Remove character before cursor'''
        if self._cursor[1] > 0:
            _str = self._precommit_list[self._cursor[0]]
            self._precommit_list[self._cursor[0]] = _str[:self._cursor[1]-1] + _str[self._cursor[1]:]
            self._cursor[1] -= 1
        else:
            if self._cursor[0] == 0:
                pass
            else:
                if len(self._precommit_list[self._cursor[0] - 1]) == 1:
                    self.remove_before_string()
                else:
                    self._precommit_list[self._cursor[0] - 1] = self._precommit_list[self._cursor[0] - 1][:-1]
        # if we remove all characters in preedit string, we need to clear the self._wb_char_list
        if self._cursor == [0,0]:
            self._wb_char_list =[]

    def remove_after_char(self):
        '''Remove character after cursor'''
        if self._cursor[1] == 0:
            if self._cursor[0] == len(self._precommit_list):
                pass
            else:
                if len(self._precommit_list[self._cursor[0]]) == 1:
                    self.remove_after_string()
                else:
                    self._precommit_list[self._cursor[0]] = self._precommit_list[self._cursor[0]][1:]
        else:
            if (self._cursor[1] + 1) == len(self._precommit_list[self._cursor[0]]):
                self.split_phrase()
                self.remove_after_string()
            else:
                string = self._precommit_list[self._cursor[0]]
                self._precommit_list[self._cursor[0]] = string[:self._cursor[1]] + string[self._cursor[1] + 1:]

#    def add_caret(self, addstr):
#        '''add length to caret position'''
#        self._caret += len(addstr)

#    def get_caret(self):
#        '''Get caret position in preedit strings'''
#        self._caret = 0
#        if self._cursor[0] and self._precommit_list:
#            map(self.add_caret,self._precommit_list[:self._cursor[0]])
#        self._caret += self._cursor[1]
#        if self._candidates:
#            _candidate =self._candidates[int(self._ibus_lookup_table.get_cursor_pos())][wbjj.candidx_word] 
#        else:
#            _candidate = u''.join(map(str,self.get_input_chars()))
#        self._caret += len(_candidate) 
#        return self._caret
    
    def append_candidate_to_lookup_table(self, candidate):
        '''追加侯选字词到IBus.LookupTable中(常规)'''
        if not candidate or not candidate[wbjj.candidx_code] or not candidate[wbjj.candidx_word]:
            return
        _code2 = ''
        attrs = IBus.AttrList()
        _word = candidate[wbjj.candidx_word]
        if len(_word) > 5:
            _word = _word[:5] + u'…'
        _wlen = len(_word)
        # 侯选字上色
        attrs.append(IBus.attr_foreground_new(self._cfg._ltFontColor, 0, _wlen))
        # 编码截短(去掉已在aux中的编码)
        _aux_string = self.get_aux_strings()
        # 编码及反查编码上色(准备)
        if self._py_mode:
            # 提示编码上色
            _color = self._cfg._ltCodeColor
            _code = candidate[wbjj.candidx_code].split(' ',2)[0]
            _aux_string = _aux_string[1:]       # 拼音去掉引导符z
            _code = _code.replace('!','↑1').replace('@','↑2').replace('#','↑3').replace('$','↑4').replace('%','↑5')
            _aux_string = _aux_string.replace('1','↑1').replace('2','↑2').replace('3','↑3').replace('4','↑4').replace('5','↑5')
            if self._cfg._stpyRequery and candidate[wbjj.candidx_code].find(' ') >= 0:
                # 返查编码上色(E7700C3)
                _color2 = self._cfg._ltCode2Color
                _code2 = candidate[wbjj.candidx_code].split(' ',2)[1]
        else:
            # 提示编码上色
            _color = self._cfg._ltCodeColor
            _code = candidate[wbjj.candidx_code].split(',')[0]
            if len(_code) > 4:
                _code = _code[:4]
        # 提示编码截掉已输入的部分
        _alen = len(_aux_string)
        if len(_code) >= _alen:
            if _code[0:_alen] == _aux_string:
                _code = _code[_alen:]
        elif len(_code) <= _alen and _aux_string.find(_code) == 0:
            _code = ''
        # 编码上色
        attrs.append(IBus.attr_foreground_new(_color, _wlen, _wlen + len(_code)))
        # 反查编码上色
        if len(_code2) > 0:
            _c2 = _wlen + len(_code) + 1
            attrs.append(IBus.attr_foreground_new(_color2, _c2, _c2 + len(_code2)))
            _code = _code + ' ' + _code2
        # 填充字符串
        self._ibus_lookup_table.append_candidate(IBus.Text(_word + _code, attrs))
        self._ibus_lookup_table.show_cursor(False)
        self._ibus_lookup_table.set_cursor_visible(True)    # 设置焦点

    def append_candidate_to_lookup_table_special(self, candidate):
        '''追加侯选字词到IBus.LookupTable中(非常规)'''
        if not candidate or not candidate[wbjj.candidx_word]:
            return
        attrs = IBus.AttrList()
        _word = candidate[wbjj.candidx_word]
        if len(_word) > 12:
            _word = _word[:12] + u'…'    # 这里的长度限制比append_candidate_to_lookup_table大一些
        _wlen = len(_word)
        # 侯选字上色
        attrs.append(IBus.attr_foreground_new(self._cfg._ltFontColor, 0, _wlen))
        # 编码上色(上返查色)
        _code = candidate[wbjj.candidx_code]    # 拼音(可能多个)已标记音调,无需split拆分处理
        attrs.append(IBus.attr_foreground_new(self._cfg._ltCode2Color, _wlen, _wlen + len(_code)))
        self._ibus_lookup_table.append_candidate(IBus.Text(_word + _code, attrs))
        self._ibus_lookup_table.show_cursor(False)
        self._ibus_lookup_table.set_cursor_visible(True)    # 设置焦点

    def pinyin_tone(self, pinyin):
        '''拼音标声调'''
        tstr = pinyin
        if tstr.find('!') >= 0:
            tone = [u'aoeuvi',u'āōēūǖī']
            tstr = tstr.replace('!','')
        elif tstr.find('@') >= 0:
            tone = [u'aoeuvimn',u'áóéúǘíń']
            tstr = tstr.replace('@','')
        elif tstr.find('#') >= 0:
            tone = [u'aoeuvin',u'ǎǒěǔǚǐň']
            tstr = tstr.replace('#','')
        elif tstr.find('$') >= 0:
            tone = [u'aoeuvin',u'àòèùǜìǹ']
            tstr = tstr.replace('$','')
        else:
            tone = [u'v',u'ü']
            tstr = tstr.replace('%','')
        for i in range(len(tone[0])):
            if tstr.find(tone[0][i]) >= 0:
               tstr = tstr.replace(tone[0][i], tone[1][i], 1)
               break
        if tstr.find(u'ü') >= 0 and (tstr.find('j') >= 0 or tstr.find('q') >= 0 or tstr.find('x') >= 0):
            tstr = tstr.replace(u'ü', u'u', 1)
        return tstr

    def sort_by_clen_category(self, candidates):
        '''按码长/字符集排序'''
        if not candidates:
            return candidates[:]
        if not self._cfg._stChineseMode in(2,3):
            return candidates[:]
        _ia = wbjj.candidx_cate
        _ic = wbjj.candidx_code
        # 收集所有码长并排序
        _clenList = []
        for _candidate in candidates:
            _l = len(_candidate[wbjj.candidx_code])
            if _l not in _clenList:
                _clenList.append(_l)
        _clenList.sort()
        # 按先码长后字符集顺序排序
        _sortList = []
        for _l in _clenList:
            if self._cfg._stChineseMode == 2:
                # 简体优先的大字符集
                _sortList = _sortList + list(filter(lambda x,l=_l,ia=_ia,ic=_ic: len(x[ic]) == l and x[ia] & 1, candidates))\
                    + list(filter(lambda x,l=_l,ia=_ia,ic=_ic: len(x[ic]) == l and x[ia] & (1 << 1) and (not x[ia] & 1), candidates))\
                    + list(filter(lambda x,l=_l,ia=_ia,ic=_ic: len(x[ic]) == l and x[ia] & (1 << 2), candidates))
            elif self._cfg._stChineseMode == 3:
                # 繁体优先的大字符集
                _sortList = _sortList + list(filter(lambda x,l=_l,ia=_ia,ic=_ic: len(x[ic]) == l and x[ia] & (1 << 1), candidates))\
                    + list(filter(lambda x,l=_l,ia=_ia,ic=_ic: len(x[ic]) == l and x[ia] & 1 and (not x[ia] & (1 << 1)) , candidates))\
                    + list(filter(lambda x,l=_l,ia=_ia,ic=_ic: len(x[ic]) == l and x[ia] & (1 << 2), candidates))
        return _sortList

    def update_candidates(self):
        '''Update lookuptable'''
        print("DEBUG: in update_candidates() and self._query_code_str = " + str(self._query_code_str) + " and [fst]self._chars = " + str(self._chars))
        if (self._chars[0] == self._chars[2] and self._candidates) or self._chars[1]:
            return True
        self._ibus_lookup_table.clean()
        try:
            self._ibus_lookup_table.show_cursor(False)
        except:
            print("DEBUG: self._ibus_lookup_table.show_cursor(False) Error.")
        self._ibus_lookup_table.set_cursor_visible(True)
        if self._query_code_str:
            self._chars[2] = self._chars[0][:]
            if len(self._chars[0]) < 1:
                self._candidates = []
                return True
            # 在这里,我们需要考虑三种情况,中文数字,五笔和拼音
            st = ''.join(self._chars[0])
            regDate = r'^((((1[6-9]|[2-9]\d)\d{2})[\.\-\/](0?[13578]|1[02])[\.\-\/](0?[1-9]|[12]\d|3[01]))|(((1[6-9]|[2-9]\d)\d{2})[\.\-\/](0?[13456789]|1[012])[\.\-\/](0?[1-9]|[12]\d|30))|(((1[6-9]|[2-9]\d)\d{2})[\.\-\/]0?2[\.\-\/](0?[1-9]|1\d|2[0-8]))|(((1[6-9]|[2-9]\d)(0[48]|[2468][048]|[13579][26])|((16|[2468][048]|[3579][26])00))[\.\-\/]0?2[\.\-\/]29))$'
            regNum = r'^\-?[0-9]+(\.[0-9]+)?$'     # 取消负数支持 r'^\-?[0-9]+(\.[0-9]+)?$'
            # 中文日期优先
            if self._cfg._stChineseDigital and re.match(regDate, st):
                d1 = u'〇一二三四五六七八九'
                n1 = u'０１２３４５６７８９'
                ny = '年月'
                scn = ''
                for c in st[:]:
                    if c in '.-/':
                        scn = scn + str(ny[0:1])
                        ny = ny[1:]
                    else:
                        scn = scn + c
                scn = scn + '日'
                # 2020年3月15日
                chdate = scn
                # ２０２０年３月１５日
                cndate = ''.join(list(map(lambda x: x if not str(x).isdigit() else n1[int(x):int(x)+1], scn[:])))
                # 二〇二〇年三月十五日
                ccdate = ''.join(list(map(lambda x: x if not str(x).isdigit() else d1[int(x):int(x)+1], scn[:])))
                ccdate = ccdate.replace('一〇月','十月').replace('一一月','十一月').replace('一二月','十二月')
                if ccdate[-3:-2] == '月':
                    pass
                elif ccdate[-3:-2] == '一':
                    ccdate = ccdate[0:-3] + '十' + ccdate[-2:]
                else:
                    ccdate = ccdate[0:-2] + '十' + ccdate[-2:]
                # ２０２０．３．１５
                sfs = st.replace('.','．').replace('-','－').replace('/','／')
                fdate = ''.join(list(map(lambda x: x if not str(x).isdigit() else n1[int(x):int(x)+1], sfs[:])))
                self._candidates = []
                self._candidates.append(("", chdate, 3, "", 0, 0))
                self._candidates.append(("", cndate, 3, "", 0, 0))
                self._candidates.append(("", ccdate, 3, "", 0, 0))
                self._candidates.append(("", fdate, 3, "", 0, 0))
                for _CandidateTuple in self._candidates:
                    self.append_candidate_to_lookup_table_special(_CandidateTuple)
                return True
            # 中文数字次之
            elif self._cfg._stChineseDigital and re.match(regNum, st) and st != '.':
                p1 = u'零壹贰叁肆伍陆柒捌玖万仟佰拾元角分厘毫整'
                p2 = u'零一二三四五六七八九万千百十点～～～～～'
                n0 = u'0123456789.'
                n1 = u'０１２３４５６７８９．'
                unt = [[u'仟佰拾',u'万万亿'],[u'仟佰拾',u'万亿'],[u'仟佰拾',u'亿'],[u'仟佰拾',u'万'],[u'仟佰拾',u'元'],[u'角分厘',u'毫']]
                num = ['0000','0000','0000','0000','0000','0000']
                if self._chars[0][0] == '-':
                    negative = True
                    tnm_abs = ''.join(self._chars[0][1:])
                else:
                    negative = False
                    tnm_abs = ''.join(self._chars[0])
                tnm = ('000000000000000000000000' + tnm_abs + '.0000').split('.', 1)
                tnm[1] = tnm[1].replace('.','')  # 过滤多余小数点
                num[5] = tnm[1][:4]
                num[4] = tnm[0][-4:]
                num[3] = tnm[0][-8:-4]
                num[2] = tnm[0][-12:-8]
                num[1] = tnm[0][-16:-12]
                num[0] = tnm[0][-20:-16]
                umoney = u''
                for i in range(0,6):
                    if num[i] == '0000':
                        if umoney != u'' and (' '+umoney)[-1] != u'零':
                            umoney += u'零'
                    else:
                        for j in range(0,3):
                            if num[i][j] == '0':
                                if umoney != u'' and (' '+umoney)[-1] != u'零':
                                    umoney += u'零'
                            else:
                                umoney += p1[int(num[i][j])] + unt[i][0][j]
                        if num[i][3] != '0':
                            umoney += p1[int(num[i][3])]
                        if umoney[-1] == u'零':
                            umoney = umoney[:-1]
                        umoney += unt[i][1]
                if umoney[-1] == u'零':
                    umoney = umoney[:-1]
                if num[5] == '0000':
                    umoney += u'整'
                elif num[5][-1] == '0':
                    umoney = umoney[:-1]
                cnumber = ''.join(map(lambda x: p2[p1.find(x)], umoney)).replace(u'～', '')
                if cnumber[-1] == u'点':
                    cnumber = cnumber[:-1]      # 以"点"结尾去掉点
                if cnumber[0:2] == u'一十':
                    cnumber = cnumber[1:]       # 以"一十几"开头变成"十几"
                fnumber = ''.join(map(lambda x: n1[n0.find(x)], tnm_abs[:]))
                if negative:
                    fnumber = '－' + fnumber
                    cnumber = u'负' + cnumber
                    umoney = u'负' + umoney
                self._candidates = []
                self._candidates.append(("", fnumber, 3, "", 0, 0))
                self._candidates.append(("", cnumber, 3, "", 0, 0))
                self._candidates.append(("", umoney, 3, "", 0, 0))
                for _CandidateTuple in self._candidates:
                    self.append_candidate_to_lookup_table_special(_CandidateTuple)
                return True
            # 中文数字/日期输入过程
            elif self._cfg._stChineseDigital and re.match(regLikeNum, st):
                self._candidates = []
                self.append_candidate_to_lookup_table_special(None)
                return True
            # 五笔其次
            elif not self._py_mode:
                if self._cfg._stChineseMode == 0:
                    # 简体中文 simplify Chinese mode
                    self._candidates = self.db.select_wubi(self._query_code_str, self._cfg._stOneChar, 1)
                elif self._cfg._stChineseMode == 1:
                    # 繁体中文 traditional Chinese mode
                    self._candidates = self.db.select_wubi(self._query_code_str, self._cfg._stOneChar, 2)
                else:
                    # 全部
                    self._candidates = self.db.select_wubi(self._query_code_str, self._cfg._stOneChar)
            # 拼音最后
            else:
                # 如果单z引导符,则输出备选最后输入的字词,格式 字 五笔:code 拼音:code2
                if self._query_code_str == u'z':
                    self._candidates = self._last_candidates
                    if self._candidates:
                        _CandidateTuple = self._candidates[0]
                        _CandidateList = list(_CandidateTuple)
                        _CandidateList[wbjj.candidx_code] = ""
                        # 追加五笔编码
                        if _CandidateTuple[wbjj.candidx_code]:
                            _CandidateList[wbjj.candidx_code] = _CandidateList[wbjj.candidx_code] + u"  五笔:" + _CandidateTuple[wbjj.candidx_code]
                        # 追加拼音编码
                        _code2os = _CandidateTuple[wbjj.candidx_cod2].split(',')
                        _code2ns = []
                        for _code2 in _code2os:
                            _code2n = self.pinyin_tone(_code2)
                            if _code2n not in _code2ns:
                                _code2ns.append(_code2n)
                        if len(_code2ns) > 4:
                            _code2ns = _code2ns[0:4] + ['…']        # 多音情况只输出前4个并加省略号
                        if _code2ns:
                            _CandidateList[wbjj.candidx_code] = _CandidateList[wbjj.candidx_code] + u"  拼音:" + u", ".join(_code2ns)
                        # 追加到LookupTable
                        self.append_candidate_to_lookup_table_special(tuple(_CandidateList))
                    return True
                else:
                    if self._cfg._stChineseMode == 0:
                        # 简体中文 simplify Chinese mode
                        self._candidates = self.db.select_pinyin(self._query_code_str, self._cfg._stOneChar, 1)
                    elif self._cfg._stChineseMode == 1:
                        # 繁体中文 traditional Chinese mode
                        self._candidates = self.db.select_pinyin(self._query_code_str, self._cfg._stOneChar, 2)
                    else:
                        # 全部
                        self._candidates = self.db.select_pinyin(self._query_code_str, self._cfg._stOneChar)
        else:
            self._candidates = []
        # 按码长和字符集设置排序
        self._candidates = self.sort_by_clen_category(self._candidates)
        # 检查全角状态,在第三侯选位(如果有)插入全角字符
        if self._cfg._stFullLetter:
            _word = u"".join(list(map(tabdict.unichar_half_to_full, self._chars[0])))
            if len(self._candidates) > 2:
                self._candidates.insert(2, (''.join(self._chars[0]), _word, 3, '', 0, 0))
            else:
                self._candidates.append((''.join(self._chars[0]), _word, 3, '', 0, 0))
        if self._candidates:
            for candidate in self._candidates:
                self.append_candidate_to_lookup_table(candidate)
            return True
        if self._chars[0]:
            if not self._chars[1]:
                if ascii_ispunct(chr(ord(self._chars[0][-1].encode('ascii')))) or self.is_onlyone_candidate():
                    if self._py_mode:
                        if self._chars[0][-1] in "!@#$%":
                            self._chars[0].pop() 
                            self._query_code_str = self._query_code_str[:-1]
                            return True
                    if len(self._candidates) > 1 and self._candidates[1]:
                        self._candidates = self._candidates[1]
                        self._candidates[1] = []
                        last_input = self.pop_input()
                        self.auto_commit_to_preedit()
                        res = self.add_input(last_input)
                        return res
                    else:
                        self.pop_input()
                        #self._ibus_lookup_table.clean()
                        #self._ibus_lookup_table.show_cursor(False)
                        return False
                else:    
                    # this is not a punct or not a valid phrase last time
                    self._chars[1].append(self._chars[0].pop())
                    self._query_code_str = self._query_code_str[:-1]
            self._candidates = []
        return True

    def create_update(self, wordlen):
        '''造词模式的数据更新(附带lookup显示数据更新)'''
        # self._word_history 格式: [['字','wubicode','pinyincode'],...]
        l = len(list(filter(lambda x: x[0] != '', self._word_history)))
        self._ibus_lookup_table.clean()
        self._candidates = []
        if l < 2:
            return False
        elif l < wordlen:
            wordlen = l
        if wordlen > 16:
            wordlen = 16
        elif wordlen < 2:
            wordlen = 2
        word = u''
        pycode = []
        cate = 0
        n = -1 * wordlen
        for _WordTuple in self._word_history[n:]:
            word = word + _WordTuple[0]
            if _WordTuple[1] == '':
                _WordTuple[1] = self.db.get_wubi_code(_WordTuple[0])    # 查询五笔编码
            if _WordTuple[1].find('?') > 0:
                return False
            if _WordTuple[2] == '':
                _WordTuple[2] = self.db.get_pinyin_code(_WordTuple[0])  # 查询拼音编码
            if _WordTuple[2].find('?') > 0:
                return False
            if len(pycode) == 0:
                pycode = _WordTuple[2].split(',')
            else:
                _pycode_list = pycode[:]
                pycode.clear()
                _pyword_list = _WordTuple[2].split(',')
                for _py in _pycode_list:
                    for _c in _pyword_list:
                        _pystr = _py + _c
                        _pystr = _pystr[0:16]   # 拼音编码超长截断
                        if _pystr not in pycode:
                            pycode.append(_pystr)
        # 按五笔词组编码规则合成词的编码,两字AABB,三字ABCC,四字及以上ABCN
        if wordlen == 2:
            wbcode = self._word_history[n][1][0:2] + self._word_history[-1][1][0:2]
        elif wordlen == 3:
            wbcode = self._word_history[n][1][0] + self._word_history[n+1][1][0] + self._word_history[-1][1][0:2]
        else:
            wbcode = self._word_history[n][1][0] + self._word_history[n+1][1][0] + self._word_history[n+2][1][0] + self._word_history[-1][1][0]
        cate = wbjj.get_category(word)
        attrs = IBus.AttrList()
        self._wb_char_list = ['']
        # 五笔编码追加到_candidates
        self._candidates.append((wbcode, word, cate, ','.join(pycode), 0, 0))
        # 五笔编码上色
        attrs.append(IBus.attr_foreground_new(self._cfg._ltCodeColor, 0, 3))
        attrs.append(IBus.attr_foreground_new(self._cfg._ltCode2Color, 3, 3 + len(wbcode)))
        self._ibus_lookup_table.append_candidate(IBus.Text(u'五笔:' + wbcode, attrs))
        # 拼音编码追加到_candidates
        for _py in pycode:
            self._candidates.append((_py, word, cate, wbcode, 0, 0))
            # 拼音编码上色
            attrs.append(IBus.attr_foreground_new(self._cfg._ltCodeColor, 0, 3))
            attrs.append(IBus.attr_foreground_new(self._cfg._ltCode2Color, 3, 3 + len(_py)))
            self._ibus_lookup_table.append_candidate(IBus.Text(u'拼音:' + _py, attrs))
        self._ibus_lookup_table.show_cursor(False)
        self._ibus_lookup_table.set_cursor_visible(True)    # 设置焦点
        return True

    def create_remove(self, index):
        '''造词模式下从历史字表中删除字'''
        l = len(list(filter(lambda x: x[0] != '', self._word_history)))
        if l <= 2:
            return False
        self._word_history.pop(index)
        self._word_history.insert(0, [u'','',''])

    def create_add(self, pos):
        '''造词模式保存新词到数据库'''
        if pos == -1:
           pos = self._ibus_lookup_table.get_cursor_pos()
        if pos >= len(self._candidates):
            return False
        self._ibus_lookup_table.set_cursor_pos(pos)
        word = self._candidates[pos][wbjj.candidx_word]
        code = self._candidates[pos][wbjj.candidx_code]
        code2 = self._candidates[pos][wbjj.candidx_cod2]
        if len(code) <= 0:
            return False
        if pos == 0:
            table = 'wubi3'
        else:
            table = 'pinyin3'
        res = self.db.set_new_word(word, code, code2, table)
        return res

    def commit_to_preedit(self):
        '''将从lookup中选中的词提交到preedit'''
        try:
            _c = self.get_cursor_pos()
            if self._candidates:
                self._precommit_list.insert(self._cursor[0], self._candidates[_c][wbjj.candidx_word])
                self._cursor[0] += 1
                # 保存输入历史
                _candidate = self._candidates[_c]
                self._last_candidates = [_candidate]
                if self._py_mode:
                    # code与code2互换位置(五笔编码只取最简码,拼音编码返回所有音)
                    self._last_candidates[0] = (\
                        self._last_candidates[0][wbjj.candidx_cod2].split(',')[0],\
                        self._last_candidates[0][wbjj.candidx_word],\
                        self._last_candidates[0][wbjj.candidx_cate],\
                        self.db.get_pinyin_code(self._last_candidates[0][wbjj.candidx_word]),\
                        self._last_candidates[0][wbjj.candidx_freq],\
                        self._last_candidates[0][wbjj.candidx_ureq]\
                    )
                if len(_candidate[wbjj.candidx_word]) == 1:
                    if self._py_mode:
                        _code = _candidate[wbjj.candidx_code].replace('!','').replace('@','').replace('#','').replace('$','').replace('%','')
                        self._word_history.append([_candidate[wbjj.candidx_word], '', _code])
                    elif len(_candidate[wbjj.candidx_word]) == 4:
                        _code = _candidate[wbjj.candidx_code]
                        self._word_history.append([_candidate[wbjj.candidx_word], _code, ''])
                    else:
                        self._word_history.append([_candidate[wbjj.candidx_word], '', ''])
                else:
                    for w in self._candidates[_c][wbjj.candidx_word]:
                        self._word_history.append([w, '', ''])
                self._word_history = self._word_history[-1 * wbjj.historywords:]
            self.over_input()
            self.update_candidates()
        except:
            if wbjj.options.debug:
                raise
                # import traceback
                # traceback.print_exc()
            pass
    
    def auto_commit_to_preedit(self):
        '''Add select phrase in lookup table to preedit string'''
        try:
            self._un_char_list.append(self._chars[0][:])
            self._precommit_list.insert(self._cursor[0], self._candidates[self.get_cursor_pos()][wbjj.candidx_word])
            self._cursor[0] += 1
            self.clear_input()
            self.update_candidates()
        except:
            pass

    def get_input_chars(self):
        '''get characters held, valid and invalid'''
        return self._chars[0] + self._chars[1]

    def get_all_input_strings(self):
        '''Get all uncommit input characters, used in English mode or direct commit'''
        return  u''.join(map(u''.join, self._un_char_list + [self._chars[0]] + [self._chars[1]]))
    
    def get_preedit_strings(self):
        '''Get preedit strings'''
        _word = u''.join(self._precommit_list)
        if self._candidates:
            _word += self._candidates[int(self._ibus_lookup_table.get_cursor_pos())][wbjj.candidx_word]         # 返回备选当前页的第一个字/词
        else:
            _word += u''.join(self.get_input_chars())      # 返回输入的字符串
        if len(_word) > 0: print("DEBUG: in get_preedit_strings() and _word = " + _word + " and self._precommit_list = " + str(self._precommit_list) + " and self._un_char_list = " + str(self._un_char_list))
        return _word

    def get_aux_strings(self):
        '''Get aux strings'''
        if self._create_mode:
            return '造词: <=>加字,<->去字,<Del|←>删字,选字确认'
        else:
            input_chars = self.get_input_chars()
            if input_chars:
                aux_string = u''.join(self._chars[0]) 
                if self._py_mode:
                    aux_string = aux_string.replace('!','1').replace('@','2').replace('#','3').replace('$','4').replace('%','5')
                return aux_string
            return ''

    def get_cursor_pos(self):
        '''get lookup table cursor position'''
        return self._ibus_lookup_table.get_cursor_pos()

    def get_lookup_table(self):
        '''Get lookup table'''
        return self._ibus_lookup_table

    # 普通编辑事件相关函数 ====================================================================================

    def space(self):
        '''处理 space 按键事件, 返回值: (KeyProcessResult,whethercommit,commitstring)'''
        print("DEBUG: in space() and _chars[1] = " + str(self._chars[1]) + ", _wb_char_list = " + str(self._wb_char_list))
        if self._chars[1] or ''.join(self._chars[0]) == '-':
            # 含无效输入或仅为-,不提交
            return (False, u'')
        elif self._wb_char_list:
            # 五笔/拼音输入
            istr = self.get_all_input_strings()
            self.commit_to_preedit()
            pstr = self.get_preedit_strings()
            print("DEBUG: in space() and pstr = " + str(pstr))
            self.clear()
            return (True, pstr, istr)
        else:
            return (False, u'')
    
    def backspace(self):
        '''处理 backspace 按键事件'''
        if self.get_input_chars():
            self.pop_input()
            return True
        elif self.get_preedit_strings():
            self.remove_before_char()
            return True
        else:
            return False
    
    def delete(self):
        '''处理 delete 按键事件'''
        if self.get_input_chars():
            return True
        elif self.get_preedit_strings():
            self.remove_after_char()
            return True
        else:
            return False
    
    def number(self, index):
        '''将备选序号对应的词存入preedit中'''
        cursor_pos = self._ibus_lookup_table.get_cursor_pos()
        cursor_page = self._ibus_lookup_table.get_cursor_in_page()
        current_page_start = cursor_pos - cursor_page
        real_index = current_page_start + index
        if real_index >= len(self._candidates):
            return False
        self._ibus_lookup_table.set_cursor_pos(real_index)
        self.commit_to_preedit()
        return True

    def cursor_down(self):
        '''处理方向键事件, 在LookupTable中后移焦点'''
        res = self._ibus_lookup_table.cursor_down()
        self.update_candidates()
        if not res and self._candidates:
            return True
        return res
    
    def cursor_up(self):
        '''处理方向键事件, 在LookupTable中前移焦点'''
        res = self._ibus_lookup_table.cursor_up()
        self.update_candidates()
        if not res and self._candidates:
            return True
        return res
    
    def page_down(self):
        '''处理方向键事件, 在LookupTable中向后翻页'''
        res = self._ibus_lookup_table.page_down()
        self.update_candidates()
        if not res and self._candidates:
            return True
        return res
    
    def page_up(self):
        '''处理方向键事件, 在LookupTable中向前翻页'''
        res = self._ibus_lookup_table.page_up()
        self.update_candidates()
        if not res and self._candidates:
            return True
        return res
    
    # Ctrl,Alt事件相关函数 ====================================================================================

    def control_backspace(self):
        '''处理 Ctrl+Backspace 按键事件'''
        if self.get_input_chars():
            self.over_input()
            return True
        elif self.get_preedit_strings():
            self.remove_before_string()
            return True
        else:
            return False

    def control_delete(self):
        '''处理 Ctrl+Delete 按键事件'''
        if self.get_input_chars():
            return True
        elif self.get_preedit_strings():
            self.remove_after_string()
            return True
        else:
            return False

    def control_arrow_left(self):
        '''Process Control + Arrow Left Key Event. Update cursor data when move caret to string left'''
        if self.get_preedit_strings():
            if not (self.get_input_chars() or self._un_char_list):
                if self._cursor[1] == 0:
                    if self._cursor[0] == 0:
                        self._cursor[0] = len(self._precommit_list) - 1
                    else:
                        self._cursor[0] -= 1
                else:
                    self._cursor[1] = 0
                self.update_candidates()
            return True
        else:
            return False
    
    def control_arrow_right(self):
        '''Process Control + Arrow Right Key Event. Update cursor data when move caret to string right'''
        if self.get_preedit_strings():
            if not (self.get_input_chars() or self._un_char_list):
                if self._cursor[1] == 0:
                    if self._cursor[0] == len(self._precommit_list):
                        self._cursor[0] = 1
                    else:
                        self._cursor[0] += 1
                else:
                    self._cursor[0] += 1
                    self._cursor[1] = 0
                self.update_candidates()
            return True
        else:
            return False

    def alt_number(self, index):
        '''从用户的数据库索引中删除查找表中的候选项应从0开始'''
        cursor_pos = self._ibus_lookup_table.get_cursor_pos()
        cursor_page = self._ibus_lookup_table.get_cursor_in_page()
        current_page_start = cursor_pos - cursor_page
        real_index = current_page_start + index
        if index < 0:
            pos = current_page_start
        else:
            pos = current_page_start + index
        if len(self._candidates) > pos:
            tCandidateTuple = self._candidates[pos]
            if tCandidateTuple[wbjj.candidx_freq] < 0:
                self.db.remove_phrase(tCandidateTuple)
                self._chars[2].pop()
                self.update_candidates()
            return True
        else:
            return False


class TabEngine(IBus.Engine):
    '''The IM Engine for Tables'''
    def __init__(self, bus, obj_path, db):
        super().__init__(connection=bus.get_connection(), object_path=obj_path)
        self._cfg = IMEConfig(bus, db)
        self.db = db 
        self._editor = Editor(self._cfg, self.db)
        self._mode = 1                  # 0:英文模式, 1:中文模式
        # some other vals we used:
        # self._prev_key: hold the key event last time.
        self._prev_key = None
        self._prev_char = None
        self._double_quotation_state = False
        self._single_quotation_state = False
        # the commit phrases length
        self._len_list = [0]
        self._on = False
        self.reset()

    def reset(self):
        '''reset事件响应过程'''
        self._editor.clear()
        self._double_quotation_state = False
        self._single_quotation_state = False
        self._prev_key = None
        self._init_properties()
        self._update_ui()
    
    def do_destroy(self):
        try:
            self.reset()
        except:
            pass
        self.do_focus_out()
        #self.db.sync_usrdb()
        super().destroy()

    def _init_properties(self):
        self.properties = IBus.PropList()
        self._status_property = IBus.Property(key=u'InputMode')         # GNOME3 Panel Key = InputMode, 原 Key = status 无法与Panel关联动作
        self._cmode_property = IBus.Property(key=u'cmode')
        self._letter_property = IBus.Property(key=u'letter')
        self._punct_property = IBus.Property(key=u'punct')
        self._more_property = IBus.Property(key=u'more', type=3, label=u'', icon=wbjj.iconpath+'setup.svg')
        # 设置子菜单
        self.subproperties = IBus.PropList()
        self._onechar_subproperty = IBus.Property(key=u'onechar', type=IBus.PropType.TOGGLE, label=u'单字模式　Ctrl+,')
        self._autocommit_subproperty = IBus.Property(key=u'acommit', type=IBus.PropType.TOGGLE, label=u'自动提交　Ctrl+/')
        self._cndigital_subproperty = IBus.Property(key=u'cndigital', type=IBus.PropType.TOGGLE, label=u'中文数字　Ctrl+\'')
        self._line0_subproperty = IBus.Property(key=u'line0', type=IBus.PropType.SEPARATOR)
        self._setup_subproperty = IBus.Property(key=u'setup', type=IBus.PropType.NORMAL, label=u'首选项…　Ctrl+Alt+Shift+F2', icon=wbjj.iconpath+'setup.svg')
        self._line1_subproperty = IBus.Property(key=u'line1', type=IBus.PropType.SEPARATOR)
        self._help_subproperty  = IBus.Property(key=u'help',  type=IBus.PropType.NORMAL, label=u'帮助…　　Ctrl+Alt+Shift+F1', icon=wbjj.iconpath+'help.svg')
        for prop in (
                self._onechar_subproperty, 
                self._autocommit_subproperty, 
                self._cndigital_subproperty,
                self._line0_subproperty, 
                self._setup_subproperty, 
                self._line1_subproperty, 
                self._help_subproperty
            ):
            self.subproperties.append(prop)
        self._more_property.set_sub_props(self.subproperties)
        self._more_property.set_label(_(u'更多选项'))
        for prop in (
                self._status_property,
                self._cmode_property,
                self._letter_property,
                self._punct_property,
                self._more_property,
            ):
            self.properties.append(prop)
        self.register_properties(self.properties)
        self._refresh_properties()
    
    def _refresh_properties(self):
        '''属性更新方法 Method used to update properties'''
        if self._mode == 1:
            if self._editor._py_mode:
                self._status_property.set_icon(u'%s%s' % (wbjj.iconpath, 'ibus-pinyin.svg'))
                self._status_property.set_label(_(u'拼音　　　' + self._cfg._hkEnSwitchKeyStr))
                self._status_property.set_symbol(IBus.Text.new_from_string(u'拼'))
                self._status_property.set_tooltip(_(u'已激活拼音模式,切换到英文模式\n[' + self._cfg._hkEnSwitchKeyStr + ']'))
            else:
                self._status_property.set_icon(u'%s%s' % (wbjj.iconpath, 'chinese.svg'))
                self._status_property.set_label(_(u'五笔　　　' + self._cfg._hkEnSwitchKeyStr))
                self._status_property.set_symbol(IBus.Text.new_from_string(u'五'))
                self._status_property.set_tooltip(_(u'切换到英文模式\n[' + self._cfg._hkEnSwitchKeyStr + ']'))
        else:
            self._status_property.set_icon(u'%s%s' % (wbjj.iconpath, 'english.svg'))
            self._status_property.set_label(_(u'英文　　　' + self._cfg._hkEnSwitchKeyStr))
            self._status_property.set_symbol(IBus.Text.new_from_string(u'英'))
            self._status_property.set_tooltip(_(u'切换到五笔模式\n[' + self._cfg._hkEnSwitchKeyStr + ']'))

        if self._cfg._stChineseMode == 0:
            self._cmode_property.set_icon(u'%s%s' % (wbjj.iconpath, 'sc-mode.svg'))
            self._cmode_property.set_label(_(u'简体　　　Ctrl+;'))
            self._cmode_property.set_symbol(IBus.Text.new_from_string(u'简'))
            self._cmode_property.set_tooltip(_(u'切换到繁体中文模式\n[Ctrl+;]'))
        elif self._cfg._stChineseMode == 1:
            self._cmode_property.set_icon(u'%s%s' % (wbjj.iconpath, 'tc-mode.svg'))
            self._cmode_property.set_label(_(u'繁体　　　Ctrl+;'))
            self._cmode_property.set_symbol(IBus.Text.new_from_string(u'繁'))
            self._cmode_property.set_tooltip(_(u'切换到简体优先的大字符集模式\n[Ctrl+;]'))
        elif self._cfg._stChineseMode == 2:
            self._cmode_property.set_icon(u'%s%s' % (wbjj.iconpath, 'scb-mode.svg'))
            self._cmode_property.set_label(_(u'简繁　　　Ctrl+;'))
            self._cmode_property.set_symbol(IBus.Text.new_from_string(u'简大'))
            self._cmode_property.set_tooltip(_(u'切换到繁体优先的大字符集模式\n[Ctrl+;]'))
        elif self._cfg._stChineseMode == 3:
            self._cmode_property.set_icon(u'%s%s' % (wbjj.iconpath, 'tcb-mode.svg'))
            self._cmode_property.set_label(_(u'繁简　　　Ctrl+;'))
            self._cmode_property.set_symbol(IBus.Text.new_from_string(u'繁大'))
            self._cmode_property.set_tooltip(_(u'切换到大字符集模式\n[Ctrl+;]'))
        elif self._cfg._stChineseMode == 4:
            self._cmode_property.set_icon(u'%s%s' % (wbjj.iconpath, 'cb-mode.svg'))
            self._cmode_property.set_label(_(u'汉字　　　Ctrl+;'))
            self._cmode_property.set_symbol(IBus.Text.new_from_string(u'大'))
            self._cmode_property.set_tooltip(_(u'切换到简体中文模式\n[Ctrl+;]'))

        if self._cfg._stFullLetter:
            self._letter_property.set_icon(u'%s%s' % (wbjj.iconpath, 'full-letter.svg'))
            self._letter_property.set_label(_(u'全角　　　Shift+空格'))
            self._letter_property.set_symbol(IBus.Text.new_from_string(u'●'))
            self._letter_property.set_tooltip(_(u'切换到半角字符\n[Shift+空格]'))
        else:
            self._letter_property.set_icon(u'%s%s' % (wbjj.iconpath, 'half-letter.svg'))
            self._letter_property.set_label(_(u'半角　　　Shift+空格'))
            self._letter_property.set_symbol(IBus.Text.new_from_string(u'◑'))
            self._letter_property.set_tooltip(_(u'切换到全角字符\n[Shift+空格]'))

        if self._cfg._stFullPunct:
            self._punct_property.set_icon(u'%s%s' % (wbjj.iconpath, 'full-punct.svg'))
            self._punct_property.set_label(_(u'全角标点　Ctrl+.'))
            self._punct_property.set_symbol(IBus.Text.new_from_string(u'。'))
            self._punct_property.set_tooltip(_(u'切换到半角标点\n[Ctrl+.]'))
        else:
            self._punct_property.set_icon(u'%s%s' % (wbjj.iconpath,'half-punct.svg'))
            self._punct_property.set_label(_(u'半角标点　Ctrl+.'))
            self._punct_property.set_symbol(IBus.Text.new_from_string(u',.'))
            self._punct_property.set_tooltip(_(u'切换到全角标点\n[Ctrl+.]'))
        
        self._onechar_subproperty.set_state(int(self._cfg._stOneChar))
        self._autocommit_subproperty.set_state(int(self._cfg._stAutoCommit))
        self._cndigital_subproperty.set_state(int(self._cfg._stChineseDigital))

        if self._mode == 1:
            self._cmode_property.set_sensitive(True)
            self._letter_property.set_sensitive(True)
            self._punct_property.set_sensitive(True)
            self._onechar_subproperty.set_sensitive(True)
            self._autocommit_subproperty.set_sensitive(True)
            self._cndigital_subproperty.set_sensitive(True)
        else:
            self._cmode_property.set_sensitive(False)
            self._cmode_property.set_tooltip(_(u''))
            self._letter_property.set_sensitive(False)
            self._letter_property.set_tooltip(_(u''))
            self._punct_property.set_sensitive(False)
            self._punct_property.set_tooltip(_(u''))
            self._onechar_subproperty.set_sensitive(False)
            self._autocommit_subproperty.set_sensitive(False)
            self._cndigital_subproperty.set_sensitive(False)

        # 调用更新,使属性生效
        for prop in (
                self._status_property,
                self._cmode_property,
                self._letter_property,
                self._punct_property,
                self._more_property,
            ):
            self.update_property(prop)
        for prop in (
                self._onechar_subproperty, 
                self._autocommit_subproperty, 
                self._cndigital_subproperty, 
                self._line0_subproperty, 
                self._setup_subproperty, 
                self._line1_subproperty, 
                self._help_subproperty
            ):
            self.update_property(prop)

#   def register_properties(IBusEngine *engine, IBusPropList *prop_list):
#       方法继承自 IBus.Engine
    
    def do_property_activate(self, ibus_property, prop_state=IBus.PropState.UNCHECKED):
        '''属性活动响应过程'''
        if ibus_property == u'status' or ibus_property == u'InputMode':
            self._change_mode()
        elif ibus_property == u'cmode':
            self._cfg._set_stChineseMode((self._cfg._stChineseMode + 1) % 5)
            self.reset()
        elif ibus_property == u'letter':
            self._cfg._set_stFullLetter(not self._cfg._stFullLetter)
        elif ibus_property == u'punct':
            self._cfg._set_stFullPunct(not self._cfg._stFullPunct)
        elif ibus_property == u'onechar':
            self._cfg._set_stOneChar(not self._cfg._stOneChar)
            self._onechar_subproperty.set_state(int(self._cfg._stOneChar))
        elif ibus_property == u'acommit':
            self._cfg._set_stAutoCommit(not self._cfg._stAutoCommit)
            self._autocommit_subproperty.set_state(int(self._cfg._stAutoCommit))
        elif ibus_property == u'cndigital':
            self._cfg._set_stChineseDigital(not self._cfg._stChineseDigital)
            self._cndigital_subproperty.set_state(int(self._cfg._stChineseDigital))
        elif ibus_property == "setup":
            # 异步调用,并行执行,确保对话框打开时输入法依然可用
            import subprocess
            subprocess.Popen(wbjj.setup, shell=True)
        elif ibus_property == u'help':
            import webbrowser
            webbrowser.open_new_tab(wbjj.help)
        self._refresh_properties()
    
    def _change_mode(self):
        '''切换输入模式, 五笔(1)->英文(0)->五笔(1) Shift input mode, TAB -> EN -> TAB'''
        self._mode = int(not self._mode)
        self.reset()

    def _update_preedit(self):
        '''更新预编辑字符(即将上屏的文字)'''
        _preedit_strings = self._editor.get_preedit_strings()
        if _preedit_strings == u'':
            super().update_preedit_text(IBus.Text(u'',None), 0, False)
        else:
            attrs = IBus.AttrList()
            if len(self._editor._precommit_list) > 0:
                # _precommit_list字符着色,以区分当前输入
                attrs.append(IBus.attr_foreground_new(self._cfg._pcFontColor, 0, len(u''.join(self._editor._precommit_list))))
            # _preedit_strings字符加下划线,以区分待提交
            attrs.append(IBus.attr_underline_new(IBus.AttrUnderline.SINGLE, 0, len(_preedit_strings)))
            #super().update_preedit_text(IBus.Text(_preedit_strings, attrs), self._editor.get_caret(), True)
            _cursor_pos = 1 if self._editor._create_mode else len(_preedit_strings)     # 造词模式光标始终停在第一个字后
            super().update_preedit_text(IBus.Text(_preedit_strings, attrs), _cursor_pos, True)
    
    def _update_aux(self):
        '''更新编辑框中的字符(当前编辑的编码)'''
        if self._editor._chars[1]:
            # 存在无效字符时,直接输出全部字符串
            _input_chars = ''.join(self._editor._chars[0]) + ''.join(self._editor._chars[1])
        else:
            # 提取当前的字符
            _input_chars = self._editor.get_aux_strings()
        if _input_chars:
            print("DEBUG: in _update_aux() and _input_chars = " + _input_chars)
            attrs = IBus.AttrList()
            attrs.append(IBus.attr_foreground_new(0x9515b5, 0, len(_input_chars)))
            super().update_auxiliary_text(IBus.Text(_input_chars, attrs), True)
        else:
            self.hide_auxiliary_text()

    def _update_lookup_table(self):
        '''更新LookupTable(备选列表)'''
        if not self._editor._candidates:
            super().hide_lookup_table()
            return
        if self._editor.is_empty():
            super().hide_lookup_table()
            return
        print("DEBUG: in _update_lookup_table() and _editor._candidates = " + str(self._editor._candidates))
        super().update_lookup_table(self._editor.get_lookup_table(), True)

    def _update_ui(self):
        '''Update User Interface'''
        self._update_lookup_table()
        self._update_preedit()
        self._update_aux()

    def _create_update_ui(self):
        '''造词模式的UI更新'''
        self._update_lookup_table()
        self._update_preedit()
        self._update_aux()

    def commit_string(self,string):
        '''提交上屏'''
        self._editor.clear()
        self._update_ui()
        if len(string) > 0:
            super().commit_text(IBus.Text(string))
            self._prev_char = string[-1]

    def _convert_to_full_width(self, c):
        '''转换半角字符到全角字符'''
        if not self._mode:
            return c
        _href_chars = u"`~!@#$%&*()+-=[]{}\\|;:,.<>/?^_''\"\""
        _full_chars = u"·～！＠＃￥％＆×（）＋－＝［］｛｝、｜；：，。《》、？…—‘’“”"
        _full_char = u""
        _index = _href_chars.find(c)
        if _index >= 0:
            _char = _full_chars[_index]
            if c == u"." and self._prev_char and self._prev_char.isdigit() and self._prev_key and chr(self._prev_key.code) == self._prev_char:
                return c
            elif c == u"^" or c == u"_":
                return _char + _char
            elif c == u"\"":
                # 双引号自动配对
                self._double_quotation_state = not self._double_quotation_state
                return _char if self._double_quotation_state else _full_chars[_index+1]
            elif c == u"'":
                # 单引号自动配对
                self._single_quotation_state = not self._single_quotation_state
                return _char if self._single_quotation_state else _full_chars[_index+1]
            else:
                return _char
        else:
            return tabdict.unichar_half_to_full(c)
    
    def _match_hotkey(self, key, code, mask):
        if key.code == code and key.mask == mask:
            if self._prev_key and key.code == self._prev_key.code and key.mask & IBus.ModifierType.RELEASE_MASK:
                return True
            if not key.mask & IBus.ModifierType.RELEASE_MASK:
                return True
        return False
    
    def do_process_key_event(self, keyval, keycode, state):
        '''键盘事件响应过程[事件接口]'''
        key = KeyEvent(keyval, state & IBus.ModifierType.RELEASE_MASK == 0, state)
        # ignore NumLock mask
        key.mask &= ~IBus.ModifierType.MOD2_MASK
        #try:
        if 1==1:
            result = self._process_key_event(key)
        #except:
        #    result = false
        #    if wbjj.options.debug:
        #        raise
        #        #import traceback
        #        #traceback.print_exc()
        self._prev_key = key
        return result

    def _process_key_event(self, key):
        '''键盘事件响应过程[内部过程]'''
        # 中/英切换热键 Match mode switch hotkey
        if key.code in self._cfg._hkEnSwitchKey:
            if key.code in (IBus.Control_L, IBus.Control_R):
                key_mask = IBus.ModifierType.CONTROL_MASK
            elif key.code in (IBus.Shift_L, IBus.Shift_R):
                key_mask = IBus.ModifierType.SHIFT_MASK
            if self._match_hotkey(key, key.code, key_mask | IBus.ModifierType.RELEASE_MASK):
                if not self._editor.is_empty():
                    self.reset()
                self._change_mode()
                return True
        if key.mask & IBus.ModifierType.CONTROL_MASK and key.mask & IBus.ModifierType.MOD1_MASK and key.mask & IBus.ModifierType.SHIFT_MASK and not key.mask & IBus.ModifierType.RELEASE_MASK:
            # 设置
            if self._cfg._hkSetupHotKey and key.code == IBus.F2:
                self.do_property_activate(u'setup')
                return True
            # 帮助
            if self._cfg._hkSetupHotKey and key.code == IBus.F1:
                self.do_property_activate(u'help')
                return True
            # 自杀键组合(Ctrl+Alt+Shift+BackSpace)
            elif self._cfg._hkKillHotKey and key.code == IBus.BackSpace:
                os.system("ibus-daemon -d -x -r")
                return True
            return False
        if self._mode:
            # 中文输入状态下的键盘事件处理
            return self._table_mode_process_key_event(key)
        else:
            # 英文输入状态下的键盘事件处理
            return self._english_mode_process_key_event(key)

    def _table_mode_process_key_event(self, key):
        '''中文模式键盘事件处理过程'''
        cond_letter_translate = lambda c: self._convert_to_full_width(c) if self._cfg._stFullLetter else c
        cond_punct_translate = lambda c: self._convert_to_full_width(c) if self._cfg._stFullPunct else c
        try:
           _keychar = chr(key.code)
        except:
           _keychar = u""
        IBUS_0=0x030
        IBUS_1=0x031
        IBUS_2=0x032
        IBUS_3=0x033
        IBUS_4=0x034
        IBUS_5=0x035
        IBUS_6=0x036
        IBUS_7=0x037
        IBUS_8=0x038
        IBUS_9=0x039

        # 处理释放事件(KeyUp事件)
        if key.mask & IBus.ModifierType.RELEASE_MASK:
            # Shift处理, 左Shift选第二备选字, 右Shift选第三备选字
            if self._cfg._hkShiftSelection and (self._match_hotkey(key, IBus.Shift_L, IBus.ModifierType.SHIFT_MASK | IBus.ModifierType.RELEASE_MASK) or self._match_hotkey(key, IBus.Shift_R, IBus.ModifierType.SHIFT_MASK | IBus.ModifierType.RELEASE_MASK)) and self._editor._candidates:
                if not self._editor._create_mode:
                    if key.code == IBus.Shift_L:
                        res = self._select_number(1)
                    else:
                        res = self._select_number(2)
                    return res
                else:
                    if key.code == IBus.Shift_L:
                        res = self._editor.create_add(1)    # 按第二组编码(拼音编码)造词
                    elif key.code == IBus.Shift_R:
                        res = self._editor.create_add(2)    # 按第三组编码(拼音编码)造词
                    if res:
                        self._editor.clear()
                        self.reset()
                    return True
            # 释放失效
            return True

        # 不带Alt或Ctrl键的键盘事件
        if not key.mask & IBus.ModifierType.MOD1_MASK and not key.mask & IBus.ModifierType.CONTROL_MASK:
            # Shift快捷键优先处理
            if key.mask & IBus.ModifierType.SHIFT_MASK:
                # 全/半角切换热键 Match full half letter mode switch hotkey
                if self._match_hotkey(key, IBus.space, IBus.ModifierType.SHIFT_MASK):
                    self.do_property_activate(u"letter")
                    return True
            # 在编辑框为空时,按下非编码键则原字符输出,不进入编辑框
            if self._editor.is_empty():
                if key.code <= 127 and _keychar not in wbjj.wbValidChar + (wbjj.numValidChar if self._cfg._stChineseDigital else ''):
                    if key.code == IBus.space:
                        # 空格
                        self.commit_string(cond_letter_translate(_keychar))
                        return True
                    if ascii_ispunct(_keychar) and ((not self._cfg._stChineseDigital) or (self._cfg._stChineseDigital and _keychar not in '.-/')):
                        # 标点符号
                        self.commit_string(cond_punct_translate(_keychar))
                        return True
                    if ascii_isdigit(key.code) and not self._cfg._stChineseDigital:
                        # 数字
                        self.commit_string(cond_letter_translate(_keychar))
                        return True
                elif key.code > 127 and not self._editor._py_mode:
                    return False

                # 如果首字符是z则进入拼音模式,否则退出拼音模式(切换)
                if (not self._editor._py_mode) and _keychar == u"z":
                   res = self._editor.switch_py_wb()
                   self._refresh_properties()

            elif self._editor._py_mode and self._editor._wb_char_list[0] != u"z":
                res = self._editor.switch_py_wb()
                self._refresh_properties()

            # 非造词模式(即正常模式)
            if not self._editor._create_mode:
                # 正常输入
                is_numeric = self._cfg._stChineseDigital and re.match(regLikeNum, ''.join(self._editor._chars[0]) + _keychar)
                if (_keychar in wbjj.wbValidChar or _keychar == u"z") or \
                   (self._editor._py_mode and _keychar in wbjj.pyValidChar) or \
                   (is_numeric):
                    # 输入字符追加到输入框
                    if 1==1:
                    #try:
                        res = self._editor.add_input(_keychar)
                        if not res:
                            if ascii_ispunct(_keychar):
                                key_char = cond_punct_translate(_keychar)
                            else:
                                key_char = cond_letter_translate(_keychar)
                            sp_res = self._editor.space()
                            if sp_res[0]:
                                self.commit_string(sp_res[1] + key_char)
                                self.db.check_phrase(sp_res[1], sp_res[2])
                                return True
                            else:
                                self.commit_string(key_char)
                                return True
                    #except:
                    #    if wbjj.options.debug:
                    #        raise
                    #        # import traceback
                    #        # traceback.print_exc()
                    
                    # 如果启用自动提交,且非拼音模式,且非数字,且已达最大码,且备选唯一,则提交
                    #print("DEBUG: in _table_mode_process_key_event() and self._cfg._stAutoCommit = " + str(self._cfg._stAutoCommit) + " and is_numeric = " + str(is_numeric) + " and self._editor._py_mode = " + str(self._editor._py_mode) + " and len(self._editor._chars[0]) = " + str(len(self._editor._chars[0])) + " and wbjj.wbMaxLength = " + str(wbjj.wbMaxLength))
                    if self._cfg._stAutoCommit and (not self._editor._py_mode) and (not is_numeric) and (len(self._editor._chars[0]) == wbjj.wbMaxLength) and self._editor.is_onlyone_candidate():
                        sp_res = self._editor.space()
                        if sp_res[0]:
                            self.commit_string(sp_res[1])
                            self.db.check_phrase(sp_res[1], sp_res[2])
                            return True
                    self._update_ui()
                    return True

                # 空格选字
                if key.code == IBus.space:
                    o_py = self._editor._py_mode
                    sp_res = self._editor.space()
                    if sp_res[0]:
                        self.commit_string(sp_res[1])
                        self.db.check_phrase(sp_res[1], sp_res[2] if sp_res[2] != u'z' else None)
                    elif sp_res[1] == u' ':
                        self.commit_string(cond_letter_translate(u" "))
                    if o_py != self._editor._py_mode:
                        self._refresh_properties()
                        self._update_ui()
                    return True

                # 数字键选字
                elif self._cfg._hkNumericKeySelection and key.code >= IBUS_0 and key.code <= IBUS_9 and self._editor._candidates:
                    if key.code == IBUS_0:
                        return self._select_number(9)
                    else:
                        return self._select_number(key.code - IBUS_1)
                
                # BackSpace键(删预编辑字符)
                elif key.code == IBus.BackSpace:
                    res = self._editor.backspace()
                    # 如果删空且在拼音模式,则退出
                    if self._editor.is_empty() and self._editor._py_mode:
                        res = self._editor.switch_py_wb()
                        self._refresh_properties()
                    self._update_ui()
                    return res

                # 回车键(直接上屏)
                elif key.code in (IBus.Return, IBus.KP_Enter):
                    commit_string = self._editor.get_all_input_strings()
                    self.commit_string(commit_string)
                    return True

                # Delete键
                elif key.code == IBus.Delete:
                    res = self._editor.delete()
                    # 如果删空且在拼音模式,则退出
                    if self._editor.is_empty() and self._editor._py_mode:
                        res = self._editor.switch_py_wb()
                        self._refresh_properties()
                    self._update_ui()
                    return res

                # Esc键(清空)
                elif key.code == IBus.Escape:
                    self.reset()
                    #self._update_ui()
                    return True

                # 翻页(处理所有翻页热键)
                elif key.code in self._cfg._hkPgDnList and self._editor._candidates:
                    if (key.code in (IBus.Down, IBus.KP_Down) and self._cfg._ltOrientation != 0) or (key.code in (IBus.Right, IBus.KP_Right) and self._cfg._ltOrientation == 0):
                        res = self._editor.cursor_down()
                    else:
                        res = self._editor.page_down()
                        #self._update_lookup_table()
                    self._update_ui()
                    return res
                elif key.code in self._cfg._hkPgUpList and self._editor._candidates:
                    if (key.code in (IBus.Up, IBus.KP_Up) and self._cfg._ltOrientation != 0) or (key.code in (IBus.Left, IBus.KP_Left) and self._cfg._ltOrientation == 0):
                        res = self._editor.cursor_down()
                    else:
                        res = self._editor.page_up()
                        #self._update_lookup_table()
                    self._update_ui()
                    return res

                # <;><'>快捷键选字支持
                elif self._cfg._hkSemicolonSelection and key.code in (IBus.semicolon, IBus.apostrophe):
                    if key.code == IBus.semicolon:
                        res = self._select_number(1)
                    else:
                        res = self._select_number(2)
                    return res

                # 方向键(需在翻页后处理)
                elif key.code in (IBus.Up, IBus.KP_Up):
                    res = self._editor.cursor_up()
                    self._update_ui()
                    return res
                elif key.code in (IBus.Down, IBus.KP_Down):
                    res = self._editor.cursor_down()
                    self._update_ui()
                    return res
                elif key.code in (IBus.Left, IBus.KP_Left):
                    res = self._editor.cursor_up()
                    self._update_ui()
                    return res
                elif key.code in (IBus.Right, IBus.KP_Right):
                    res = self._editor.cursor_down()
                    self._update_ui()
                    return res

                # 处理其他按键
                elif key.code <= 127:
                    if not self._editor._candidates:
                        commit_string = self._editor.get_all_input_strings()
                    else:
                        self._editor.commit_to_preedit()
                        commit_string = self._editor.get_preedit_strings()
                    self._editor.clear()
                    if ascii_ispunct(_keychar):
                        self.commit_string(commit_string + cond_punct_translate(_keychar))
                    else:
                        self.commit_string(commit_string + cond_letter_translate(_keychar))
                    return True
                # 全不匹配返回False
                return False

            # 造词模式
            else:
                # 加一个字<=>
                if key.code == IBus.equal:
                    #res = self._editor.create_update(len(self._editor.get_aux_strings())+1)
                    res = self._editor.create_update(len(self._editor.get_preedit_strings())+1)
                    if res:
                        self._create_update_ui()
                    return True
                # 去一个字<->
                elif key.code == IBus.minus:
                    #res = self._editor.create_update(len(self._editor.get_aux_strings())-1)
                    res = self._editor.create_update(len(self._editor.get_preedit_strings())-1)
                    if res:
                        self._create_update_ui()
                    return True
                # 确认加词<Space><Enter>
                elif key.code in (IBus.Return, IBus.KP_Enter, IBus.space):
                    res = self._editor.create_add(-1)
                    if res:
                        self._editor.clear()
                        self.reset()
                    return True
                # 数字键加词<1-9><0>
                elif key.code in (IBUS_1, IBUS_2, IBUS_3, IBUS_4, IBUS_5, IBUS_6, IBUS_7, IBUS_8, IBUS_9, IBUS_0):
                    if key.code == IBUS_0:
                        res = self._editor.create_add(9)
                    else:
                        res = self._editor.create_add(key.code - IBUS_1)
                    if res:
                        self._editor.clear()
                        self.reset()
                    return True
                # <;><'>快捷键加词(Shift_L加词在前面快捷键检测支持)
                elif self._cfg._hkSemicolonSelection and key.code in (IBus.semicolon, IBus.apostrophe):
                    if key.code == IBus.semicolon:
                        res = self._editor.create_add(1)
                    else:
                        res = self._editor.create_add(2)
                    if res:
                        self._editor.clear()
                        self.reset()
                    return True
                # Esc键
                elif key.code == IBus.Escape:
                    self._editor.clear()
                    self.reset()
                    return True
                # 退格删字
                elif key.code == IBus.BackSpace:
                    f = len(self._editor._word_history)         # 历史表长
                    l = len(self._editor.get_preedit_strings()) # 当前词长
                    self._editor.create_remove(f - l)           # 删光标位置前(当前词首字)
                    self._editor.create_update(l)
                    self._create_update_ui()
                    return True
                # Del删字
                elif key.code == IBus.Delete:
                    f = len(self._editor._word_history)         # 历史表长
                    l = len(self._editor.get_preedit_strings()) # 当前词长
                    self._editor.create_remove(f - l + 1)       # 删光标位置后(当前词第二字)
                    self._editor.create_update(l)
                    self._create_update_ui()
                    return True
                # 翻页(处理所有翻页热键)
                elif key.code in self._cfg._hkPgDnList and self._editor._candidates:
                    if (key.code in (IBus.Down, IBus.KP_Down) and self._cfg._ltOrientation != 0) or (key.code in (IBus.Right, IBus.KP_Right) and self._cfg._ltOrientation == 0):
                        res = self._editor.cursor_down()
                    else:
                        res = self._editor.page_down()
                        #self._update_lookup_table()
                    self._update_ui()
                    return res
                elif key.code in self._cfg._hkPgUpList and self._editor._candidates:
                    if (key.code in (IBus.Up, IBus.KP_Up) and self._cfg._ltOrientation != 0) or (key.code in (IBus.Left, IBus.KP_Left) and self._cfg._ltOrientation == 0):
                        res = self._editor.cursor_down()
                    else:
                        res = self._editor.page_up()
                        #self._update_lookup_table()
                    self._update_ui()
                    return res
                # 方向键(需在翻页后处理)
                elif key.code in (IBus.Up, IBus.KP_Up):
                    res = self._editor.cursor_up()
                    self._create_update_ui()
                    return True
                elif key.code in (IBus.Down, IBus.KP_Down):
                    res = self._editor.cursor_down()
                    self._create_update_ui()
                    return True
                elif key.code in (IBus.Left, IBus.KP_Left):
                    res = self._editor.cursor_up()
                    self._create_update_ui()
                    return True
                elif key.code in (IBus.Right, IBus.KP_Right):
                    res = self._editor.cursor_down()
                    self._create_update_ui()
                    return True
                # 其它所有情况
                else:
                    return True

        # Ctrl键盘事件(不带Alt键,可组合Shift)
        elif key.mask & IBus.ModifierType.CONTROL_MASK and not key.mask & IBus.ModifierType.MOD1_MASK:
            # 全/半角标点切换热键 Match full half punct mode switch hotkey
            if self._match_hotkey(key, IBus.period, IBus.ModifierType.CONTROL_MASK):
                self.do_property_activate(u"punct")
                return True

            # 单字模式切换热键(Ctrl+,)
            if self._match_hotkey(key, IBus.comma, IBus.ModifierType.CONTROL_MASK):
                self.do_property_activate(u"onechar")
                return True

            # 自动提交模式切换热键(Ctrl+/)
            if self._match_hotkey(key, IBus.slash, IBus.ModifierType.CONTROL_MASK):
                self.do_property_activate(u"acommit")
                return True
        
            # 中文数字模式切换热键(Ctrl+')
            if self._match_hotkey(key, IBus.apostrophe, IBus.ModifierType.CONTROL_MASK):
                self.do_property_activate(u"cndigital")
                return True
        
            # 字符集切换(Ctrl+;)
            if self._match_hotkey(key, IBus.semicolon, IBus.ModifierType.CONTROL_MASK):
                self.do_property_activate(u"cmode")
                return True
        
            # 进入时实造词状态(Ctrl+=) 前预编辑入栈
            if self._match_hotkey(key, IBus.equal, IBus.ModifierType.CONTROL_MASK):
                # if self._editor._create_mode:
                #     return True
                self._editor._create_mode = True
                res = self._editor.create_update(2)
                if res:
                    self._create_update_ui()
                else:
                    self._editor.clear()
                return res
            
            # Ctrl+←, 什么作用?
            elif key.code in (IBus.Left, IBus.KP_Left) and key.mask & IBus.ModifierType.CONTROL_MASK:
                res = self._editor.control_arrow_left()
                self._update_ui()
                return res

            # Ctrl+→, 什么作用?
            elif key.code in (IBus.Right, IBus.KP_Right) and key.mask & IBus.ModifierType.CONTROL_MASK:
                res = self._editor.control_arrow_right()
                self._update_ui()
                return res

            # Ctrl+Backspace, 什么作用?
            elif key.code == IBus.BackSpace and key.mask & IBus.ModifierType.CONTROL_MASK:
                res = self._editor.control_backspace()
                self._update_ui()
                return res
            
            # Ctrl+Delete, 什么作用?
            elif key.code == IBus.Delete  and key.mask & IBus.ModifierType.CONTROL_MASK:
                res = self._editor.control_delete()
                self._update_ui()
                return res
        
            # Ctrl+数字键且有备选项, 与数字键选择备选功能相同,可用于无法使用数字备选的情况,或用于未启用数字备选时
            elif key.code >= IBUS_0 and key.code <= IBUS_9 and self._editor._candidates and key.mask & IBus.ModifierType.CONTROL_MASK:
                if key.code == IBUS_0:
                    return self._select_number(9)
                else:
                    return self._select_number(key.code - IBUS_1)

        # Alt键盘事件(不带Ctrl键,可组合Shift)
        elif key.mask & IBus.ModifierType.MOD1_MASK and not key.mask & IBus.ModifierType.CONTROL_MASK:
            # Alt+数字(删词快捷键)
            if key.code >= IBUS_1 and key.code <= IBUS_9 and self._editor._candidates and key.mask & IBus.ModifierType.MOD1_MASK:
                res = self._editor.alt_number(key.code - IBUS_1)
                self._update_ui()
                return res

        # Ctrl+Alt组合(可组合Shift)或其它
        else:
            pass

    def _english_mode_process_key_event(self, key):
        '''英文模式键盘事件处理过程'''
        return False
        #if key.mask & IBus.ModifierType.RELEASE_MASK:
        if key.mask & IBus.ModifyerType.RELEASE_MASK and key.code < 128:
            return True
        if key.code >= 128:
            return False
        if key.mask & (IBus.ModifierType.CONTROL_MASK | IBus.ModifierType.MOD1_MASK):
            return False
        #return False
        return True
    
    def do_page_up(self):
        '''LookupTable翻页按钮(前一页)事件响应过程[事件接口]'''
        res = self._editor.page_up()
        self._update_ui()

    def do_page_down(self):
        '''LookupTable翻页按钮(下一页)事件响应过程[事件接口]'''
        res = self._editor.page_down()
        self._update_ui()

    def do_candidate_clicked(self, index, button, state):
        '''LookupTable备选项单击事件响应过程[事件接口]'''
        if button == 1 and self._editor._candidates:
            return self._select_number(index)

    def _select_number(self, number):
        '''通过数字键或快捷键选字'''
        input_keys = self._editor.get_all_input_strings()
        res = self._editor.number(number)
        if res:
            o_py = self._editor._py_mode
            commit_string = self._editor.get_preedit_strings()
            self.commit_string(commit_string)
            if o_py != self._editor._py_mode:
                self._refresh_properties()
                self._update_ui()
            self.db.check_phrase(commit_string, input_keys)
        return True

    def do_focus_in(self):
        '''IBus.Engine[Signals]绑定的事件'''
        if self._on:
            self.register_properties(self.properties)
            self._refresh_properties()
            self._update_ui()
    
    def do_focus_out(self):
        pass

    def do_set_content_type(self, purpose, hints):
        pass

    def do_enable(self):
        self._on = True
        self.do_focus_in()

    def do_disable(self):
        self.reset()
        self._on = False

