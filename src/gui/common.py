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

import types
from operator import itemgetter

from aqt import mw
from aqt.qt import *

from anki.hooks import addHook, remHook, wrap
from aqt import gui_hooks, mw
from aqt.addcards import AddCards
from aqt.qt import *
from aqt.utils import downArrow, shortcut, showInfo

from ..constants import Template
from ..context import config
from ..lang import _
from ..service import service_manager, service_pool
from .dictmanager import DictManageDialog
from .foldermanager import FoldersManageDialog
from .options import OptionsDialog
from .base import *


__all__ = [
    'browser_menu', 'customize_addcards', 'config_menu', 'context_menu',
    'show_options', 'show_fm_dialog', 'show_about_dialog'
]  # 'check_updates',


def show_fm_dialog(browser=None):
    '''open dictionary folder manager window'''
    parent = mw if browser is None else browser
    fm_dialog = FoldersManageDialog(parent, u'Dictionary Folder Manager')
    fm_dialog.activateWindow()
    fm_dialog.raise_()
    if fm_dialog.exec() == QDialog.DialogCode.Accepted:
        # update local services
        service_pool.clean()
        service_manager.update_services()
    fm_dialog.destroy()
    # reshow options window
    show_options(browser)


def show_dm_dialog(browser=None):
    parent = mw if browser is None else browser
    dm_dialog = DictManageDialog(parent, u'Dictionary Manager')
    dm_dialog.activateWindow()
    dm_dialog.raise_()
    if dm_dialog.exec() == QDialog.DialogCode.Accepted:
        # update local services
        service_pool.clean()
        service_manager.update_services()
    dm_dialog.destroy()
    # reshow options window
    show_options(browser)


def show_options(browser=None, model_id=-1, callback=None, *args, **kwargs):
    '''open options window'''
    parent = mw if browser is None else browser
    config.read()
    opt_dialog = OptionsDialog(parent, u'Options', model_id)
    opt_dialog.activateWindow()
    opt_dialog.raise_()
    result = opt_dialog.exec()
    opt_dialog.destroy()
    if result == QDialog.DialogCode.Accepted:
        if isinstance(callback, types.FunctionType):
            callback(*args, **kwargs)
    elif result == 1001:
        show_fm_dialog(parent)
    elif result == 1002:
        show_dm_dialog(parent)


def show_about_dialog(parent):
    '''open about dialog'''
    QMessageBox.about(parent, _('ABOUT'), Template.tmpl_about)


have_setup = False
my_shortcut = ''

def set_options_def(mid, i):
    mconf = config.get_query_configs(mid)
    if mconf['default'] != i:
        mconf['default'] = i
        data = dict()
        data[mid] = mconf
        config.update(data)


# end set_options_def


def browser_menu():
    """
    add add-on's menu to browser window
    """
    _OK_ICON = get_icon('ok.png')
    _NULL_ICON = get_icon('null.png')
    from ..aquery import query_from_browser, query_from_editor_fields

    def on_setup_menus(browser):
        """
        on browser setupMenus was called
        """
        # main menu
        menu = browser.form.menubar.addMenu("FastWQ")

        # menu gen
        def init_fastwq_menu():
            try:
                menu.clear()
            except RuntimeError:
                remHook('config.update', init_fastwq_menu)
                return
            # Query Selected
            action = QAction(_('QUERY_SELECTED'), browser)
            action.triggered.connect(lambda: query_from_browser(browser))
            action.setShortcut(QKeySequence(my_shortcut))
            menu.addAction(action)
            # Options
            action = QAction(_('OPTIONS'), browser)

            def _show_options():
                model_id = -1
                for note_id in browser.selectedNotes():
                    note = browser.mw.col.get_note(note_id)
                    model_id = note.note_type()['id']
                    break
                show_options(browser, model_id)

            action.triggered.connect(_show_options)
            menu.addAction(action)

            # Default qconfigs
            menu.addSeparator()
            b = False
            for m in sorted(
                    browser.mw.col.models.all(), key=itemgetter("name")):
                mconf = config.get_query_configs(m['id'])
                qconfigs = mconf['query_configs']
                if len(qconfigs) > 1:
                    submenu = menu.addMenu(m['name'])
                    for i, cfg in enumerate(qconfigs):
                        submenu.addAction(
                            _OK_ICON if i == mconf['default'] else _NULL_ICON, cfg['name'],
                            lambda mid=m['id'], i=i: set_options_def(mid, i)
                        )
                    b = True
            if b:
                menu.addSeparator()

            # # check update
            # action = QAction(_('CHECK_UPDATE'), browser)
            # action.triggered.connect(lambda: check_updates(background=False, parent=browser))
            # menu.addAction(action)

            # About
            action = QAction(_('ABOUT'), browser)
            action.triggered.connect(lambda: show_about_dialog(browser))
            menu.addAction(action)

        # end init_fastwq_menu
        init_fastwq_menu()
        addHook('config.update', init_fastwq_menu)

    gui_hooks.browser_menus_did_init.append(on_setup_menus)


def customize_addcards():
    """
    add button to addcards window
    """
    _OK_ICON = get_icon('ok.png')
    _NULL_ICON = get_icon('null.png')
    from ..aquery import query_from_browser, query_from_editor_fields

    def add_query_button(self):
        '''
        add a button in add card window
        '''
        bb = self.form.buttonBox
        ar = QDialogButtonBox.ButtonRole.ActionRole
        # button
        fastwqBtn = QPushButton(_("QUERY") + u" " + downArrow())
        fastwqBtn.setShortcut(QKeySequence(my_shortcut))
        fastwqBtn.setToolTip(_(u"Shortcut: %s") % shortcut(my_shortcut))
        bb.addButton(fastwqBtn, ar)

        # signal
        def onQuery(e):
            if isinstance(e, QMouseEvent):
                if e.buttons() & Qt.MouseButton.LeftButton:
                    menu = QMenu(self)
                    menu.addAction(
                        _("ALL_FIELDS"),
                        lambda: query_from_editor_fields(self.editor))  # ,QKeySequence(my_shortcut))
                    # default options
                    mid = self.editor.note.note_type()['id']
                    mconf = config.get_query_configs(mid)
                    qconfigs = mconf['query_configs']
                    if len(qconfigs) > 1:
                        menu.addSeparator()
                        for i, cfg in enumerate(qconfigs):
                            menu.addAction(
                                _OK_ICON if i == mconf['default'] else _NULL_ICON,
                                cfg['name'],
                                lambda mid=mid, i=i: set_options_def(mid, i))
                        menu.addSeparator()
                    # end default options
                    menu.addAction(_("OPTIONS"), 
                                   lambda: show_options(self, self.editor.note.note_type()['id']))
                    menu.exec(
                        fastwqBtn.mapToGlobal(QPoint(0, fastwqBtn.height())))
            else:
                query_from_editor_fields(self.editor)

        fastwqBtn.mousePressEvent = onQuery
        fastwqBtn.clicked.connect(onQuery)

    AddCards.setupButtons = wrap(AddCards.setupButtons, add_query_button,
                                 "after")


def config_menu():
    """
    add menu to anki window menebar
    """
    action = QAction(APP_ICON, "FastWQ Options...", mw)
    action.triggered.connect(lambda: show_options())
    mw.form.menuTools.addAction(action)


def context_menu():
    """mouse right click menu"""

    def on_setup_menus(web_view, menu):
        """
        add context menu to webview
        """
        if not isinstance(web_view.editor.currentField, int):
            return
        current_model_id = web_view.editor.note.note_type()['id']
        mconf = config.get_query_configs(current_model_id)
        qconfigs = mconf['query_configs']
        curr_flds = []
        names = []
        for i, cfg in enumerate(qconfigs):
            fields = cfg if isinstance(cfg, list) else cfg['fields']
            for mord, m in enumerate(fields):
                if m.get('word_checked', False):
                    word_ord = mord
                    break
            if web_view.editor.currentField != word_ord:
                each = fields[web_view.editor.currentField]
                ignore = each.get('ignore', False)
                if not ignore:
                    dict_unique = each.get('dict_unique', '').strip()
                    dict_fld_ord = each.get('dict_fld_ord', -1)
                    fld_ord = each.get('fld_ord', -1)
                    if dict_unique and dict_fld_ord != -1 and fld_ord != -1:
                        svc = service_pool.get(dict_unique)
                        if svc and svc.support:
                            name = svc.title + ' :-> ' + svc.fields[dict_fld_ord]
                            if name not in names:
                                names.append(name)
                                curr_flds.append({'name': name, 'default': i})
                        service_pool.put(svc)

        submenu = menu.addMenu(_('QUERY'))
        submenu.addAction(
            _('ALL_FIELDS'), lambda: query_from_editor_fields(web_view.editor))  # ,QKeySequence(my_shortcut))
        if len(curr_flds) > 0:
            # quer hook method
            def query_from_editor_hook(i):
                mconf = config.get_query_configs(current_model_id)
                maps_old_def = mconf.get('default', 0)
                set_options_def(current_model_id, i)
                query_from_editor_fields(web_view.editor, fields=[web_view.editor.currentField])
                set_options_def(current_model_id, maps_old_def)

            # sub menu
            # flds_menu = submenu.addMenu(_('CURRENT_FIELDS'))
            submenu.addSeparator()
            for c in curr_flds:
                submenu.addAction(
                    c['name'], lambda i=c['default']: query_from_editor_hook(i))
            submenu.addSeparator()
        submenu.addAction(_("OPTIONS"), lambda: show_options(web_view, web_view.editor.note.note_type()['id']))

    gui_hooks.editor_will_show_context_menu.append(on_setup_menus)
