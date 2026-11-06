"""Keep original sensor bytes and timestamps; remove unsupported startup scans."""
from __future__ import print_function
import collections
import hashlib
import json
import os
import struct
import sys
import rosbag

root = '/data/users/taslab_zxp/datasets/UrbanNav/Deep-Urban-1'
source = root+'/rosbag/UrbanNav-HK_Whampoa-20210521_sensors.bag'
dest = root+'/processed/Deep-Urban-1_GLIO_input.bag'
manifest = root+'/processed/GLIO_input_manifest.json'
if os.path.exists(dest):
    raise RuntimeError('Refusing to overwrite an existing prepared input')
counts = collections.Counter()
hashes = {}
first_imu = None
dropped = []


def raw_bytes(raw):
    value = raw[1]
    return value if isinstance(value, bytes) else value[0]


with rosbag.Bag(str(source)) as original, rosbag.Bag(str(dest), 'w', chunk_threshold=4*1024*1024) as prepared:
    for topic, raw, timestamp in original.read_messages(topics=['/imu/data','/velodyne_points','/time_reference'], raw=True):
        data = raw_bytes(raw)
        if topic == '/imu/data' and first_imu is None:
            message = raw[-1]()
            message.deserialize(data)
            first_imu = message.header.stamp.to_nsec()
        if topic == '/velodyne_points':
            message = raw[-1]()
            message.deserialize(data)
            if first_imu is None or message.header.stamp.to_nsec() < first_imu:
                dropped.append({'record_time_ns':timestamp.to_nsec(), 'header_time_ns':message.header.stamp.to_nsec()})
                continue
        prepared.write(topic, raw, timestamp, raw=True)
        hashes.setdefault(topic, hashlib.sha256()).update(struct.pack('<Q',timestamp.to_nsec())+data)
        counts[topic] += 1
        if counts['/imu/data'] and counts['/imu/data'] % 100000 == 0 and topic == '/imu/data':
            print('IMU messages written:',counts['/imu/data'])
            sys.stdout.flush()
check_counts = collections.Counter()
check_hashes = {}
with rosbag.Bag(str(dest)) as prepared:
    for topic, raw, timestamp in prepared.read_messages(raw=True):
        check_counts[topic] += 1
        check_hashes.setdefault(topic, hashlib.sha256()).update(struct.pack('<Q',timestamp.to_nsec())+raw_bytes(raw))
if counts != check_counts or any(hashes[k].hexdigest() != check_hashes[k].hexdigest() for k in hashes):
    raise RuntimeError('Prepared message identity check failed')
report = {'source':str(source), 'prepared':str(dest), 'first_imu_header_ns':first_imu,
          'dropped_startup_lidar_scans':dropped, 'retained_message_counts':dict(counts),
          'retained_message_sha256':{k:h.hexdigest() for k,h in hashes.items()},
          'message_bytes_verified':True,
          'policy':'Center LiDAR, original 400 Hz IMU, and time reference only. Remove only LiDAR scans earlier than the first IMU header. Retained message bytes and timestamps are unchanged. Original archive and bag are untouched.'}
with open(manifest,'w') as stream:
    stream.write(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
sys.stdout.flush()
