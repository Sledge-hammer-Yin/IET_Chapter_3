"""Create separate per-mode configuration without editing the upstream source."""
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import yaml

ROOT = Path('/data/users/taslab_zxp')
SETUP = ROOT / 'projects/GLIO_setup'
REPO = ROOT / 'projects/GLIO_ws/src/GLIO'
DATA = ROOT / 'datasets/UrbanNav/Deep-Urban-1'
CONFIGS = SETUP / 'configs'
CONFIGS.mkdir(exist_ok=True)
config = yaml.safe_load((REPO / 'GLIO/config/config_urban_hk.yaml').read_text())
config['visualization']['GTinLocal'] = False
config['visualization']['RTKinLocal'] = False
config['Estimator']['save_pcd'] = False
config['Estimator']['loop_closure_on'] = False
modes = {
    'LC': (True, False, 0),
    'TC_Pose': (False, True, 0),
    'TC_Surface': (False, True, 1),
}
for mode, (lc, batch, level) in modes.items():
    cfg = yaml.safe_load(yaml.safe_dump(config))
    cfg['visualization']['LCinLocal'] = lc
    cfg['Estimator']['enable_batch_fusion'] = batch
    cfg['Estimator']['sms_fusion_level'] = level
    config_path = CONFIGS / (mode + '.yaml')
    config_path.write_text(yaml.safe_dump(cfg, default_flow_style=False, sort_keys=False))
    tree = ET.parse(str(REPO / 'GLIO/launch/run_urban_hk.launch'))
    launch = tree.getroot()
    launch.insert(0, ET.Element('arg', name='result_dir'))
    for node in list(launch):
        if node.tag == 'node' and node.get('pkg') == 'rviz':
            launch.remove(node)
        if node.tag == 'param' and node.get('name') == '/use_sim_time':
            node.set('value', 'false')
        if node.tag == 'rosparam':
            node.set('file', str(config_path))
        if node.tag == 'node' and node.get('type') in ('Preprocessing', 'LidarOdometry', 'Estimator', 'gnss_preprocessor_node'):
            node.set('required', 'true')
        if node.tag == 'node' and node.get('type') == 'Estimator':
            for param in node.findall('param'):
                if param.get('name') == 'result_path':
                    param.set('value', '$(arg result_dir)/')
        if node.tag == 'param':
            files = {
                'roverMeasureFile': DATA / 'gnss/20210521.medium-urban.whampoa.ublox.f9p.obs',
                'baseMeasureFile': DATA / 'gnss/hksc1410.21o',
                'EmpFile': DATA / 'gnss/hksc141g.nav',
            }
            if node.get('name') in files:
                node.set('value', str(files[node.get('name')]))
            if node.get('name') == 'out_folder':
                node.set('value', '$(arg result_dir)/rtklibResult.pos')
    tree.write(str(CONFIGS / (mode + '.launch')), encoding='utf-8', xml_declaration=True)

manifest = {
    'sequence': 'Deep-Urban-1',
    'glio_commit': '332d19ff641f2ada9d9d75f2a6dab013d6015f76',
    'host_os': 'Ubuntu 24.04.5',
    'container_os': 'Ubuntu 18.04 / ROS Melodic',
    'gtsam_version': '4.0.3',
    'initialization': 'Author-provided Deep-Urban-1 anchor and Euler angles retained; their original derivation is not verified.',
    'reference_use': 'Ground-truth topic excluded from replay; reference used for offline evaluation only.',
    'calibration': 'Author-provided GLIO IMU/LiDAR extrinsics and zero GNSS lever arm retained for the initial reproduction; audit lever-arm convention before book-quality comparisons.',
    'resource_policy': 'Four logical CPUs, nice 10, CPU-only, private ROS master port 11371.',
    'modes': {m: dict(LCinLocal=x[0], enable_batch_fusion=x[1], sms_fusion_level=x[2]) for m,x in modes.items()},
    'scope': 'A short run verifies operation only; book metrics require complete sequences and common evaluation epochs.',
}
(SETUP / 'reproduction_manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
print('Three headless configurations written to', CONFIGS)
