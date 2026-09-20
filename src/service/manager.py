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


class ServiceManager(object):
    """
    Query service class manager
    """

    def __init__(self):
        self.update_services()

    @property
    def services(self):
        return self.web_services + self.local_services

    def update_services(self):
        self.mdx_services, self.star_dict_services = self._get_available_local_services()
        self.web_services, self.local_custom_services = self._get_services_from_files()
        # combine the customized local services into local services
        self.local_services = self.mdx_services + self.star_dict_services + self.local_custom_services
        # print(f"service local {self.mdx_services} {self.local_custom_services} web {self.web_services}")

    def get_service(self, unique) -> Service:
        # webservice unique: class name
        # mdxservice unique: md5 of dict filepath
        for svc in self.services:
            if svc._unique_ == unique:
                service = svc()

                service.unique = unique
                return service
        
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
            if 'LDOCE6' not in f:
                continue
            #try:
            module = importlib.import_module( 
                u'.%s.%s' % (service_dirname, os.path.splitext(f)[0]), 
                __package__
            )
            for name, clazz in inspect.getmembers(module, predicate=inspect.isclass):
                if clazz in base_class:
                    continue
                if not(issubclass(clazz, WebService) or issubclass(clazz, LocalService)):
                    continue
                if getattr(clazz, '_register_label_', None) is None:
                    continue
                svc = object_builder(clazz, *args)
                svc._title_ = getattr(clazz, '_register_label_', name)
                svc._unique_ = name
                svc._src_path_ = os.path.join(svc_rootdir, f)
                svc._enabled_ = clazz._enabled_
                print(f"Found service: {vars(svc)}")

                if issubclass(clazz, WebService):
                    web_services.append(svc)
                # get the customized local services
                if issubclass(clazz, LocalService):
                    local_custom_services.append(svc)
        web_services = sorted(web_services, key=lambda service: service._title_)
        local_custom_services = sorted(local_custom_services, key=lambda service: service._title_)
        return web_services, local_custom_services

    def _get_available_local_services(self):
        '''
        available local dictionary services
        '''
        mdx_services = list()
        star_dict_services = list()
        for each in config.dict_dirs:
            print(f'config.dict_dirs {each}')
            for dirpath, dirnames, filenames in os.walk(each):
                for filename in filenames:
                    svc = None
                    dict_path = os.path.join(dirpath, filename)
                    #MDX
                    if MdxService.check(dict_path):
                        print(f'config.dict_dirs > MdxService dict_path {dict_path}')
                        svc = object_builder(MdxService, dict_path)
                        svc._unique_ = md5(str(dict_path).encode('utf-8')).hexdigest()
                        svc._enabled_ = True
                        mdx_services.append(svc)
                    #Stardict    
                    if StardictService.check(dict_path):
                        svc = object_builder(StardictService, dict_path)
                        svc._unique_ = md5(str(dict_path).encode('utf-8')).hexdigest()
                        svc._enabled_ = True
                        star_dict_services.append(svc)
                # support mdx dictionary and stardict format dictionary
        return mdx_services, star_dict_services
