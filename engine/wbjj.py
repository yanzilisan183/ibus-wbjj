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
from locale import getdefaultlocale
from gi import require_version
require_version('IBus', '1.0')
from gi.repository import IBus


sysname       = "ibus-wbjj"
version       = "0.3.42"
date          = "20220922"
requestpath   = "org.freedesktop.IBus.ibus-wbjj"
section       = 'engine/wbjj'

language      = "zh"
layout        = "us"
license       = "LGPL"
symbol        = u"五"
author        = u"LI Yunfei <yanzilisan183@sina.com>"
homepage      = u"https://github.com/yanzilisan183/ibus-wbjj/"
description   = u'IBus框架下的五笔输入法\n基于ibus-table和极点五笔86修改\n\n感谢:\n  　ibus-table 作者: Wozy <wozy.in@gmail.com>\n  　五笔加加Plus(Windows版)作者: Easycode <easycode@freemail.sx.cn>\n  　五笔加加之父: 北京六合源软件技术有限公司\n\n我是小三,Ubuntu爱好者,python初学者.'
description_short = u'IBus框架下的五笔输入法,基于ibus-table和极点五笔86修改'

path          = os.path.expanduser('/usr/share/ibus-wbjj/')
user          = os.path.expanduser('~/.local/share/ibus-wbjj/')
lib           = os.path.expanduser('/usr/lib/ibus/')
setup         = lib + 'ibus-wbjj-setup'

iconpath      = path + 'icons/'
iconname      = 'wbjjplus_1.svg'
icon          = iconpath + iconname
trayicon      = iconpath + 'wbjjplus_1.svg'

docpath       = path + 'docs/'
enginepath    = path + 'engine/'
datapath      = path + 'data/'
help          = docpath + 'help_Tips.htm'

dbpath        = path + 'tables/'
dbname        = 'wbjjplus3.db'
db            = dbpath + dbname

userdbpath    = user
userdbname    = 'wbjjplus3-user.db'
userdb        = userdbpath + userdbname

logpath       = os.path.expanduser('~/.cache/ibus-wbjj/')
logname       = 'debug.log'
log           = logpath + logname

dbversion     = '3.0'
dbfields      = ['id','clen','code','wlen','word','category','code2','freq','user_freq']
idx_id        = dbfields.index('id')
idx_clen      = dbfields.index('clen')
idx_code      = dbfields.index('code')
idx_wlen      = dbfields.index('wlen')
idx_word      = dbfields.index('word')
idx_cate      = dbfields.index('category')
idx_cod2      = dbfields.index('code2')
idx_freq      = dbfields.index('freq')
idx_ureq      = dbfields.index('user_freq')

candfields    = ('code', 'word', 'category', 'code2', 'freq', 'user_freq')
candidx_code  = candfields.index('code')
candidx_word  = candfields.index('word')
candidx_cate  = candfields.index('category')
candidx_cod2  = candfields.index('code2')
candidx_freq  = candfields.index('freq')
candidx_ureq  = candfields.index('user_freq')

allValidChar  = "abcdefghijklmnopqrstuvwxyz!@#$%"           # 所有编码使用到的字符(不含中文数字字符)
wbValidChar   = "abcdefghijklmnopqrstuvwxy"                 # 五笔编码使用的字符
pyValidChar   = "abcdefghijklmnopqrstuvwxyz!@#$%"           # 拼音编码使用的字符
numValidChar  = "1234567890.-/"                             # 中文数字使用的字符,其中-/为日期分隔符
wbMaxLength   = 4                                           # 五笔最大编码长度
pyMaxLength   = 16                                          # 拼音最大编码长度
historywords  = 32                                          # 
ltOrientationEnum =  {0:'水平', 1:'竖直', 2:'系统默认'}
ltOrientationEnumRev = {value:key for key, value in ltOrientationEnum.items()}
stChineseModeEnum =  {0:'简体', 1:'繁体', 2:'简体优先的大字符集', 3:'繁体优先的大字符集', 4:'大字符集'}
stChineseModeEnumRev = {value:key for key, value in stChineseModeEnum.items()}
hkEnSwitchKeyEnumRev =  {'左Ctrl键':[IBus.Control_L], 
                         '右Ctrl键':[IBus.Control_R], 
                         'Ctrl键':[IBus.Control_L, IBus.Control_R], 
                         '左Shift键':[IBus.Shift_L], 
                         '右Shift键':[IBus.Shift_R], 
                         'Shift键':[IBus.Shift_L, IBus.Shift_R], 
                         '禁用':[]}


global options

def name():
    sname = {'zh_CN':u"五笔加加Plus", 'zh_SG':u"五笔加加Plus", 'zh_TW':u"五筆加加Plus", 'zh_HK':u"五筆加加Plus"}
    locale = getdefaultlocale()[0]
    try:
        return sname[locale]
    except:
        return sname['zh_CN']

def longname():
    lname = {'zh_CN':u"五笔加加Plus For IBus", 'zh_SG':u"五笔加加Plus For IBus", 'zh_TW':u"五筆加加Plus For IBus", 'zh_HK':u"五筆加加Plus For IBus"}
    locale = getdefaultlocale()[0]
    try:
        return lname[locale]
    except:
        return lname['zh_CN']

def get_txtfile_words(wordfile, freq=-6, user_freq=1):
    try:
        usrwordfile = os.path.expanduser(wordfile)
        f = open(usrwordfile, "r")
        lines = f.readlines()
        f.close()
    except:
        print("ERROR: Failed to read file " + wordfile + ".")
        return [[],[],[]]
    lines = list(filter(lambda x: x.find('=')>0 and x.strip()[0:1] not in [';','#','['], lines))    # 过滤无效行和注释行
    lines = list(filter(lambda x: x[0] != '' and x[1] != '', lines))                                # 过滤无效字符和空值
    RecordTupleList = []
    for line in lines:
        _tmplst = list(map(lambda x:x.strip(), line.split('=',1)))
        if _tmplst[0][-2:] == '[]' and _tmplst[1].find(',') > 0:
            _vallst = list(map(lambda x:x.strip(), _tmplst[1].split(',')))
            _ufreq = len(_vallst) * 10      # (user_freq递减变量初始值)按差值10累计user_freq,以便有限的保存原始序列中的顺序
            for value in _vallst:
                RecordTupleList.append(tuple([None, len(str(_tmplst[0][:-2]).strip()), str(_tmplst[0][:-2]).strip(), len(value), value.strip(), 3, '', freq, user_freq + _ufreq]))
                _ufreq -= 10
        else:
            RecordTupleList.append(tuple([None, len(_tmplst[0]), _tmplst[0], len(_tmplst[1]), _tmplst[1], 3, '', freq, user_freq]))
    #print("DEBUG: in get_txtfile_words() and RecordTupleList = " + str(RecordTupleList))
    formated = [[],[],[]]
    formated[0] = list(map(lambda y: tuple(y), filter(lambda x: x[2][0] != 'z', RecordTupleList)))  # 提取五笔表数据
    formated[1] = list(map(lambda y: tuple([y[0]] + [int(y[1]) - 1] + [y[2][1:]] + list(y[3:])), filter(lambda x: x[2][0] == 'z', RecordTupleList))) # 提取拼音表数据(code去引导字符z,clen长度减1)
    formated[2] = []
    return formated[:]

def get_category(phrase):
    # 使用三位掩码,低位为简体,中位为繁体,高位为超出GBK范围
    category = 0
    # 首先验证是否简体(GB2312)
    try:
        phrase.encode('gb2312')
        category |= 1
    except:
        if '〇'.encode('utf-8').decode('utf-8') in phrase:  # we add '〇' into SC as well
            category |= 1
    # 然后验证是否繁体(Big5-hkscs)
    try:
        phrase.encode('big5hkscs')
        category |= 1 << 1
    except:
        # 如果也不是简体
        if not (category & 1):
            # 最后验证是否GBK
            try:
                phrase.encode('gbk')
                category |= 1
            except:
                pass
    # 如果非简体和繁体,设高位为1
    if not (category & (1 | 1 << 1)):
        category |= (1 << 2)
    return category

def check_dir():
    #print("DEBUG: in check_dir()")
    os.path.exists(user) or os.makedirs(user)
    os.path.exists(userdbpath) or os.makedirs(userdbpath)
    os.path.exists(logpath) or os.makedirs(logpath)


