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
sys.dont_write_bytecode = True

# print(sys.modules)

import multiprocessing as mp

def is_main_process():
    for m in sys.modules:
        if "Qt" in m or "aqt" in m:
            return True
    return False

print(f'---sys.argv {sys.argv}')
print(f"[PID {os.getpid()}] Starting worker module import...", flush=True)
# Print loaded modules before any add-on imports
# print("Loaded Qt modules before add-on imports:", [m for m in sys.modules if "Qt" in m or "aqt" in m], flush=True)

if is_main_process():
    from aqt import mw, gui_hooks
    from anki.utils import is_mac
else:
    mw = None
# print("Loaded Qt modules before add-on imports:", [m for m in sys.modules if "Qt" in m or "aqt" in m], flush=True)

print(f'===mw {mw}')

def start_here():
    import ssl
    if is_mac:
        ssl._create_default_https_context = ssl._create_unverified_context

    ############## other config here ##################
    shortcut = ('Ctrl+Alt' if is_mac else 'Ctrl') + '+Q'

    print(f'-'*80)
    print(__file__)

    # https://github.com/sth2018/FastWordQuery/issues/258
    wp = mw.pm.profileFolder()
    mediaPath = os.path.join(wp, "collection.media")
    os.chdir(mediaPath)
    print(f"CWD {os.getcwd()}")

    from .context import config
    from .gui import common as fastwq
    # config is only imported once, we should call read every time profile changed
    config.read()
    fastwq.my_shortcut = shortcut
    if not fastwq.have_setup:
        fastwq.have_setup = True
        fastwq.config_menu()
        fastwq.browser_menu()
        fastwq.context_menu()
        fastwq.customize_addcards()

if mw:
    gui_hooks.profile_did_open.append(start_here)
