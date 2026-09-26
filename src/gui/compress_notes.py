import base64
import re
import zlib
# import zstandard as zstd

from aqt import gui_hooks
from aqt import mw
from aqt.qt import QAction
from aqt.utils import showInfo, tooltip

from ..context import config, gui_processEvents
from ..lang import _

COMPRESS_PREFIX = "ZLIB::"
MIN_LENGTH = 80  # Minimum length required to trigger compression
LEN_COMPRESS_PREFIX = len(COMPRESS_PREFIX)

def compress_text(text: str) -> str:
    """Compresses plain text/HTML into a base64-encoded zlib string."""
    if not text or text.startswith(COMPRESS_PREFIX):
        return text
    compressed_bytes = zlib.compress(text.encode("utf-8"))
    b64_str = base64.b64encode(compressed_bytes).decode("ascii")
    return f"{COMPRESS_PREFIX}{b64_str}"


def decompress_text(text: str) -> str:
    """Decompresses a ZLIB:: tagged string back to original text."""
    if not text or not text.startswith(COMPRESS_PREFIX):
        return text
    try:
        if LEN_COMPRESS_PREFIX:
            raw_b64 = text[LEN_COMPRESS_PREFIX:]
        else:
            raw_b64 = text
        compressed_bytes = base64.b64decode(raw_b64)
        return zlib.decompress(compressed_bytes).decode("utf-8")
    except Exception:
        return text


# --- 1. Decompress fields when loaded into the Anki Editor ---
def on_editor_did_load_note(editor):
    """Decompresses field values when a note is opened in the Browser editor."""
    note = editor.note
    if not note:
        return

    modified = False
    for name, value in note.items():
        if value.startswith(COMPRESS_PREFIX):
            # Temporarily replace with decompressed text for human reading/editing
            note[name] = decompress_text(value)
            modified = True

    if modified:
        # Refresh the webview editor UI to display decompressed text
        editor.loadNoteKeepingFocus()
        # tooltip(_("Note Decompressed"), period=1000)


gui_hooks.editor_did_load_note.append(on_editor_did_load_note)


# --- 2. Compress fields before saving changes in the Editor ---
def on_editor_will_save_note(txt, editor):
    if not config.auto_compress_notes:
        return txt
    if len(txt) >= MIN_LENGTH and not txt.startswith(COMPRESS_PREFIX):
        txt = compress_text(txt)
        # tooltip(_("Note Compressed."), period=1000)

    return txt

# Hook before note saves from browser or add screen
gui_hooks.editor_will_munge_html.append(on_editor_will_save_note)


# --- 3. Manual Batch Compress Action (Edit Menu) ---
# action: compress or decompress
def zlib_process_selected_notes(browser, action: str):
    """Batch compresses selected notes in the Browser list."""
    if action not in ['compress', 'decompress']:
        raise Exception(f"Unknown action {action}")
    
    note_ids = browser.selectedNotes()
    if not note_ids:
        showInfo("Please select at least one note to compress.")
        return

    # mw.checkpoint(f"Process Notes: {action}")
    mw.progress.start(label=f"Processing notes: {action}...", max=len(note_ids))

    updated_count = 0
    for idx, nid in enumerate(note_ids):
        mw.progress.update(value=idx)
        note = mw.col.get_note(nid)
        modified = False

        for name, value in note.items():
            if action == 'compress' and len(value) >= MIN_LENGTH and not value.startswith(COMPRESS_PREFIX):
                note[name] = compress_text(value)
                modified = True
            elif action == 'decompress' and value.startswith(COMPRESS_PREFIX):
                note[name] = decompress_text(value)
                modified = True

        if modified:
            mw.col.update_note(note)
            updated_count += 1
            if updated_count % 100 == 0:
                gui_processEvents()

    mw.progress.finish()
    mw.reset()
    showInfo(f"Updated {updated_count} of {len(note_ids)} selected notes.")

def toggle_auto_compress(checked: bool):
    tooltip(f'Auto Compressed {"Enabled" if checked else "Disabled"}', period=1000)

    config.update({
        'auto_compress_notes': checked
    })

def setup_browser_menu(browser, menu):
    if not menu:
        menu = browser.form.menuEdit

    # Checkable menu action for auto-compression
    auto_action = QAction("Enable Auto-Compress on Edit", browser)
    auto_action.setCheckable(True)
    tooltip(f'Auto Compressed {"Enabled" if config.auto_compress_notes else "Disabled"}', period=3000)
    auto_action.setChecked(config.auto_compress_notes)
    auto_action.triggered.connect(toggle_auto_compress)
    menu.addAction(auto_action)
    
    action = QAction("Compress Selected Notes", browser)
    action.triggered.connect(lambda: zlib_process_selected_notes(browser, 'compress'))
    menu.addAction(action)

    action = QAction("Decompress Selected Notes", browser)
    action.triggered.connect(lambda: zlib_process_selected_notes(browser, 'decompress'))
    menu.addAction(action)


# gui_hooks.browser_will_show.append(setup_browser_menu)


# --- 4. Decompress fields during Reviewer display ---
def on_card_will_show(text: str, card, kind: str) -> str:
    if COMPRESS_PREFIX in text:
        pattern = re.compile(rf"{re.escape(COMPRESS_PREFIX)}[A-Za-z0-9+/=]+")
        return pattern.sub(lambda m: decompress_text(m.group(0)), text)
    return text


gui_hooks.card_will_show.append(on_card_will_show)