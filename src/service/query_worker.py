import traceback
from collections import defaultdict
import multiprocessing as mp
import queue
import unicodedata
import re

from ..libs.snowballstemmer import stemmer
from .. import context
from ..context import config
from . import Service, LocalService, service_manager, QueryResult, WordNotFoundError
from ..utils import QueryStat
from ..lang import _

def strip_combining(txt):
    """Return txt with all combining characters removed."""
    norm = unicodedata.normalize('NFKD', txt)
    return u"".join([c for c in norm if not unicodedata.combining(c)])


def query_flds(note_fields_len_list, word_ord, word, cfg_qfields, qfields:list[int]) -> tuple[defaultdict[int, QueryResult], QueryStat, list]:
    """
    Query fields of single note
    """
    # traceback.print_stack()

    # print(f"qfields {qfields}")
    # print(f'query_flds {word_ord}, {word}, {fields}')
    if not word:
        # raise InvalidWordException
        raise Exception(f'Empty Word')

    if config.ignore_accents:
        word = strip_combining(word)

    # progress.update_title(u'Querying [[ %s ]]' % word)

    services: dict[str, Service] = {}
    tasks = []
    qstat = QueryStat()
    qstat.note_count = 1

    for i, field in enumerate(cfg_qfields):
        if i == word_ord:
            continue
        if i >= len(note_fields_len_list):
            break
        # ignore field
        ignore = field.get('ignore', False)
        if ignore:
            continue
        # skip valued
        skip = field.get('skip_valued', False)
        if skip and note_fields_len_list[i] != 0:
            qstat.field_skip_count += 1
            continue
        # cloze
        cloze = field.get('cloze_word', False)
        # normal
        dict_unique = field.get('dict_unique', '').strip()
        dict_fld_ord = field.get('dict_fld_ord', -1)
        fld_ord = field.get('fld_ord', -1)

        # print(f"---dict_unique {dict_unique} dict_fld_ord {dict_fld_ord} fld_ord {fld_ord}")
        if not dict_unique or dict_fld_ord < 0 or fld_ord < 0:
            print(f"---dict_unique {dict_unique} dict_fld_ord {dict_fld_ord} fld_ord {fld_ord}")
            continue
        # print(f"---qfields {qfields}")
        if qfields and fld_ord not in qfields:
            print(f'---word `{word}` fld_ord `{fld_ord}` not in qfields {qfields}')
            continue

        svc = services.get(dict_unique, None)
        if svc is None:
            svc = service_manager.get(dict_unique)
            if svc and svc.support:
                services[dict_unique] = svc
            else:
                print(f'*** Error: service `{dict_unique}` `{svc}` is not supported')

        # print(f"---service {svc} support {svc.support} for {dict_unique}")
        if svc and svc.support:
            tasks.append({
                'dict_uniq': dict_unique,
                'word': word,
                'dict_fld_ord': dict_fld_ord,
                'fld_ord': fld_ord,
                'cloze': cloze,
            })

    # print(f'---query_flds tasks {tasks}')
    if not tasks:
        print(f"*** Error: No tasks generated for word `{word}`")

    missed_css_info_list = list()

    result = defaultdict()
    for task in tasks:
        try:
            service = services.get(task['dict_uniq'], None)
            qr = service.active(task['dict_fld_ord'], task['word'])
            # print(f"--- qr {str(qr)[:100]}")
            if qr:
                if isinstance(service, LocalService):
                    # print(f'--- {service}.missed_css {service.missed_css}')
                    for css in service.missed_css:
                        missed_css_info_list.append({
                            'dict_path': service.dict_path,
                            'title': service.title,
                            'file': css
                        })
                if task['cloze']:
                    qr['result'] = cloze_deletion(qr['result'], word)
                result.update({task['fld_ord']: qr})
                qstat.field_success_count += 1
            else:
                qstat.field_no_result_count += 1
        except WordNotFoundError as e:
            # print(f'{e}')
            pass
        except Exception as e:
            qstat.field_error_count += 1
            print(traceback.format_exc())
            print(_("NO_QUERY_WORD"), e)
        finally:
            service_manager.put(service)

    return result, qstat, missed_css_info_list


def cloze_deletion(text, cloze):
    """create cloze deletion text"""
    text = text.replace('’', '\'')
    result = text
    offset = 0
    term = _stemmer.stemWord(cloze).lower()

    terms = re.finditer(r"\b[\w'-]*\b", text)
    tags = re.finditer(r"<[^>]+>", text)
    for m in terms:
        s = m.start()
        e = m.end()
        f = False
        for tag in tags:
            if s >= tag.start() and e <= tag.end():
                f = True
                break
        if f:
            continue
        word = text[s:e]
        if _stemmer.stemWord(word).lower() == term:
            ln = len(cloze)
            w = word
            if w[:ln].lower() == cloze.lower():
                e = s + ln
                w = word[:ln]
            result = result[:s + offset] + (
                config.cloze_str % w) + result[e + offset:]
            offset += len(config.cloze_str) - 2
    return result

_stemmer = stemmer('english')


# import os
# from pympler import asizeof, muppy, summary

# def print_mem_sumary():
#     # --- Profile memory footprint before worker exits ---
#     all_objects = muppy.get_objects()
#     sum_data = summary.summarize(all_objects)

#     print(f"=== Worker PID {os.getpid()} Memory Footprint ===")
#     summary.print_(sum_data, limit=10)

# def print_top_mem():
#     top_n = 10
#     top_objects = sorted(muppy.get_objects(), key=asizeof.asizeof, reverse=True)[:top_n]
#     print(f"[PID {os.getpid()}] Top {top_n} Objects by Size:")
#     for obj in top_objects:
#         size_mb = asizeof.asizeof(obj, limit=10) / (1024 * 1024)
#         print(f"  - {type(obj).__name__}: {size_mb:.2f} MB")

# def _init_worker(parent_sys_path):
#     """Runs inside the spawned child process before worker execution begins."""
#     # Restore parent sys.path entries that are missing in the spawned process
#     for path in parent_sys_path:
#         if path not in sys.path:
#             sys.path.insert(0, path)

def process_worker_loop(stop_event, task_queue: mp.Queue, result_queue: mp.Queue, query_fields, mdx_backend_lock, llm_lock):
    """
    Top-level worker function executed in isolated child processes.
    Pulls lightweight note payload data, performs queries, and sends back results.
    """
    print(f"--- worker STARTED {mp.current_process()}")
    context.set_worker_lock('mdx_backend', mdx_backend_lock)
    context.set_worker_lock('llm', llm_lock)
    # print(f'---process_worker_loop col_path {col_path}')
    n = 0
    while not stop_event.is_set():
        # try:
        #     n += 1
        #     if n % 50 == 0:
        #         print_top_mem()
        # except:
        #     traceback.print_exc()

        try:
            # Poll task queue
            payload = task_queue.get(block=True, timeout=0.1)
        except queue.Empty:
            break

        if payload is None:  # Poison pill to gracefully shut down worker
            break


        note_id, note_fields_len_list, word_ord, word, cfg_qfields = payload
        # note = col.get_note(note_id)
        # print(f'--- note_id {note_id} payload {payload}')

        try:
            # Reconstruction or dummy encapsulation if query_flds needs field data
            # Adjust query_flds call depending on whether it works with dict or Note
            results, qstat, missed_css_info_list = query_flds(note_fields_len_list, word_ord, word, cfg_qfields, query_fields)
            result_queue.put(('success', (note_id, results, qstat, missed_css_info_list)))
            # result_queue.put(('success', (note_id, pickle.dumps(results), pickle.dumps(qstat), missed_css_info_list)))
        # except InvalidWordException:
        #     traceback.print_exc()
        #     result_queue.put(('invalid_word', (note_id,)))
        except Exception as e:
            traceback.print_exc()
            result_queue.put(('error', (note_id, str(e), traceback.format_exc())))

    print(f'--- worker {mp.current_process()} exit')
    # col.close()
