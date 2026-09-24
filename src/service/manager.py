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

import inspect
import os
from hashlib import md5
from typing import Callable

from .base import Service, LocalService, MdxService, StardictService, WebService, object_builder
from ..context import config
from ..utils import importlib
from ..utils import Empty, Queue

class ServiceManager(object):
    """
    Query service class manager
    """

    def __init__(self):
        self.pools = {}

        # self.update_services()

    def get(self, unique) -> Service:
        # print(f'--- ServicePool.get {unique}')
        queue = self.pools.get(unique, None)
        if queue:
            try:
                return queue.get(True, timeout=0.1)
            except Empty:
                pass
        
        return self.get_service(unique)
    
    def put(self, service: Service):
        if service is None:
            return
        unique = service.unique
        queue = self.pools.get(unique, None)
        if queue == None:
            queue = Queue()
            self.pools[unique] = queue
            
        queue.put(service)
        
    def clean(self):
        self.pools = {}

    @property
    def services(self) -> list[object_builder]:
        return self.web_services + self.local_services

    def update_services(self):
        self.mdx_services, self.star_dict_services = self._get_available_local_services()
        self.web_services, self.local_custom_services = self._get_services_from_files()
        # combine the customized local services into local services
        self.local_services = self.mdx_services + self.star_dict_services + self.local_custom_services

        # try new customized services to disable associated parent
        for sw in self.local_custom_services:
            if sw._enabled_:
                self.put(sw())

        # print(f"service local {self.mdx_services} {self.local_custom_services} web {self.web_services}")
        # self.local_services = self.mdx_services + self.star_dict_services + self.local_custom_services

    def get_service(self, unique) -> Service:
        # webservice unique: class name
        # mdxservice unique: md5 of dict filepath
        for clazz in self.services:
            if clazz._unique_ == unique:
                svc = clazz()
                # print(f'---get_service {svc} clazz._title_ { clazz._title_} title {svc.title} unique {svc.unique}')
                return svc
        
        raise Exception(f"service of unique `{unique}` not found")

    def _get_services_from_files(self, *args):
        """
        get service from service packages, available type is
        WebService, LocalService
        """
        service_dirname = u'dict'
        web_services, local_custom_services = list(), list()
        svc_rootdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), service_dirname)
        files = [
            f for f in os.listdir(svc_rootdir) \
                if f not in ('__init__.py') and \
                    f.endswith('.py') and \
                    not os.path.isdir(os.path.join(svc_rootdir, f))
        ]
        base_class = (
            WebService, 
            LocalService,
            MdxService, 
            StardictService
        )
        for f in files:
            # if 'LDOCE6' not in f:
            #     continue

            module = importlib.import_module( 
                u'.%s.%s' % (service_dirname, os.path.splitext(f)[0]), 
                __package__
            )
            for mod_name, clazz in inspect.getmembers(module, predicate=inspect.isclass):
                if clazz in base_class:
                    continue
                if not(issubclass(clazz, WebService) or issubclass(clazz, LocalService)):
                    continue
                if getattr(clazz, '_register_label_', None) is None:
                    continue
                # print(f'---_get_services_from_files {mod_name} -> {clazz}')
                svc_wrap = object_builder(clazz, *args)
                svc_wrap._title_ = getattr(clazz, '_register_label_', mod_name)
                svc_wrap._unique_ = clazz.__name__
                svc_wrap._src_path_ = os.path.join(svc_rootdir, f)
                svc_wrap._enabled_ = clazz._enabled_
                # svc_wrap._class_ = clazz
                # print(f"[Found] service: {vars(svc)}")

                if issubclass(clazz, WebService):
                    web_services.append(svc_wrap)
                # get the customized local services
                if issubclass(clazz, LocalService):
                    local_custom_services.append(svc_wrap)
        web_services = sorted(web_services, key=lambda clazz: clazz._title_)
        local_custom_services = sorted(local_custom_services, key=lambda clazz: clazz._title_)
        return web_services, local_custom_services

    def _get_available_local_services(self):
        '''
        available local dictionary services
        '''
        mdx_services = list()
        star_dict_services = list()
        print(f'config.dict_dirs: {config.dict_dirs}')
        for each in config.dict_dirs:
            print(f'config.dict_dirs > {each}')
            for dirpath, dirnames, filenames in os.walk(each):
                for filename in filenames:
                    dict_path = os.path.join(dirpath, filename)
                    #MDX
                    svc_wrap = object_builder(MdxService, dict_path)
                    rootname, _ = os.path.splitext(os.path.basename(dict_path))
                    if MdxService.check(dict_path):
                        print(f'config.dict_dirs > MdxService dict_path {dict_path}')
                        svc_wrap._title_ = rootname
                        svc_wrap._unique_ = md5(str(dict_path).encode('utf-8')).hexdigest()
                        svc_wrap._enabled_ = True
                        # svc_wrap._class_ = MdxService

                        mdx_services.append(svc_wrap)
                    #Stardict    
                    if StardictService.check(dict_path):
                        svc_wrap = object_builder(StardictService, dict_path)
                        svc_wrap._title_ = rootname
                        svc_wrap._unique_ = md5(str(dict_path).encode('utf-8')).hexdigest()
                        svc_wrap._enabled_ = True
                        # svc_wrap._class_ = StardictService

                        star_dict_services.append(svc_wrap)
                # support mdx dictionary and stardict format dictionary
        return mdx_services, star_dict_services


# # MDX-LDOEC6CE supersede LDOEC6CE, init once and disable
# def try_init_services():
#     dicts = config.dicts
#     for clazz in service_manager.local_services:
#         if dicts.get(clazz._unique_, {}).get('enabled', clazz._enabled_):
#             svc = service_manager.get(clazz._unique_)
#             service_manager.put(svc)

# try_init_services()
