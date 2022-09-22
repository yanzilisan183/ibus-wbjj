# coding=utf-8
# vim:et st=4 sts=4 sw=4
# ibus-wbjj - 五笔加加Plus for IBus
#
# Copyright (c) 2013-2022 LI Yunfei <yanzilisan183@sina.com>
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
from gi import require_version
require_version('IBus', '1.0')
from gi.repository import IBus
import table
import tabsqlitedb
import wbjj


class EngineFactory(IBus.Factory):
    """Table IM Engine Factory"""
    def __init__(self, bus, db=''):
        if db:
            self.dbusname = os.path.basename(db).replace('.db', '')
            udb = os.path.basename(db).replace('.db', '-user.db')
            self.db = tabsqlitedb.TabSqliteDb(name=db, user_db=udb)
            self.db.db.commit()
            self.dbdict = {self.dbusname:self.db}
        else:
            self.db = None
            self.dbdict = {}
        self.bus = bus
        super().__init__(connection=bus.get_connection(), object_path=IBus.PATH_FACTORY)
        self.engine_id = 0
        self.engine_path = ''
       

    def do_create_engine(self, engine_name):
        path_patt = re.compile(r'[^a-zA-Z0-9_/]')
        engine_base_path = "/com/redhat/IBus/engines/%s/engine/"
        self.engine_path = engine_base_path % path_patt.sub('_', engine_name)
        try:
        #if 1==1:
            if not self.db:
                if not engine_name in self.dbdict:
                    db = os.path.join(wbjj.dbpath, engine_name + '.db')
                    udb = engine_name + '-user.db'
                    _sq_db = tabsqlitedb.TabSqliteDb(name=db, user_db=udb)
                    _sq_db.db.commit()
                    self.dbdict[engine_name] = _sq_db
            else:
                engine_name = self.dbusname

            engine = table.TabEngine(self.bus, self.engine_path + str(self.engine_id), self.dbdict[engine_name])
            self.engine_id += 1
            #return engine.get_dbus_object()
            return engine
        except:
            print("WARNING: fail to create engine %s" % engine_name)
            if wbjj.options.debug:
                raise
            else:
                import traceback
                traceback.print_exc()
            raise Exception("Can not create engine %s" % engine_name)

    def do_destroy(self):
        '''Destructor, which finish some task for IME'''
        for _db in self.dbdict:
            self.dbdict[_db].sync_usrdb()
        try:
            self._sm.Quit()
        except:
            pass
        super().destroy()


