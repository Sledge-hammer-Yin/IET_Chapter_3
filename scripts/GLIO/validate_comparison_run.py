"""Check a completed run without fitting or changing any trajectory."""
import csv
import hashlib
import json
import math
from pathlib import Path
import sys

root=Path('/data/users/taslab_zxp')
folder=Path(sys.argv[1])
mode=sys.argv[2]
output=root/'outputs/GLIO/Deep-Urban-1/Comparison_calibrated_v2'
assert folder.parent==output/'runs'
assert folder.name.startswith(mode+'_')
assert (folder/'requested_duration_seconds.txt').read_text().strip()=='0'
assert (folder/'playback_rate.txt').read_text().strip()=='1.0'
assert json.loads((folder/'backend_drain.json').read_text())['status']=='complete'
native=folder/('lc_result.csv' if mode=='LC' else 'tc_batch_result.csv')
rows=list(csv.reader(native.open()))
assert len(rows)>4000
assert all(len(row)==12 and all(math.isfinite(float(x)) for x in row) for row in rows)
assert float(rows[-1][0])-float(rows[0][0])>1500
if mode=='LC':
    factors=list(csv.reader((folder/'lc_gnss_factors.csv').open()))
    assert len(factors)>0,'LC must contain actual GNSS position factors'
else: factors=[]
print(json.dumps({'mode':mode,'run_dir':str(folder),'native_rows':len(rows),'lc_gnss_factors':len(factors),'validated':True}))
