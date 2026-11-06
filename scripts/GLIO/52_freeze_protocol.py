"""Freeze the shared experiment inputs and evaluation rules before any full run."""
import hashlib
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET
import yaml

ROOT=Path('/data/users/taslab_zxp')
SETUP=ROOT/'projects/GLIO_setup'
PROFILE=SETUP/'profiles/calibrated_v2'
OUTPUT=ROOT/'outputs/GLIO/Deep-Urban-1/Comparison_calibrated_v2'
OUTPUT.mkdir(exist_ok=True)
if (OUTPUT/'protocol.json').exists():
    raise RuntimeError('A frozen protocol already exists; refusing overwrite')
def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(4*1024*1024),b''): h.update(block)
    return h.hexdigest()
def asset(path):
    stat=path.stat()
    return {'path':str(path),'bytes':stat.st_size,'mtime_ns':stat.st_mtime_ns,'sha256':sha(path)}
baseline=None
config_hashes={}
for mode in ['LC','TC_Pose','TC_Surface']:
    path=PROFILE/'configs'/f'{mode}.yaml'
    config=yaml.safe_load(path.read_text())
    controls={key:config[section].pop(key) for section,key in [('visualization','LCinLocal'),('Estimator','enable_batch_fusion'),('Estimator','sms_fusion_level')]}
    assert controls=={'LCinLocal':mode=='LC','enable_batch_fusion':mode!='LC','sms_fusion_level':int(mode=='TC_Surface')}
    if baseline is None: baseline=config
    else: assert config==baseline,'Unexpected shared configuration difference'
    assert config['visualization']['RTKinLocal'] is True
    assert config['initialization']['lever_arm_y']==0.86
    tree=ET.parse(PROFILE/'configs'/f'{mode}.launch')
    common=[(p.get('name'),p.get('type'),p.get('value')) for p in tree.getroot().findall('param')]
    if mode=='LC': reference_launch=common
    else: assert common==reference_launch
    config_hashes[mode]={'yaml':sha(path),'launch':sha(PROFILE/'configs'/f'{mode}.launch')}
data=ROOT/'datasets/UrbanNav/Deep-Urban-1'
prepared=json.loads((data/'processed/GLIO_input_manifest.json').read_text())
source_info=yaml.safe_load((data/'rosbag/source_bag_info.yaml').read_text())
paths=[data/'processed/Deep-Urban-1_GLIO_input.bag',data/'gnss/20210521.medium-urban.whampoa.ublox.f9p.obs',data/'gnss/hksc1410.21o',data/'gnss/hksc141g.nav',data/'ground_truth/UrbanNav_whampoa_raw.txt',data/'calibration/extrinsic.yaml',data/'calibration/xsens_imu_param.yaml']
assets={p.name:asset(p) for p in paths}
binary=ROOT/'projects/GLIO_ws/devel/lib/GLIO/Estimator'
manifest=json.loads((PROFILE/'manifest.json').read_text())
protocol={'version':'calibrated_v2','sequence':'Deep-Urban-1','modes':['LC','TC_Pose','TC_Surface'],
    'assets':assets,'configs':config_hashes,'estimator_binary':asset(binary),
    'container':asset(ROOT/'installers/apptainer/images/glio-melodic.sif'),
    'profile_manifest_sha256':sha(PROFILE/'manifest.json'),'source_files':manifest['source_files'],
    'feature_sampling_seed':42,'replay_rate':1.0,'duration_seconds':0,
    'resources':{'logical_cpus':'0-3','nice':10,'virtual_memory_limit_gib_per_process':24,'gpu':False},
    'evaluation':{'reference_point':'SPAN-CPT','body_T_span_translation_m':[0,0,0.14],
        'start_utc':float(math.ceil(prepared['first_imu_header_ns']/1e9+20)),
        'end_utc':float(math.floor(source_info['end'])-1),
        'settling_seconds':20,'max_interpolation_bracket_s':1.0,
        'main_epochs':'Intersection of the same fixed 1 Hz reference epochs valid in all three native outputs',
        'alignment':'None','reference_quality':'All available raw quality codes, with per-code results also reported',
        'rpe_interval_s':10},
    'shared_config':baseline,
    'limitations':['One full run per mode on one ground-vehicle sequence; no significance or universal-superiority claim.',
        'Shared supplied initial position/orientation prior, with unverified derivation; no truth fitted alignment or online reference input.',
        'Public antenna translation is manually measured (reported uncertainty about 0.1 m).',
        'Feature sampling seed is fixed, but asynchronous scheduling can still affect floating-point results.',
        'TC factors use a frozen nearest-estimated-attitude lever offset when assembled; rotational lever-arm Jacobians are not added.',
        'The upstream shared sliding-window GNSS and Doppler blocks are disabled; the active TC GNSS input is DD pseudorange.']}
(OUTPUT/'protocol.json').write_text(json.dumps(protocol,indent=2)+'\n')
(OUTPUT/'profile_manifest.json').write_bytes((PROFILE/'manifest.json').read_bytes())
(OUTPUT/'source.patch').write_bytes((PROFILE/'source.patch').read_bytes())
print('Protocol frozen:',OUTPUT/'protocol.json',flush=True)
