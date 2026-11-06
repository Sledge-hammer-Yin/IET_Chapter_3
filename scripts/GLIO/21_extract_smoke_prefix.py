"""Recover a real ROS-bag prefix from the downloaded first ZIP volume.

Only a separate processed file is written. The official archive is read-only.
This prefix is for functional verification, never full-sequence benchmarking.
"""
from pathlib import Path
import os
import struct
import zlib

root = Path('/data/users/taslab_zxp/datasets/UrbanNav/Deep-Urban-1')
source = root / 'rosbag/UrbanNav-HK_Whampoa-20210521_sensors.z01'
dest_dir = root / 'processed'
dest_dir.mkdir(exist_ok=True)
output = dest_dir / 'Deep-Urban-1_smoke_prefix.bag'
if output.exists():
    raise RuntimeError('Processed prefix already exists; refusing overwrite')
max_output = 7 * 1024**3
with source.open('rb') as stream, output.open('wb') as target:
    prefix = stream.read(65536)
    offset = prefix.find(b'PK\x03\x04')
    if offset < 0:
        raise ValueError('No ZIP local file header')
    fields = struct.unpack_from('<IHHHHHIIIHH', prefix, offset)
    method, name_len, extra_len = fields[3], fields[-2], fields[-1]
    name = prefix[offset+30:offset+30+name_len].decode('utf-8')
    print('Archive member:', name, 'compression method:', method, flush=True)
    if method != 8 or not name.endswith('.bag'):
        raise ValueError('Unexpected archive format')
    stream.seek(offset + 30 + name_len + extra_len)
    decoder = zlib.decompressobj(-15)
    written = 0
    while written < max_output:
        block = stream.read(1024*1024)
        if not block:
            raise RuntimeError('Downloaded prefix too short')
        plain = decoder.decompress(block)
        remaining = max_output-written
        target.write(plain[:remaining])
        written += min(len(plain), remaining)
        if decoder.eof:
            break
with output.open('r+b') as stream:
    if stream.read(13) != b'#ROSBAG V2.0\n':
        raise ValueError('Not a ROS bag V2.0 file')
    size = os.fstat(stream.fileno()).st_size
    cursor = 13
    last_complete = cursor
    records = 0
    while cursor + 4 <= size:
        stream.seek(cursor)
        header_size = struct.unpack('<I', stream.read(4))[0]
        if not 0 < header_size < 2**20 or cursor+8+header_size > size:
            break
        header = stream.read(header_size)
        data_size = struct.unpack('<I', stream.read(4))[0]
        next_record = cursor + 8 + header_size + data_size
        if next_record > size:
            break
        if records == 0:
            index_field = header.find(b'index_pos=')
            if index_field < 0:
                raise ValueError('No bag index field')
            stream.seek(cursor + 4 + index_field + len(b'index_pos='))
            stream.write(b'\x00'*8)
        last_complete = next_record
        cursor = next_record
        records += 1
    stream.truncate(last_complete)
print('Recovered complete top-level records:', records)
print('Processed prefix bytes:', last_complete)
print('Run native rosbag reindex before use:', output)
