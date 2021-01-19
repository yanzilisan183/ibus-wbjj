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
import os.path as path
import sys
import sqlite3
import tabdict
import uuid
import time
import re
import wbjj


# 表结构: 'id','clen','code','wlen','word','category','code2','freq','user_freq'
# candidate结构: ('code', 'word', category, 'code2', freq, user_freq)

# 关于 main, user_db, memu_db
# 关于freq与user_freq
# main.table.freq           (只读)基础字频, 不随用户字频变化, 但随主码表更新变化
# main.table.user_freq      (只读)总是为0
# user_db.table.freq        [0,-1], 0:main原有词; -1:用户自造词; -6:来自于TXT码表;
# user_db.table.user_freq   用户字频(已保存的字频)
# memu_db.table.freq        [-6,-3,-2,1,2], 不会出现0和-1(user_db表用), -6:来自于TXT码表; -3:; -2:用户自造词(对应user_db的-1); 1:; 2:;
# memu_db.table.user_freq   待保存到用户表中的字频
# UNION ALL查询时
#   user_freq==0                            记录来自于main
#   user_freq!=0 and freq in [0,-1]         记录来自于user_db
#   user_freq!=0 and not(freq in [0,-1])    记录来自于memu_db
# category:                 0:错误; 1:简体; 2:繁体; 3:简繁共用; 4:超出GBK范围

class TabSqliteDb:
    '''Phrase database for tables'''
    def __init__(self, name='wbjjplus3.db', user_db=None, filename=None):
        # use filename when you are creating db from source
        # use name when you are using db
        self._cfg = None                                    # 由IMEConfig对象写入,此处仅声明
        if filename:
            self.db = sqlite3.connect(filename)             # 创建指定的数据库
        else:
            try:
                os.system('cat %s > /dev/null' % name)
            except:
                pass
            self.db = sqlite3.connect(name)                 # 使用系统数据库
        try:
            self.db.execute('PRAGMA page_size = 8192;')
            self.db.execute('PRAGMA cache_size = 20000;')   # 加大缓存以提速
            self.db.execute('PRAGMA temp_store = MEMORY;')
            self.db.execute('PRAGMA synchronous = OFF;')
        except:
            if wbjj.options.debug:
                raise
            print('初始化数据库时遇到错误')
            pass

        if filename:  # 如果是新建数据库,跳过后面创建user_db和memu_db的过程
            return
        
        # user database:
        if user_db == None:
            user_db = ":memory:"
        else:
            user_db = wbjj.userdb
            try:
                desc = self.get_database_desc(user_db)
                if desc == None:
                    self.init_user_db(user_db)
                elif desc["version"] != wbjj.dbversion or (not self.fields_alike(user_db, 'wubi3')) or (not self.fields_alike(user_db, 'pinyin3')):
                    os.rename(user_db, "%s.%d" %(user_db, os.getpid()))
                    print("Can not support the user db. We will rename it.", file=sys.stderr)
                    self.init_user_db(user_db)
            except:
                import traceback
                traceback.print_exc()
        
        # open user phrase database
        try:
            self.db.execute('ATTACH DATABASE "%s" AS user_db;' % user_db)
        except:
            print("The user database was damaged. We will recreate it!", file=sys.stderr)
            os.rename(user_db, "%s.%d" % (user_db, os.getpid()))
            self.init_user_db(user_db)
            self.db.execute('ATTACH DATABASE "%s" AS user_db;' % user_db)
        self.create_tables("user_db")
        self.create_indexes("user_db", commit=False)
        self.set_database_desc()
        memu_db = ":memory:"  
        self.db.execute('ATTACH DATABASE "%s" AS memu_db;' % memu_db)
        self.create_tables("memu_db")

    def select_wubi(self, code_str, onechar=False, bitmask=0):
        '''从数据库[wubiN]表检索字词,如果非onechar模式,则会返回更多可能的结果'''
        _code_len = len(code_str)
        _sqlsub = ' AND code LIKE \'' + code_str + '%\''
        if onechar:
            _sqlsub += ' AND wlen = 1'
        if bitmask:
            _sqlsub += ' AND (' + ' OR '.join(map(lambda x: 'category = %d' % x, filter(lambda x: x & bitmask, range(1,5)))) + ')'
        CandidateTupleList = []
        _more_len = 1   # 预查编码长度,从1开始递增到最大编码长度,直到返回结果
        while _code_len + _more_len <= wbjj.wbMaxLength + 1:
            sqlstr = '''SELECT code, word, category, code2, freq, user_freq FROM (SELECT * FROM main.wubi3 WHERE clen <= %(clen)d%(sqlsub)s
                             UNION ALL SELECT * FROM user_db.wubi3 WHERE clen <= %(clen)d%(sqlsub)s
                             UNION ALL SELECT * FROM memu_db.wubi3 WHERE clen <= %(clen)d%(sqlsub)s
                        ) ORDER BY clen ASC, user_freq DESC, freq DESC, id ASC;''' % {'clen':_code_len + _more_len, 'sqlsub':_sqlsub}
            CandidateTupleList = CandidateTupleList + self.db.execute(sqlstr).fetchall()
            if len(CandidateTupleList) >= self._cfg._ltPageSize:
                break
            else:
                _more_len += 1
        if len(CandidateTupleList) <= 0:
            return []
        # 字频合并(重码累加字频,保留短code和字频)
        wordlist = []        # wordlist格式["codeA", "wordA", categoryA, "code2A", freqA, user_freqA, "codeB", "wordB", categoryB, "code2B", freqB, user_freqB]
        for o in CandidateTupleList:
            word = o[wbjj.candidx_word]
            code = o[wbjj.candidx_code]
            if word in wordlist:
                code_idx = wordlist.index(word) - 1
                if wordlist[code_idx] == code:                                 # 同码字累加字频
                    wordlist[code_idx + wbjj.candidx_freq] += o[wbjj.candidx_freq]
                    wordlist[code_idx + wbjj.candidx_ureq] += o[wbjj.candidx_ureq]
                elif len(wordlist[code_idx]) > len(code):                      # 保留短code
                    wordlist[code_idx] = code
                    wordlist[code_idx + wbjj.candidx_freq] = o[wbjj.candidx_freq]
                    wordlist[code_idx + wbjj.candidx_ureq] = o[wbjj.candidx_ureq]
            else:                                                              # 追加字到列表
                wordlist += list(o[:])
        i = 0
        l = len(wordlist)
        ll = len(wbjj.candfields)
        CandidateTupleList = []
        while i < l:
            CandidateTupleList.append(tuple(wordlist[i:i+ll]))
            i += ll
        # print("DEBUG: select_wubi.CandidateTupleList = " + str(CandidateTupleList))
        return CandidateTupleList

    def select_pinyin(self, code_str, onechar=False, bitmask=0):
        '''从数据库[pinyinN]表检索字词,如果非onechar模式,则会返回更多可能的结果'''
        def fuzzy_tone(codelist, idx, codestr):
            nonlocal _complist
            if idx == len(codelist):
                _complist.append(codestr)
                return
            for n in range(len(codelist[idx])):
                fuzzy_tone(codelist, idx + 1, codestr + codelist[idx][n])
                
        code_str = code_str[1:]     # 去除引导字符z
        _FuzzyTone = self._cfg._stpyFuzzyTone and ('z' in code_str or 'c' in code_str or 's' in code_str)
        _sqlcode = ''
        if _FuzzyTone:
            # 排列组合
            _codelist = code_str.replace('zh','z').replace('ch','c').replace('sh','s').replace('z',' z ').replace('c',' c ').replace('s',' s ').split()
            # 将一维List变二维List
            for n in range(len(_codelist)):
                if _codelist[n] in ['z','c','s']:
                    _codelist[n] = [_codelist[n], _codelist[n]+'h']
                else:
                    _codelist[n] = [_codelist[n]]
            # 排列组合
            _complist = []
            _t = fuzzy_tone(_codelist, 0, '')
            for code_str in _complist:
                _code_len = len(code_str)
                _sqlcode = _sqlcode + ('' if _sqlcode == '' else ' OR ') + str('(clen <= %(clen)d+%%(mlen)d AND code LIKE \'' + code_str + '~\')') % {'clen':_code_len}
        else:
            _code_len = len(code_str)
            _sqlcode = ' AND code LIKE \'' + code_str + '~\''
        _sqlother = ''
        if onechar:
            _sqlother += ' AND wlen = 1'
        if bitmask:
            _sqlother += ' AND (' + ' OR '.join(map(lambda x: 'category = %d' % x, filter(lambda x: x & bitmask, range(1,5)))) + ')'
        CandidateTupleList = []
        _more_len = 1   # 预查编码长度,从1开始递增到最大编码长度,直到返回结果
        while _code_len + _more_len <= wbjj.pyMaxLength + 1:
            if _FuzzyTone:
                sqlstr = '''SELECT code, word, category, code2, freq, user_freq FROM (SELECT * FROM main.pinyin3 WHERE (%(sqlcode)s)%(sqlother)s
                                UNION ALL SELECT * FROM user_db.pinyin3 WHERE (%(sqlcode)s)%(sqlother)s
                                UNION ALL SELECT * FROM memu_db.pinyin3 WHERE (%(sqlcode)s)%(sqlother)s
                            ) ORDER BY clen ASC, user_freq DESC, freq DESC, id ASC;''' % {'sqlcode':_sqlcode % {'mlen':_more_len}, 'sqlother':_sqlother}
            else:
                sqlstr = '''SELECT code, word, category, code2, freq, user_freq FROM (SELECT * FROM main.pinyin3 WHERE clen <= %(cmlen)d%(sqlcode)s%(sqlother)s
                                UNION ALL SELECT * FROM user_db.pinyin3 WHERE clen <= %(cmlen)d%(sqlcode)s%(sqlother)s
                                UNION ALL SELECT * FROM memu_db.pinyin3 WHERE clen <= %(cmlen)d%(sqlcode)s%(sqlother)s
                            ) ORDER BY clen ASC, user_freq DESC, freq DESC, id ASC;''' % {'cmlen':_code_len + _more_len, 'sqlcode':_sqlcode, 'sqlother':_sqlother}
            sqlstr = sqlstr.replace('~','%')    # 为防止SQL通配符(%)与格式化字符(%)二义,前面使用~作为%的代用符,在此转换回%
            CandidateTupleList = CandidateTupleList + self.db.execute(sqlstr).fetchall()
            if len(CandidateTupleList) >= self._cfg._ltPageSize:
                break
            else:
                _more_len += 1
        print("DEBUG: in select_pinyin() and CandidateTupleList = " + str(CandidateTupleList))
        if len(CandidateTupleList) <= 0:
            return []
        # 字频合并(重码累加字频,保留短code和字频)
        wordlist = []        # wordlist格式["codeA", "wordA", categoryA, "code2A", freqA, user_freqA, "codeB", "wordB", categoryB, "code2B", freqB, user_freqB]
        for o in CandidateTupleList:
            word = o[wbjj.candidx_word]
            code = o[wbjj.candidx_code]
            if word in wordlist:
                code_idx = wordlist.index(word) - 1
                if wordlist[code_idx] == code:                                 # 同码字累加字频
                    wordlist[code_idx + wbjj.candidx_freq] += o[wbjj.candidx_freq]
                    wordlist[code_idx + wbjj.candidx_ureq] += o[wbjj.candidx_ureq]
                elif self._pinyin_remove_tone(wordlist[code_idx]) == self._pinyin_remove_tone(code):    # 同音异调合并累加字频
                    wordlist[code_idx] = code
                    wordlist[code_idx + wbjj.candidx_freq] = o[wbjj.candidx_freq]
                    wordlist[code_idx + wbjj.candidx_ureq] = o[wbjj.candidx_ureq]
            else:                                                              # 追加字到列表
                wordlist += list(o[:])
        i = 0
        l = len(wordlist)
        ll = len(wbjj.candfields)
        CandidateTupleList = []
        while i < l:
            if self._cfg._stpyRequery and wordlist[i+wbjj.candidx_cod2] != '':
                # 拼音编码后追加<五笔编码>(仅提取第一个编码,通常为最简码)
                wordlist[i+wbjj.candidx_code] = wordlist[i+wbjj.candidx_code] + ' <' + wordlist[i+wbjj.candidx_cod2].split(',')[0] + '>'
            CandidateTupleList.append(tuple(wordlist[i:i+ll]))
            i += ll
        # print("DEBUG: select_pinyin.CandidateTupleList = " + str(CandidateTupleList))
        return CandidateTupleList

    def get_wubi_code(self, word):
        '''反查单字五笔编码(多码时仅返回最简码)'''
        sqlstr = '''SELECT DISTINCT clen, code FROM (
            SELECT * FROM main.wubi3 WHERE wlen = 1 AND word = ?
            UNION ALL SELECT * FROM user_db.wubi3 WHERE wlen = 1 AND word = ?
            UNION ALL SELECT * FROM memu_db.wubi3 WHERE wlen = 1 AND word = ?
        ) ORDER BY clen DESC LIMIT 1 OFFSET 0;'''
        res = self.db.execute(sqlstr, (word,word,word)).fetchall()
        if len(res) < 1:
            code = '?'
        else:
            code = res[0][1]
        return code

    def get_pinyin_code(self, word):
        '''反查单字拼音(已转音调)(多码全部返回)'''
        sqlstr = '''SELECT DISTINCT clen, code FROM (
            SELECT * FROM main.pinyin3 WHERE wlen = 1 AND word = ?
            UNION ALL SELECT * FROM user_db.pinyin3 WHERE wlen = 1 AND word = ?
            UNION ALL SELECT * FROM memu_db.pinyin3 WHERE wlen = 1 AND word = ?
        ) ORDER BY clen DESC'''
        res = self.db.execute(sqlstr, (word,word,word)).fetchall()
        if len(res) < 1:
            code = '?'
        elif len(res) == 1:
            code = self._pinyin_remove_tone(res[0][1])
        else:
            # 去除音调后去重,可过滤同音不同调的重码
            _list = []
            for _item in res:
                _one_code = self._pinyin_remove_tone(_item[1])
                if _one_code not in _list:
                    _list.append(_one_code)
            code = ','.join(_list)
        return code

    def set_new_word(self, word, code, code2, table):
        '''保存用户造词'''
        clen = len(code)
        wlen = len(word)
        category = wbjj.get_category(word)
        sqlstr = '''SELECT * FROM (SELECT * FROM user_db.%(table)s WHERE word = ?
                         UNION ALL SELECT * FROM memu_db.%(table)s WHERE word = ?
                    ) ORDER BY clen DESC''' % {'table':table}
        RecordTupleList = self.db.execute(sqlstr, (word,word)).fetchall()
        for x in RecordTupleList:
            if x[wbjj.idx_clen] == clen and x[wbjj.idx_cate] == category:
                return True
        record = [None] * len(wbjj.dbfields)
        record[wbjj.idx_id] = None
        record[wbjj.idx_clen] = clen
        record[wbjj.idx_code] = code
        record[wbjj.idx_wlen] = wlen
        record[wbjj.idx_word] = word
        record[wbjj.idx_cate] = category
        record[wbjj.idx_cod2] = code2
        record[wbjj.idx_freq] = -1          # 用户自造词在user_db.freq中值为-1
        record[wbjj.idx_ureq] = 0
        sqlstr = 'INSERT INTO user_db.%(table)s (' + ', '.join(wbjj.dbfields) + ') VALUES (' + ', '.join(['?']*len(wbjj.dbfields)) + ');'
        self.db.execute(sqlstr % {'table':table}, record)
        return True

    def update_phrase(self, inRecordTupleList, table='wubi3'):
        '''更新用户频次(仅由sync_usrdb过程调用)'''
        sqllist = [inRecordTupleList[wbjj.idx_ureq]] + \
                  [inRecordTupleList[wbjj.idx_clen]] + \
                  [inRecordTupleList[wbjj.idx_code]] + \
                  [inRecordTupleList[wbjj.idx_wlen]] + \
                  [inRecordTupleList[wbjj.idx_word]] + \
                  [inRecordTupleList[wbjj.idx_cate]]
        sqlstr = 'UPDATE user_db.%(table)s SET user_freq = ? WHERE clen = ? AND code = ? AND wlen = ? AND word = ? AND category = ?;' % {'table':table}
        self.db.execute(sqlstr, sqllist)
        self.db.commit()

    def add_phrase(self, inRecordTuple, database='main', commit=True, table='wubi3'):
        '''添词到指定表(非造词过程)'''
        if len(inRecordTuple) == 0:
            return
        try:
            sqlstr = 'SELECT * FROM %(database)s.%(table)s WHERE code = ? AND word = ?;'
            RecordTupleList = self.db.execute(sqlstr % {'database':database, 'table':table}, [inRecordTuple[wbjj.idx_code],inRecordTuple[wbjj.idx_word]]).fetchall()
            #print("DEBUG: add_phrase() and RecordTupleList = " + str(RecordTupleList))
            if len(RecordTupleList) > 0:
                if inRecordTuple[wbjj.idx_ureq] > RecordTupleList[0][wbjj.idx_ureq] and inRecordTuple[wbjj.idx_ureq] > 0:
                    sqlstr = 'UPDATE %(database)s.%(table)s SET user_freq = ? WHERE id = ?;'
                    #print("DEBUG: add_phrase() to <" + database + "> and [update]sqlstr = " + sqlstr % {'database':database, 'table':table} + ", parameter = " + str([inRecordTuple[wbjj.idx_ureq],RecordTupleList[0][wbjj.idx_id]]))
                    self.db.execute(sqlstr % {'database':database, 'table':table}, [inRecordTuple[wbjj.idx_ureq],RecordTupleList[0][wbjj.idx_id]])
                else:
                    # print("DEBUG: add_phrase() and return")
                    return
            else:
                sqlstr = 'INSERT INTO %(database)s.%(table)s (' + ', '.join(wbjj.dbfields) + ') VALUES (' + ', '.join(['?']*len(wbjj.dbfields)) + ');'
                #print("DEBUG: add_phrase() to <" + database + "> and [insert]sqlstr = " + sqlstr % {'database':database, 'table':table} + ", parameter = " + str([None] + list(inRecordTuple[1:])))
                self.db.execute(sqlstr % {'database':database, 'table':table}, [None] + list(inRecordTuple[1:]))
            if commit:
                self.db.commit()
        except Exception:
            import traceback
            traceback.print_exc()

    def check_phrase(self, word, code_str=None, database='main'):
        '''检查freq和user_freq,更新词频计数'''
        # 未启用调频则退出
        if not self._cfg._stDynamicAdjust:
            return
        else:
            # print("DEBUG: check_phrase() word = " + str(word) + ", code_str = " + str(code_str) + ", database = " + str(database))
            if type(word) != type(u''):
                word = word.decode('utf8')
            if word in tabdict.chinese_nocheck_chars:
                return
            if (not code_str) or len(code_str) > wbjj.wbMaxLength:
                sqlstr = '''SELECT * FROM (SELECT * FROM main.wubi3 WHERE word = ? 
                                 UNION ALL SELECT * FROM user_db.wubi3 WHERE word = ? 
                                 UNION ALL SELECT * FROM memu_db.wubi3 WHERE word = ?
                            ) ORDER BY user_freq DESC, freq DESC, id ASC;'''
                RecordTupleList = self.db.execute(sqlstr, (word,word,word)).fetchall()
            else:
                sqlstr = '''SELECT * FROM (SELECT * FROM main.wubi3 WHERE word = ? AND code = ?
                                 UNION ALL SELECT * FROM user_db.wubi3 WHERE word = ? AND code = ?
                                 UNION ALL SELECT * FROM memu_db.wubi3 WHERE word = ? AND code = ?
                            ) ORDER BY user_freq DESC, freq DESC, id ASC;'''
                RecordTupleList = self.db.execute(sqlstr, ((word,code_str)*3)).fetchall()
                if not bool(RecordTupleList):
                    sqlstr = '''SELECT * FROM (SELECT * FROM main.wubi3 WHERE word = ?
                                     UNION ALL SELECT * FROM user_db.wubi3 WHERE word = ?
                                     UNION ALL SELECT * FROM memu_db.wubi3 WHERE word = ?
                                ) ORDER BY user_freq DESC, freq DESC, id ASC;'''
                    RecordTupleList = self.db.execute(sqlstr, (word,word,word)).fetchall()
            if len(RecordTupleList) <= 0:
                return
            maindbSet = set()
            userdbSet = set()
            memudbSet = set()
            # RecordTupleList = [(id, clen, 'code', wlen, 'word', category, 'code2', freq, user_freq),(...)]
            # 如果user_freq为0,添加到maindbSet
            reslist = list(filter(lambda x: not x[wbjj.idx_ureq], RecordTupleList))
            # print("DEBUG: check_phrase() C, reslist = " + str(list(reslist)))
            for x in reslist:
                maindbSet.update((x,))
            # 如果freq为0或-1并且user_freq不为0,添加到userdbSet
            reslist = list(filter(lambda x: x[wbjj.idx_freq] in [0,-1] and x[wbjj.idx_ureq], RecordTupleList))
            # print("DEBUG: check_phrase() D, reslist = " + str(list(reslist)))
            for x in reslist:
                userdbSet.update((x,))
            # 如果freq不为0或-1并且user_freq不为0,添加到memudbSet
            reslist = list(filter(lambda x: not (x[wbjj.idx_freq] in [0,-1]) and x[wbjj.idx_ureq], RecordTupleList))
            # print("DEBUG: check_phrase() E, reslist = " + str(list(reslist)))
            for x in reslist:
                memudbSet.update((x,))

            #try:
            if 1==1:
                # print("DEBUG: check_phrase() maindbSet = " + str(maindbSet) + ", userdbSet = " + str(userdbSet) + ", memudbSet = " + str(memudbSet))
                keyout = list(filter(lambda k,memudbSet=memudbSet: k in memudbSet, userdbSet))     # 从userdbSet中删除包含在memudbSet的键
                for x in keyout:
                    try:
                        userdbSet.remove(x)
                    except:
                        pass
                # print("DEBUG: check_phrase() userdbSet = " + str(userdbSet))
                keyout = list(filter(lambda k,memudbSet=memudbSet,userdbSet=userdbSet: k in memudbSet or k in userdbSet, maindbSet))  # 从maindbSet删除包含在memudbSet和userdbSet的项
                for x in keyout:
                    try:
                        maindbSet.remove(x)
                    except:
                        pass
                # print("DEBUG: check_phrase() maindbSet = " + str(maindbSet))
                sqlstr = 'UPDATE memu_db.wubi3 SET user_freq = ? WHERE clen = ? AND code = ? AND wlen = ? AND word = ? AND category = ?;'
                for x in memudbSet:
                    self.db.execute(sqlstr, [x[wbjj.idx_ureq]+1] + list(x[1:6]))
                self.db.commit()
                if userdbSet and len(word) == 1:                # 单字
                    for x in userdbSet:
                        self.add_phrase(tuple(list(x[:7]) + [1, x[wbjj.idx_ureq]+1]), database='memu_db')
                elif userdbSet and len(RecordTupleList) > 0:    # 词组
                    for x in userdbSet:
                        self.add_phrase(tuple(list(x[:7]) + [(-3 if x[wbjj.idx_freq] == -1 else 1), x[wbjj.idx_ureq]+1]), database='memu_db')
                for x in maindbSet:
                    self.add_phrase(tuple(list(x[:7]) + [2, 1]), database='memu_db')
            #except:
            #    import traceback
            #    traceback.print_exc()

    def load_user_words(self, wordfile):
        '''加载用户自定义码表'''
        _RecordTupleList = wbjj.get_txtfile_words(wordfile, -6, 1)
        if not _RecordTupleList:
            return
        self.db.execute("DELETE FROM memu_db.wubi3 WHERE freq = -6;")
        self.db.execute("DELETE FROM memu_db.pinyin3 WHERE freq = -6;")
        for _RecordTuple in _RecordTupleList[0]:
            self.add_phrase(_RecordTuple, 'memu_db', False, 'wubi3')
        for _RecordTuple in _RecordTupleList[1]:
            self.add_phrase(_RecordTuple, 'memu_db', False, 'pinyin3')
        self.db.commit()

    def sync_usrdb(self):
        '''将内存表同步到用户码表'''
        RecordTupleList = self.db.execute('SELECT * FROM memu_db.wubi3;').fetchall()
        # 同步词频
        freqSyncTupleList = filter(lambda x: x[wbjj.idx_freq] in [1,-3], RecordTupleList)
        map(self.update_phrase, freqSyncTupleList)
        # 同步字词到user_db
        for x in RecordTupleList:
            # 同步原码表已有词(freq==2)
            if x[wbjj.idx_freq]==2:
                print("DEBUG: sync_userdb() add_phrase(" + str(tuple(list(x[:7]) + [0, x[wbjj.idx_ureq]])) + ", 'user_db', False)")
                self.add_phrase(tuple(list(x[:7]) + [0, x[wbjj.idx_ureq]]), 'user_db', False)
            # 同步用户新造词(freq==-2)
            elif x[wbjj.idx_freq]==-2:
                print("DEBUG: sync_userdb() add_phrase(" + str(tuple(list(x[:7]) + [0, x[wbjj.idx_ureq]])) + ", 'user_db', False)")
                self.add_phrase(tuple(list(x[:7]) + [-1, x[wbjj.idx_ureq]]), 'user_db', False)
        self.db.commit()
    
    def remove_phrase(self, inCandidateTuple):
        '''删词(从用户码表和内存表)'''
        sqlParameterList = [len(inCandidateTuple[wbjj.candidx_code]), inCandidateTuple[wbjj.candidx_code], len(inCandidateTuple[wbjj.candidx_word]), inCandidateTuple[wbjj.candidx_word], inCandidateTuple[wbjj.candidx_cate]]
        for database in ['user_db','memu_db']:
            sqlstr = 'DELETE FROM %(database)s.wubi3 WHERE clen = ? AND code = ? AND wlen = ? AND word = ? AND category = ?;' % {'database':database}
            self.db.execute(sqlstr, sqlParameterList)
        self.db.commit()


    # 过滤拼音的声调字符
    def _pinyin_remove_tone(self, code):
        return code.replace('!','').replace('@','').replace('#','').replace('$','').replace('%','')


    # 数据库基础操作 ====================================================================================
    def create_tables(self, database):
        '''创建表'''
        self.db.execute('PRAGMA page_size = 4096;')
        self.db.execute('PRAGMA cache_size = 20000;')
        self.db.execute('PRAGMA temp_store = MEMORY;')
        self.db.execute('PRAGMA synchronous = OFF;')
        _createsql = 'CREATE TABLE IF NOT EXISTS %(database)s.%(table)s (id INTEGER PRIMARY KEY AUTOINCREMENT, clen INTEGER, code TEXT, '\
                     'wlen INTEGER, word TEXT, category INTEGER, code2 TEXT, freq INTEGER, user_freq INTEGER);'
        # 创建五笔表
        self.db.execute(_createsql % {'database':database, 'table':'wubi3'})
        # 创建拼音表
        self.db.execute(_createsql % {'database':database, 'table':'pinyin3'})
        #if database == 'main':
        #    # 创建ikeys表
        #    sqlstr = 'CREATE TABLE IF NOT EXISTS %s.ikeys (ikey TEXT PRIMARY KEY, id INTEGER);' % database
        #    self.db.execute(sqlstr)
        self.db.commit()
    
    def optimize_database(self, database):
        '''优化数据库(压缩重建)'''
        sqlstr = '''
            CREATE TABLE tmp AS SELECT * FROM %(database)s.%(table)s;
            DELETE FROM %(database)s.%(table)s;
            CREATE TABLE IF NOT EXISTS %(database)s.%(table)s (id INTEGER PRIMARY KEY AUTOINCREMENT, clen INTEGER, code TEXT, 
                   wlen INTEGER, word TEXT, category INTEGER, code2 TEXT, freq INTEGER, user_freq INTEGER);
            INSERT INTO %(database)s.%(table)s SELECT * FROM tmp ORDER BY clen ASC, code ASC, wlen ASC, user_freq DESC, freq DESC;
            DROP TABLE tmp;
            '''
        drop_indexes(database, False)
        self.db.executescript(sqlstr % {'database':database, 'table':'wubi3'})
        self.db.executescript(sqlstr % {'database':database, 'table':'pinyin3'})
        create_indexes(database, False)
        self.db.executescript("VACUUM;")        # 压缩数据库
        self.db.commit()
    
    def drop_indexes(self, database, commit=True):
        '''删除索引'''
        sqlstr = '''
            DROP INDEX IF EXISTS %(database)s.wubi3_index_m;
            DROP INDEX IF EXISTS %(database)s.wubi3_index_w;
            DROP INDEX IF EXISTS %(database)s.pinyin3_index_m;
            DROP INDEX IF EXISTS %(database)s.pinyin3_index_w;
            '''
        self.db.executescript(sqlstr % {'database':database})
        if commit:
            self.db.executescript("VACUUM;")    # 压缩数据库
            self.db.commit()
    
    def create_indexes(self, database, commit=True):
        '''创建索引'''
        sqlstr = '''
            CREATE INDEX IF NOT EXISTS %(database)s.wubi3_index_m ON wubi3 (code, clen ASC, freq DESC, id ASC);
            CREATE INDEX IF NOT EXISTS %(database)s.wubi3_index_w ON wubi3 (word, clen ASC);
            CREATE INDEX IF NOT EXISTS %(database)s.pinyin3_index_m ON pinyin3 (code, clen ASC, freq DESC, id ASC);
            CREATE INDEX IF NOT EXISTS %(database)s.pinyin3_index_w ON pinyin3 (word, clen ASC);
            '''
        self.db.executescript(sqlstr % {'database':database})
        if commit:
            self.db.commit()

    def init_user_db(self, db_file):
        '''创建用户码表文件(如果不存在的话)'''
        if not path.exists(db_file):
            self.db = sqlite3.connect(db_file)
            self.db.execute('PRAGMA page_size = 4096;')
            self.db.execute('PRAGMA cache_size = 20000;')
            self.db.execute('PRAGMA temp_store = MEMORY;')
            self.db.execute('PRAGMA synchronous = OFF;')
            self.db.commit()
    
    def set_database_desc(self):
        '''创建或更新码表信息'''
        try:
            sqlstring = 'CREATE TABLE IF NOT EXISTS user_db.desc (name PRIMARY KEY, value);'
            self.db.executescript(sqlstring)
            sqlstring = 'INSERT OR IGNORE INTO user_db.desc VALUES (?, ?);'
            self.db.execute(sqlstring, ('version', wbjj.dbversion))
            sqlstring = 'INSERT OR IGNORE INTO user_db.desc VALUES (?, DATETIME("now", "localtime"));'
            self.db.execute(sqlstring, ('create-time',))
            self.db.commit()
        except:
            import traceback
            traceback.print_exc()

    def get_database_desc(self, db_file):
        '''返回码表信息'''
        if not path.exists(db_file):
            return None
        try:
            desc = {}
            db = sqlite3.connect(db_file)
            for row in db.execute("SELECT * FROM desc;").fetchall():
                desc[row[0]] = row[1]
            self.db.commit()
            return desc
        except:
            return None

    def fields_alike(self, db_file, table):
        '''表字段是否一致'''
        table_patt = re.compile(r'.*\((.*)\)')
        if not path.exists(db_file):
            return False
        try:
            db = sqlite3.connect(db_file)
            tp_res = db.execute("SELECT sql FROM sqlite_master WHERE name='%(table)s';" % {'table':table}).fetchall()
            self.db.commit()
            res = table_patt.match(tp_res[0][0])
            if res:
                tp = res.group(1).split(',')
                tp = list(map(lambda x: x.strip().split(' ')[0], tp))
                return tp==wbjj.dbfields
            else:
                return False
        except:
            return False


