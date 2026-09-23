#-*- coding:utf-8 -*-
#
# Copyright (C) 2018 sthoo <sth201807@gmail.com>
#
# Support: Report an issue at https://github.com/sth2018/FastWordQuery/issues
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version; http://www.gnu.org/copyleft/gpl.html.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
import sys
sys.dont_write_bytecode = True

from .manager import ServiceManager
from .pool import ServicePool
from .base import Service, LocalService, QueryResult, copy_static_file, WordNotFoundError
from ..context import config

service_manager = ServiceManager()                             # Service Manager
service_pool = ServicePool(service_manager)                    # Service Instance Pool Manager

# MDX-LDOEC6CE supersede LDOEC6CE, init once and disable
def try_init_services():
    dicts = config.dicts
    for clazz in service_manager.local_services:
        if dicts.get(clazz._unique_, {}).get('enabled', clazz._enabled_):
            svc = service_pool.get(clazz._unique_)
            service_pool.put(svc)

try_init_services()
