# -*- coding: utf-8 -*-

import json
import os
import re
import sqlite3
from contextlib import closing
import threading
import sys
# zlib compression is used for engine version >=2.0
import zlib
from io import BytesIO
from struct import pack, unpack

from .readmdict import MDD, MDX

# import chardet

# LZO compression is used for engine version < 2.0
try:
    import lzo
except ImportError:
    lzo = None
    #print("LZO compression support is not available")

# 2x3 compatible
if sys.hexversion >= 0x03000000:
    unicode = str

version = '1.1'


class IndexBuilder(object):
    #todo: enable history
    def __init__(self,
                 fname,
                 encoding="",
                 passcode=None,
                 force_rebuild=False,
                 enable_history=False,
                 sql_index=True,
                 check=False):
        self._tlocal_mdx_db_conn = threading.local()
        self._tlocal_mdd_db_conn = threading.local()
        self._mdx_file = fname
        self._mdd_file = ""
        self._encoding = ''
        self._stylesheet = {}
        self._title = ''
        self._version = ''
        self._description = ''
        self._sql_index = sql_index
        self._check = check
        _filename_base, _file_extension = os.path.splitext(fname)
        assert (_file_extension == '.mdx')
        assert (os.path.isfile(fname))
        self._mdx_db_path = _filename_base + ".mdx.db"

        build_mdx_index = False

        try:
            with closing(sqlite3.connect(self._mdx_db_path)) as conn:
                #判断有无版本号
                self._version = self._query_meta(conn, "version")
                ################# if not version in fo #############
                if not self._version:
                    print("*** version info not found, rebuilding!")
                    build_mdx_index = True
                else:
                    self._encoding = self._query_meta(conn, "encoding")
                    self._stylesheet = json.loads(self._query_meta(conn, "stylesheet"))
                    self._title = self._query_meta(conn, "title")
                    self._description = self._query_meta(conn, "description")
        except Exception as e:
            build_mdx_index = True

        if force_rebuild or build_mdx_index:     
            mdx = MDX(self._mdx_file)
            self._make_md_index(mdx, self._mdx_db_path, unique=False)
            self._make_mdx_meta(mdx, self._mdx_db_path)

        if os.path.isfile(_filename_base + ".mdd"):
            self._mdd_file = _filename_base + ".mdd"
            self._mdd_db_path = _filename_base + ".mdd.db"
            if not os.path.isfile(self._mdd_db_path):
                self._make_md_index(MDD(self._mdd_file), self._mdd_db_path, unique=True)

    
    def __del__(self):
        if hasattr(self._tlocal_mdx_db_conn, "connection"):
            self._tlocal_mdx_db_conn.connection.close()
        if hasattr(self._tlocal_mdd_db_conn, "connection"):
            self._tlocal_mdd_db_conn.connection.close()

    def _query_meta(self, conn, key):
        cursor = conn.execute(f'SELECT * FROM META WHERE key = ?', (key,))
        for cc in cursor:
            return cc[1]
        return ''
    
    def _replace_stylesheet(self, txt):
        # substitute stylesheet definition
        encoding = 'utf-8'
        if isinstance(txt, bytes):
            # encode_type = chardet.detect(txt)
            # encoding = encode_type['encoding']
            txt = txt.decode(encoding)
        txt_list = re.split(r'`\d+`', txt)
        txt_tag = re.findall(r'`\d+`', txt)
        txt_styled = txt_list[0]
        for j, p in enumerate(txt_list[1:]):
            style = self._stylesheet[txt_tag[j][1:-1]]
            if p and p[-1] == '\n':
                txt_styled = txt_styled + style[0] + p.rstrip(
                ) + style[1] + '\r\n'
            else:
                txt_styled = txt_styled + style[0] + p + style[1]
        return txt_styled.encode(encoding)

    def _make_mdx_meta(self, mdx, db_path):
        meta = mdx.get_meta()
        _stylesheet = json.dumps(meta['stylesheet'])

        with closing(sqlite3.connect(db_path)) as conn:
            with conn:
                # build the metadata table
                c = conn.cursor()
                c.execute('''CREATE TABLE META  (key TEXT, value TEXT)''')

                #for k,v in meta:
                #    c.execute(
                #    'INSERT INTO META VALUES (?,?)',
                #    (k, v)
                #    )

                c.executemany('INSERT INTO META VALUES (?,?)',
                            [('encoding', meta['encoding']),
                            ('stylesheet', _stylesheet),
                            ('title', meta['title']),
                            ('description', meta['description']),
                            ('version', version)])


        self._encoding = meta['encoding']
        self._stylesheet = json.loads(_stylesheet)
        self._title = meta['title']
        self._description = meta['description']

    def _make_md_index(self, md, db_path, unique):
        if os.path.exists(db_path):
            os.remove(db_path)
        self._mdd_db_path = db_path
        index_list = md.get_index(check_block=self._check)
        print(f'_make_md_index {db_path} index list size {len(index_list)}')
        with closing(sqlite3.connect(db_path)) as conn:
            print(f"*** conn {conn}")
            with conn:
                c = conn.cursor()
                c.execute(f''' CREATE TABLE MDX_INDEX
                    (key_text text not null,
                        file_pos integer,
                        compressed_size integer,
                        decompressed_size integer,
                        record_block_type integer,
                        record_start integer,
                        record_end integer,
                        offset integer
                        )''')
                if self._sql_index or unique:
                    c.execute(f'''CREATE {"UNIQUE" if unique else ""} INDEX IF NOT EXISTS key_index ON MDX_INDEX (key_text)''')
                    
                tuple_list = [(item['key_text'], item['file_pos'],
                            item['compressed_size'], item['decompressed_size'],
                            item['record_block_type'], item['record_start'],
                            item['record_end'], item['offset'])
                            for item in index_list]
                c.executemany('INSERT INTO MDX_INDEX VALUES (?,?,?,?,?,?,?,?)',
                            tuple_list)

                    
    def get_connection(self, _local, db_path) -> sqlite3.Connection:
        """Retrieves or creates a thread-unique SQLite connection."""
        if not hasattr(_local, "connection"):
            # check_same_thread=True is default, reinforcing thread safety
            _local.connection = sqlite3.connect(
                db_path,
                timeout=20.0  # Prevents immediate locking errors under concurrency
            )
            # Enable foreign keys per connection
            _local.connection.execute("PRAGMA foreign_keys = ON;")
        return _local.connection
    
    @staticmethod
    def get_data_by_index(fmdx, index):
        fmdx.seek(index['file_pos'])
        record_block_compressed = fmdx.read(index['compressed_size'])
        record_block_type = record_block_compressed[:4]
        record_block_type = index['record_block_type']
        decompressed_size = index['decompressed_size']
        #adler32 = unpack('>I', record_block_compressed[4:8])[0]
        if record_block_type == 0:
            _record_block = record_block_compressed[8:]
            # lzo compression
        elif record_block_type == 1:
            if lzo is None:
                raise Exception("LZO compression is not supported")
                # decompress
            header = b'\xf0' + pack('>I', index['decompressed_size'])
            _record_block = lzo.decompress(
                record_block_compressed[8:],
                initSize=decompressed_size,
                blockSize=1308672)
            # zlib compression
        elif record_block_type == 2:
            # decompress
            _record_block = zlib.decompress(record_block_compressed[8:])
        else:
            raise ValueError(f"Unsupported record block type: {record_block_type}")
        
        data = _record_block[index['record_start'] -
                             index['offset']:index['record_end'] -
                             index['offset']]
        return data

    def get_md_by_index(self, fmdx, index, decode):
        data = self.get_data_by_index(fmdx, index)
        
        if not decode:
            return data
        
        record = data.decode(self._encoding, errors='ignore').strip(u'\x00').encode('utf-8')
        if self._stylesheet:
            record = self._replace_stylesheet(record)
        record = record.decode('utf-8')
        return record

    @staticmethod
    def lookup_indexes(conn, keyword, ignorecase=None):
        indexes = []
        if ignorecase:
            sql = 'SELECT * FROM MDX_INDEX WHERE lower(key_text) = lower(?)'
        else:
            sql = 'SELECT * FROM MDX_INDEX WHERE key_text = ?'
        # with sqlite3.connect(db) as conn:  # leaks fd hanlder
        with conn:
            cursor = conn.execute(sql, (keyword,))
            for result in cursor:
                index = {}
                index['file_pos'] = result[1]
                index['compressed_size'] = result[2]
                index['decompressed_size'] = result[3]
                index['record_block_type'] = result[4]
                index['record_start'] = result[5]
                index['record_end'] = result[6]
                index['offset'] = result[7]
                indexes.append(index)
        return indexes

    def md_lookup(self, index_db_conn, mdict_file, keyword, decode, ignorecase=None):
        lookup_result_list = []
        indexes = self.lookup_indexes(index_db_conn, keyword, ignorecase)
        with open(mdict_file, 'rb') as md_file:
            for index in indexes:
                lookup_result_list.append(self.get_md_by_index(md_file, index, decode))
        return lookup_result_list
    
    def mdx_lookup(self, keyword, ignorecase=None):
        conn = self.get_connection(self._tlocal_mdx_db_conn, self._mdx_db_path)
        return self.md_lookup(conn, self._mdx_file, keyword, True)

    def mdd_lookup(self, keyword, ignorecase=None):
        conn = self.get_connection(self._tlocal_mdd_db_conn, self._mdd_db_path)
        return self.md_lookup(conn, self._mdd_file, keyword, False)

    @staticmethod
    def get_keys(conn, query=''):
        if not conn:
            return []

        if query:
            if '*' in query:
                query = query.replace('*', '%')
            else:
                query = query + '%'
            sql = 'SELECT key_text FROM MDX_INDEX WHERE key_text LIKE ?'
        else:
            sql = 'SELECT key_text FROM MDX_INDEX'

        with conn:
            cursor = conn.execute(sql, (query,)) if query else conn.execute(sql)
            keys = [item[0] for item in cursor]
            return keys

    def get_mdx_keys(self, query=''):
        conn = self.get_connection(self._tlocal_mdx_db_conn, self._mdx_db_path)
        return self.get_keys(conn, query)

    def get_mdd_keys(self, query=''):
        conn = self.get_connection(self._tlocal_mdd_db_conn, self._mdd_db_path)
        return self.get_keys(conn, query)


# mdx_builder = IndexBuilder("oald.mdx")
# text = mdx_builder.mdx_lookup('dedication')
# keys = mdx_builder.get_mdx_keys()
# keys1 = mdx_builder.get_mdx_keys('abstrac')
# keys2 = mdx_builder.get_mdx_keys('*tion')
# for key in keys2:
#   text = mdx_builder.mdx_lookup(key)[0]
# pass
