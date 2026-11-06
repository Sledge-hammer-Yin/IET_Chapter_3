"""Apply traceable calibration/sampling fixes to this private GLIO checkout."""
import hashlib
import json
from pathlib import Path
import subprocess
import yaml

ROOT=Path('/data/users/taslab_zxp')
SETUP=ROOT/'projects/GLIO_setup'
REPO=ROOT/'projects/GLIO_ws/src/GLIO'
PROFILE=SETUP/'profiles/calibrated_v2'
PROFILE.mkdir(parents=True,exist_ok=True)
assert subprocess.check_output(['git','-C',str(REPO),'rev-parse','HEAD'],text=True).strip()=='332d19ff641f2ada9d9d75f2a6dab013d6015f76'
changes={}
def replace(path,old,new,count=1):
    text=changes.get(path,path.read_text())
    if text.count(old)!=count:
        raise RuntimeError('Unexpected source match count: '+str(path))
    changes[path]=text.replace(old,new)

header=REPO/'GLIO/include/factors/dd_psr_factor.hpp'
replace(header,'const double &_DDpsrThreshold):','const double &_DDpsrThreshold, const Eigen::Vector3d &_lever_arm_local = Eigen::Vector3d::Zero()):')
replace(header,'DDpsrThreshold(_DDpsrThreshold)\n','DDpsrThreshold(_DDpsrThreshold), lever_arm_local(_lever_arm_local)\n')
replace(header,'Eigen::Vector3d lever_arm_T = Eigen::Vector3d::Zero();','const Eigen::Vector3d lever_arm_T = lever_arm_local;')
replace(header,'Eigen::Vector3d ecefRefP, Station_pos;','Eigen::Vector3d ecefRefP, Station_pos, lever_arm_local;')
estimator=REPO/'GLIO/src/Estimator.cpp'
replace(estimator,'identity_weight_matrix, mPrn, ts_ratio, Station_pos, DDpsrThreshold);','identity_weight_matrix, mPrn, ts_ratio, Station_pos, DDpsrThreshold, lever_arm_T);')
replace(estimator,'float gps_x = thisGPS.pose.pose.position.x;\n                float gps_y = thisGPS.pose.pose.position.y;\n                float gps_z = thisGPS.pose.pose.position.z;',
'''// The PVT solution is at the antenna; graph poses are at the IMU.
                const PointPoseInfo &imu_pose = pose_info_keyframe->points[proc_kf_idx];
                const Eigen::Quaterniond imu_rotation(imu_pose.qw, imu_pose.qx, imu_pose.qy, imu_pose.qz);
                const Eigen::Vector3d antenna_offset = imu_rotation.normalized() * lever_arm_t;
                float gps_x = thisGPS.pose.pose.position.x - antenna_offset.x();
                float gps_y = thisGPS.pose.pose.position.y - antenna_offset.y();
                float gps_z = thisGPS.pose.pose.position.z - antenna_offset.z();''')
replace(estimator,'GNSSAdded = true;\n                last_GNSS_add_pos',
'''std::ofstream audit(result_path + "lc_gnss_factors.csv", std::ios::app);
                audit << std::fixed << std::setprecision(8)
                      << pose_info_keyframe->points[proc_kf_idx].time << ','
                      << gps_x << ',' << gps_y << ',' << gps_z << '\\n';
                GNSSAdded = true;
                last_GNSS_add_pos''')
# iomanip is used elsewhere by transitive includes, but declare it directly.
replace(estimator,'#include <random>','#include <random>\n#include <iomanip>')
rng=REPO/'GLIO/include/utils/random_generator.hpp'
replace(rng,'namespace common\n{',
'''namespace common
{
    inline unsigned int experimentSeed()
    {
        const char *seed = ::getenv("GLIO_RANDOM_SEED");
        return seed ? static_cast<unsigned int>(::strtoul(seed, nullptr, 10)) : std::random_device{}();
    }''')
replace(rng,'m_random_engine( std::random_device{}() )','m_random_engine( experimentSeed() )',count=2)

backup=PROFILE/'upstream'
for path,text in changes.items():
    relative=path.relative_to(REPO)
    original=backup/relative
    original.parent.mkdir(parents=True,exist_ok=True)
    if original.exists(): raise RuntimeError('Backup already exists; refusing repeated patch')
    original.write_bytes(path.read_bytes())
for path,text in changes.items():
    path.write_text(text)
(PROFILE/'source.patch').write_bytes(subprocess.check_output(['git','-C',str(REPO),'diff','--','GLIO/src/Estimator.cpp','GLIO/include/factors/dd_psr_factor.hpp','GLIO/include/utils/random_generator.hpp']))

config_dir=PROFILE/'configs'
config_dir.mkdir(exist_ok=True)
import xml.etree.ElementTree as ET
for mode in ['LC','TC_Pose','TC_Surface']:
    cfg=yaml.safe_load((SETUP/'configs'/f'{mode}.yaml').read_text())
    cfg['initialization'].update(lever_arm_x=0.0,lever_arm_y=0.86,lever_arm_z=-0.31)
    cfg['visualization']['RTKinLocal']=True
    (config_dir/f'{mode}.yaml').write_text(yaml.safe_dump(cfg,sort_keys=False))
    tree=ET.parse(SETUP/'configs'/f'{mode}.launch')
    for node in tree.getroot().findall('rosparam'):
        node.set('file',str(config_dir/f'{mode}.yaml'))
    tree.write(config_dir/f'{mode}.launch',encoding='utf-8',xml_declaration=True)

manifest=json.loads((SETUP/'reproduction_manifest.json').read_text())
manifest.update(profile='calibrated_v2', random_seed=42,
    calibration='Published IMU-to-antenna lever arm [0, 0.86, -0.31] m; LiDAR-to-IMU [0, 0, 0.28] m; estimated IMU poses are transferred to the SPAN reference point [0, 0, 0.14] m for evaluation.',
    reference_use='Offline position evaluation only. Reference positions and attitudes do not enter the estimator or the pose-point transfer.',
    actual_gnss_factors='Shared front end is LiDAR/IMU. LC adds gated DGNSS PVT factors. TC back ends use raw double-difference L1 pseudorange. Upstream sliding-window GNSS and Doppler blocks remain disabled.',
    initialization='Identical author-provided ECEF anchor and roll/pitch/yaw prior for all modes; derivation unverified. This is a shared-prior case study, not unaided initialization.',
    scope='Controlled three-mode single-sequence case study; not an exact reproduction of the published GLIO numerical results.',
    source_patch_sha256=hashlib.sha256((PROFILE/'source.patch').read_bytes()).hexdigest(),
    source_files={str(p.relative_to(REPO)):hashlib.sha256(p.read_bytes()).hexdigest() for p in changes},
    reference_point_body_m=[0.0,0.0,0.14],gnss_lever_arm_body_m=[0.0,0.86,-0.31],
    frozen_attitude_approximation='TC GNSS lever arm is rotated using the nearest estimated pose when a factor is assembled; its orientation is held fixed inside that position-only factor.')
(PROFILE/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('Controlled calibration/sampling profile and source patch saved:',PROFILE)
