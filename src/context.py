# -*- coding:utf-8 -*-
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

import os
import sys
import json
import traceback
import threading
from packaging.version import Version

import multiprocessing as mp

_IS_MAIN_PROCESS = 0

def is_main_process():
    global _IS_MAIN_PROCESS
    if _IS_MAIN_PROCESS > 0:
        return _IS_MAIN_PROCESS == 1
    
    for m in sys.modules:
        if "Qt" in m or "aqt" in m:
            _IS_MAIN_PROCESS = 1
            break
    else:
        _IS_MAIN_PROCESS = 2

    return _IS_MAIN_PROCESS == 1

if is_main_process():
    from aqt import mw
else:
    mw = None


###################################################
# spawned worker process has no mw
ADDON_NAME = mw.addonManager.addonFromModule(__name__) if mw else os.path.basename(os.path.dirname(__file__))
ADDON_DIR = mw.addonManager.addonsFolder(ADDON_NAME) if mw else os.path.dirname(__file__)

# 1. Point Anki's Python environment to your bundled offline library
for ldir in ["libs", "vendor", '.']:
    vendor_dir = os.path.join(ADDON_DIR, ldir)
    if vendor_dir not in sys.path:
        sys.path.append(vendor_dir)

# sys.path.append(ADDON_DIR)

print(f'sys.path {sys.path}')
print(f"ADDON_NAME {ADDON_NAME}")
print(f"ADDON_DIR {ADDON_DIR}")

from .utils import misc
# show current dir in open error message for easy debug
misc.hook_builtins_open_exception()


from .constants import VERSION
from .utils.events import events

# __all__ = ['config', 'ADDON_NAME']


class Config(object):
    """
    Addon Config
    """

    _CONFIG_FILENAME = 'fastwqcfg.json'  # Config File Path

    def __init__(self, window):
        self.data = {}
        self.path = u'_' + self._CONFIG_FILENAME
        self.window = window
        # self.version = '0'
        self.profile_folder = None
        self.read()

    @property
    def pm_name(self):
        return self.window.pm.name

    def update(self, data:dict):
        """
        Update && Save
        """
        data['version'] = VERSION
        data['%s_last' % self.pm_name] = data.get('last_model', self.last_model_id)
        self.data.update(data)
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump(
                self.data, f, indent=4, ensure_ascii=False)
            f.close()
        events.trigger('config.update')

    def read(self):
        """
        Load from config file
        """
        # print(f'---read mw {mw} self.data {self.data}')
        if self.data:
            if mw and mw.pm and mw.pm.profileFolder() != self.profile_folder:
                self.data = {}
        try:
            if not self.data:
                path = self.path  # if os.path.exists(self.path) else u'.' + self._CONFIG_FILENAME
                print(f'---reading config path {path}')
                with open(path, 'r', encoding="utf-8") as f:
                    self.data = json.load(f)
                # if not os.path.exists(self.path):
                #     self.update(self.data)
                if self.version < Version(VERSION):
                    print(f'Version {self.version} is less than required version {Version(VERSION)}')
                    print(f'Use empty config')
                    self.data = {}
                if mw:
                    self.profile_folder = mw.pm.profileFolder()
        except Exception as e:
            print(f'*** Can not find config file:', e)
            # print(traceback.format_exc())
            self.data = {}

        return self.data

    def get_query_configs(self, model_id):
        """
        Query fileds map
        """
        return self.data.get(str(model_id), {'query_configs':[], 'default': -1})

    @property
    def version(self):
        return Version(self.data.get('version', '0'))
    
    @version.setter
    def version(self, new_ver):
        self.data.update({'version': new_ver})

    @property
    def last_model_id(self):
        return self.data.get('%s_last' % self.pm_name, 0)

    @property
    def dict_dirs(self):
        return self.data.get('dict_dirs', list())

    @property
    def dicts(self):
        return self.data.get('dicts', dict())

    @property
    def use_filename(self):
        return self.data.get('use_filename', True)

    @property
    def export_media(self):
        return self.data.get('export_media', True)

    @property
    def force_update(self):
        return self.data.get('force_update', False)

    @property
    def ignore_mdx_wordcase(self):
        return self.data.get('ignore_mdx_wordcase', False)

    @property
    def thread_number(self):
        """
        Query Thread Number
        """
        return self.data.get('thread_number', 8)

    @property
    def last_folder(self):
        """
        last file dialog open path
        """
        return self.data.get('last_folder', '')

    @property
    def ignore_accents(self):
        '''ignore accents of field in querying'''
        return self.data.get('ignore_accents', False)

    @property
    def cloze_str(self):
        '''cloze formater string'''
        tmpstr = self.data.get('cloze_str', '{{c1::%s}}')
        if len(tmpstr.split('%s')) != 2:
            tmpstr = '{{c1::%s}}'
        return tmpstr

    @property
    def sound_str(self):
        '''sound formater string'''
        # 设置音频播放按钮大小
        # <span style="width:24px;height:24px;">[sound:{0}]</span>
        tmpstr = self.data.get('sound_str', u'[sound:{0}]')
        if len(tmpstr.split('{0}')) != 2:
            tmpstr = u'[sound:{0}]'
        return tmpstr

    @property
    def ollama_host(self):
        return self.data.get('ollama_host', 'localhost:11434')

    @property
    def ollama_model(self):
        return self.data.get('ollama_model', 'gemma4:26b')

    @property
    def ollama_lang(self):
        return self.data.get('ollama_lang', '中文')


    
# should chdir on profile change through hook,
# since context.py is only imported once.
# the chdir logic at `__init__.py`

config = Config(mw)


def gui_processEvents():
    if mw:
        return mw.app.processEvents()


from collections import defaultdict
_WORKER_LOCKS = defaultdict(threading.Lock)

def set_worker_lock(ltype, lock):
    if ltype in _WORKER_LOCKS:
        print(f'*** Warning: overriding lock type `{ltype}` with new lock {lock}')
    _WORKER_LOCKS[ltype] = lock

def get_worker_lock(ltype):
    if ltype not in _WORKER_LOCKS:
        print(f'*** Warning: no existing lock of type `{ltype}`, new one')
    return _WORKER_LOCKS[ltype]
