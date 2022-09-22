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

import sys
#import importlib
#importlib.reload(sys)


# 常用特殊符号
chinese_nc_chars = "，、。．；：？！＃＆＠＾＼／｀＿—￣〓…～·ˉ∶ˇ¨‘’“”＇＂（）［］〔〕「」『』【】〖〗｛｝〈〉《》｜‖♂♀°℃§€々‰№☆★○●◎◇◆□■△▲※"
# 大写罗马
chinese_nc_chars += "ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩⅪⅫ"
# 小写罗马
chinese_nc_chars += "ⅰⅱⅲⅳⅴⅵⅶⅷⅸⅹ"
# 大写希腊
chinese_nc_chars += "ΑΒΓΔΕΖΗΘΙΚΛΜΝΞΟΠΡΣΤΥΦΧΨΩ"
# 小写希腊
chinese_nc_chars += "αβγδεζηθικλμνξοπρστυφχψω"
# 大写俄文
chinese_nc_chars += "АБВГДЕЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯЁ"
# 小写俄文
chinese_nc_chars += "абвгдежзийклмнопрстуфхцчшщъыьэюяё"
# 平假名
chinese_nc_chars += "ぁあぃいぅうぇえぉおかがきぎくぐけげこごさざしじすずせぜそぞただちぢっつづてでとどなにぬねのはばひびぴふぶぷへべぺほぼぽまみむめもゃやゅゆょよらりるれろゎわゐゑをん゛゜ゝゞ"
# 片假名
chinese_nc_chars += "ァアィイゥウェエォオカガキギクグケゲコゴサザシジスズセゼソゾタダチヂッツヅテデトドナニヌネノハバパヒビピフブプヘベペホボポマミムメモャヤュユョヨラリルレロヮワヰヱヲンヴヵヶーヽヾ"
# 注音符号
chinese_nc_chars += "ㄅㄆㄇㄈㄉㄊㄋㄌㄍㄎㄏㄐㄑㄒㄓㄔㄕㄖㄗㄘㄙㄧㄨㄩㄚㄛㄜㄝㄞㄟㄠㄡㄢㄣㄤㄥㄦ"
# 数学符号
chinese_nc_chars += "＋－＜＝＞±×÷∈∏∑∕√∝∞∟∠∣∥∧∨∩∪∫∮∴∵∶∷∽≈≌≒≠≡≤≥≦≧≮≯⊕⊙⊥⊿"
# 单位符号
chinese_nc_chars += "㎎㎏㎜㎝㎞㎡㏄㏎㏑㏒㏕"
# 方向箭头
chinese_nc_chars += "←↓↑→↖↗↘↙"
# 圆圈数字
chinese_nc_chars += "①②③④⑤⑥⑦⑧⑨⑩"
# 括号数字
chinese_nc_chars += "⑴⑵⑶⑷⑸⑹⑺⑻⑼⑽⑾⑿⒀⒁⒂⒃⒄⒅⒆⒇"
# 数字点
chinese_nc_chars += "⒈⒉⒊⒋⒌⒍⒎⒏⒐⒑⒒⒓⒔⒕⒖⒗⒘⒙⒚⒛"
# 中文数字
chinese_nc_chars += "㈠㈡㈢㈣㈤㈥㈦㈧㈨㈩"
# 货币符号
chinese_nc_chars += "＄￠￡￥¤"
# 拼音符号
chinese_nc_chars += "āáǎàōóǒòêēéěèīíǐìǖǘǚǜüūúǔùɑńňǹɡ"
# 偏旁部首
chinese_nc_chars += "勹灬冫艹屮辶刂匚阝廾丨虍彐卩钅冂冖宀疒肀丿攵凵犭亻彡饣礻扌氵纟亠囗忄讠衤廴尢夂丶"

#chinese_nocheck_chars = chinese_nc_chars.decode('utf8')
chinese_nocheck_chars = chinese_nc_chars

__HALF_FULL_TABLE = [
    (0x0020, 0x3000, 1),    # SPACE
    (0x0021, 0xFF01, 0x5E), # !及后续94个字符,含(a-zA-Z0-9等)
    (0x00A2, 0xFFE0, 2),    # ¢
    (0x00A5, 0xFFE5, 1),    # ¥
    (0x00A6, 0xFFE4, 1),    # ¥
    (0x00AC, 0xFFE2, 1),    # ¬
    (0x00AF, 0xFFE3, 1),    # ¯
    (0x20A9, 0xFFE6, 1),    # ₩
    (0xFF61, 0x3002, 1),    # 
    (0xFF62, 0x300C, 2),    # 
    (0xFF64, 0x3001, 1),    # 
    (0xFF65, 0x30FB, 1),    # 
    (0xFF66, 0x30F2, 1),    # 
    (0xFF67, 0x30A1, 1),    # 
    (0xFF68, 0x30A3, 1),    # 
    (0xFF69, 0x30A5, 1),    # 
    (0xFF6A, 0x30A7, 1),    # 
    (0xFF6B, 0x30A9, 1),    # 
    (0xFF6C, 0x30E3, 1),    # 
    (0xFF6D, 0x30E5, 1),    # 
    (0xFF6E, 0x30E7, 1),    # 
    (0xFF6F, 0x30C3, 1),    # 
    (0xFF70, 0x30FC, 1),    # 
    (0xFF71, 0x30A2, 1),    # 
    (0xFF72, 0x30A4, 1),    # 
    (0xFF73, 0x30A6, 1),    # 
    (0xFF74, 0x30A8, 1),    # 
    (0xFF75, 0x30AA, 2),    # 
    (0xFF77, 0x30AD, 1),    # 
    (0xFF78, 0x30AF, 1),    # 
    (0xFF79, 0x30B1, 1),    # 
    (0xFF7A, 0x30B3, 1),    # 
    (0xFF7B, 0x30B5, 1),    # 
    (0xFF7C, 0x30B7, 1),    # 
    (0xFF7D, 0x30B9, 1),    # 
    (0xFF7E, 0x30BB, 1),    # 
    (0xFF7F, 0x30BD, 1),    # 
    (0xFF80, 0x30BF, 1),    # 
    (0xFF81, 0x30C1, 1),    # 
    (0xFF82, 0x30C4, 1),    # 
    (0xFF83, 0x30C6, 1),    # 
    (0xFF84, 0x30C8, 1),    # 
    (0xFF85, 0x30CA, 6),    # 
    (0xFF8B, 0x30D2, 1),    # 
    (0xFF8C, 0x30D5, 1),    # 
    (0xFF8D, 0x30D8, 1),    # 
    (0xFF8E, 0x30DB, 1),    # 
    (0xFF8F, 0x30DE, 5),    # 
    (0xFF94, 0x30E4, 1),    # 
    (0xFF95, 0x30E6, 1),    # 
    (0xFF96, 0x30E8, 6),    # 
    (0xFF9C, 0x30EF, 1),    # 
    (0xFF9D, 0x30F3, 1),    # 
    (0xFFA0, 0x3164, 1),    # 
    (0xFFA1, 0x3131, 30),   # 
    (0xFFC2, 0x314F, 6),    # 
    (0xFFCA, 0x3155, 6),    # 
    (0xFFD2, 0x315B, 9),    # 
    (0xFFE9, 0x2190, 4),    # 
    (0xFFED, 0x25A0, 1),    # 
    (0xFFEE, 0x25CB, 1)
]

def unichar_half_to_full(char):
    code = ord(char)
    for half, full, size in __HALF_FULL_TABLE:
        if code >= half and code < half + size:
            if sys.version_info >= (3, 0, 0):
                return chr(full + code - half)
            return unichr(full + code - half)
    return char

#def unichar_full_to_half(char):
#    code = ord(char)
#    for half, full, size in __HALF_FULL_TABLE:
#        if code >= full and code < full + size:
#            if sys.version_info >= (3, 0, 0):
#                return chr(half + code - full)
#            return unichr(half + code - full)
#    return char

