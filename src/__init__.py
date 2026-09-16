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
import ssl
import sys

from aqt import mw
from anki.hooks import addHook
from anki.utils import is_mac

sys.dont_write_bytecode = True
if is_mac:
    ssl._create_default_https_context = ssl._create_unverified_context

############## other config here ##################
shortcut = ('Ctrl+Alt' if is_mac else 'Ctrl') + '+Q'

###################################################
ADDON_NAME = mw.addonManager.addonFromModule(__name__)
ADDON_DIR = mw.addonManager.addonsFolder(ADDON_NAME)
# 1. Point Anki's Python environment to your bundled offline library
for ldir in ["libs", "vendor"]:
    vendor_dir = os.path.join(ADDON_DIR, ldir)
    if vendor_dir not in sys.path:
        sys.path.append(vendor_dir)

print(f'sys.path {sys.path}')

from .utils import misc
# show current dir in open error message for easy debug
misc.hook_builtins_open_exception()

def start_here():
    print(f'-'*80)
    print(__file__)
    print(f"ADDON_NAME {ADDON_NAME}")
    print(f"ADDON_DIR {ADDON_DIR}")

    # https://github.com/sth2018/FastWordQuery/issues/258
    wp = mw.pm.profileFolder()
    mediaPath = os.path.join(wp, "collection.media")
    os.chdir(mediaPath)
    print(f"CWD {os.getcwd()}")

    from . import common as fastwq
    from .context import config
    # config is only imported once, we should call read every time profile changed
    config.read()
    fastwq.my_shortcut = shortcut
    if not fastwq.have_setup:
        fastwq.have_setup = True
        fastwq.config_menu()
        fastwq.browser_menu()
        fastwq.context_menu()
        fastwq.customize_addcards()


addHook("profileLoaded", start_here)
