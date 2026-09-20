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


## Following code can be used to debug import chain,
## put it to where the exception occurs when importing,
## Python doesn't print import chain when print exception stack.
# Inside your submodule (e.g., my_package/submodule.py)
import inspect

def print_import_chain():
    # Retrieve all active execution frames
    frames = inspect.stack()
    
    chain = []
    for frame_info in reversed(frames):
        module_name = frame_info.frame.f_globals.get('__name__')
        if module_name and (not chain or chain[-1] != module_name):
            chain.append(module_name)
            
    print("Active Import Chain:", " -> ".join(chain))

# Execute immediately when the submodule is imported
# print_import_chain()
# print(f"{'*'*40} {__name__} imported {'*'*40}")



import os
from dataclasses import dataclass, fields as dataclass_fields
from functools import wraps

from aqt.utils import showInfo
from aqt.qt import QIcon

__all__ = ['ignore_exception',
           'get_model_byId',
           'get_icon',
           'get_ord_from_fldname',
           'MapDict',
           'QueryStat'
           ]


def ignore_exception(func):
    @wraps(func)
    def wrap(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except:
            return ''
    return wrap


def get_model_byId(models, id):
    for m in list(models.all()):
        # showInfo(str(m['id']) + ', ' + m['name'])
        if m['id'] == id:
            return m


def get_ord_from_fldname(model, name):
    flds = model['flds']
    for fld in flds:
        if fld['name'] == name:
            return fld['ord']


def get_icon(filename):
    curdir = os.path.dirname(os.path.abspath(__file__))
    pardir = os.path.join(curdir, os.pardir)
    path = os.path.join(pardir, 'res', filename)
    return QIcon(path)


# Some query words like 'Saudi Arabia' is comprised by two or more words that split by '%20'(space),
# it is an invalid query format. (Validated Dictionary: Longman, oxford learning)
def format_multi_query_word(words: str):
    _space = '%20'
    if words is None or _space not in words:
        return words

    return words.lower().replace(_space, '-')


class MapDict(dict):
    """
    Dict subclass that enables attribute/dot-notation access.
    Fully picklable across process boundaries.
    """

    def __init__(self, *args, **kwargs):
        super(MapDict, self).__init__(*args, **kwargs)
        # Update self directly using dict methods (no self.__dict__ pollution)
        for arg in args:
            if isinstance(arg, dict):
                self.update(arg)
        if kwargs:
            self.update(kwargs)

    def __getattr__(self, attr):
        try:
            return self[attr]
        except KeyError:
            raise AttributeError(
                f"'{self.__class__.__name__}' object has no attribute '{attr}'"
            )

    def __setattr__(self, key, value):
        self[key] = value

    def __delattr__(self, key):
        try:
            del self[key]
        except KeyError:
            raise AttributeError(
                f"'{self.__class__.__name__}' object has no attribute '{key}'"
            )

@dataclass
class QueryStat:
    note_count: int = 0
    field_skip_count:int = 0
    field_success_count:int = 0
    field_no_result_count:int = 0
    field_error_count:int = 0
    field_updated_count: int = 0

    def reset(self) -> None:
        """Reset all dataclass fields to their default values defined in class type annotations."""
        for f in dataclass_fields(self):
            # Restores default value (or default_factory if defined)
            default = (
                f.default_factory()
                if callable(f.default_factory)
                else f.default
            )
            setattr(self, f.name, default)
            
    def __add__(self, other: "QueryStat") -> "QueryStat":
        if not isinstance(other, QueryStat):
            return NotImplemented
        return QueryStat(
            **{
                f.name: getattr(self, f.name) + getattr(other, f.name)
                for f in dataclass_fields(self)
            }
        )

    def __iadd__(self, other: "QueryStat") -> "QueryStat":
        if not isinstance(other, QueryStat):
            return NotImplemented
        for f in dataclass_fields(self):
            setattr(self, f.name, getattr(self, f.name) + getattr(other, f.name))
        return self


### sys level

def hook_builtins_open():
    import builtins
    import os
    from pathlib import Path

    # 1. Store a reference to the original built-in open function
    original_open = builtins.open

    # 2. Define the hook/wrapper function
    def custom_open(file, mode='r', buffering=-1, encoding=None, errors=None, newline=None, closefd=True, opener=None):
        # Perform custom action (e.g., logging or debugging path resolution)
        abs_path = Path(file).resolve()
        if str(file) != str(abs_path):
            print(f"opening: `{file}` in dir `{os.getcwd()}`")

        # Call the original open function
        return original_open(file, mode, buffering, encoding, errors, newline, closefd, opener)

    # 3. Replace builtins.open with the custom function
    builtins.open = custom_open

def hook_builtins_open_exception():
    import builtins
    import os
    from pathlib import Path

    original_open = builtins.open

    def custom_open(file, *args, **kwargs):
        try:
            return original_open(file, *args, **kwargs)
        except OSError as err: # Catches FileNotFoundError, PermissionError, etc.
            cwd = os.getcwd()
            raw_file = err.filename or file
            abs_path = Path(raw_file).resolve() if raw_file else "Unknown"

            # Mutate the strerror attribute directly
            err.strerror = f"{err.strerror} in '{cwd}'"
            raise err

    builtins.open = custom_open