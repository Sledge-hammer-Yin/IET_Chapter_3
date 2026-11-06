"""Sample only native GLIO children of one private roslaunch process."""
import argparse
import csv
import json
import os
from pathlib import Path
import time

parser=argparse.ArgumentParser()
parser.add_argument('launch_pid',type=int)
parser.add_argument('run_dir',type=Path)
args=parser.parse_args()
names={'Estimator','LidarOdometry','Preprocessing','gnss_preprocess'}
ticks=os.sysconf('SC_CLK_TCK')
page=os.sysconf('SC_PAGE_SIZE')
peak=0.0
cpu={}
started=time.monotonic()
count=0
with (args.run_dir/'resource_samples.csv').open('w',newline='') as stream:
    writer=csv.writer(stream)
    writer.writerow(['elapsed_s','combined_native_rss_mib','sampled_native_cpu_seconds'])
    while True:
        table={}
        for path in Path('/proc').iterdir():
            if not path.name.isdigit(): continue
            try:
                if path.stat().st_uid!=os.getuid(): continue
                fields=(path/'stat').read_text().rsplit(')',1)[1].split()
                table[int(path.name)]=(int(fields[1]),fields,(path/'comm').read_text().strip())
            except (OSError,ValueError): pass
        if args.launch_pid not in table or table[args.launch_pid][1][0]=='Z': break
        rss=0.0
        for pid,(parent,fields,name) in table.items():
            if name not in names: continue
            ancestors=set()
            while parent in table and parent not in ancestors and parent!=args.launch_pid:
                ancestors.add(parent); parent=table[parent][0]
            if parent!=args.launch_pid: continue
            rss+=int(fields[21])*page/1024.0**2
            key=(pid,fields[19])
            cpu[key]=max(cpu.get(key,0.0),(int(fields[11])+int(fields[12]))/float(ticks))
        peak=max(peak,rss)
        writer.writerow([round(time.monotonic()-started,3),round(rss,3),round(sum(cpu.values()),3)])
        stream.flush()
        count+=1
        time.sleep(5)
report={'sample_interval_s':5,'samples':count,'observed_wall_s':time.monotonic()-started,
        'sampled_peak_combined_native_rss_mib':peak,'sampled_native_cpu_s':sum(cpu.values()),
        'scope':'Estimator, LidarOdometry, Preprocessing, and GNSS preprocessor descended from this roslaunch only; sampled values, not exact OS peaks.'}
(args.run_dir/'resources.json').write_text(json.dumps(report,indent=2)+'\n')
