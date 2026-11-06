"""Independent geometric and time-matching checks for the evaluator."""
import ast
from pathlib import Path
import numpy as np
path=Path(__file__).with_name('compare_modes.py')
tree=ast.parse(path.read_text())
functions=[node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name in ['span_position','ecef','frame','statistics','interpolate_native']]
namespace={'np':np}
exec(compile(ast.Module(body=functions,type_ignores=[]),str(path),'exec'),namespace)
raw=np.zeros((4,12))
raw[:,6:9]=[[0,0,0],[0,90,0],[90,90,0],[0,0,90]]
expected=np.array([[0,0,.14],[.14,0,0],[0,.14,0],[0,-.14,0]])
np.testing.assert_allclose(namespace['span_position'](raw),expected,atol=1e-12)
origin=namespace['ecef'](np.array([0]),np.array([0]),np.array([0]))[0]
np.testing.assert_allclose(origin,[6378137,0,0],atol=1e-9)
np.testing.assert_allclose(namespace['frame'](origin),[[0,1,0],[0,0,1],[1,0,0]],atol=1e-12)
errors=np.tile([1.,2.,2.],(21,1))
metrics=namespace['statistics'](errors,np.arange(21))
assert metrics['position_3d_rmse_m']==3 and metrics['vertical_rmse_m']==2
assert metrics['relative_displacement_10s_rmse_m']==0 and metrics['relative_displacement_10s_pairs']==11
t=np.array([0.,.5,1.,3.])
_,valid=namespace['interpolate_native'](t,np.column_stack((t,t,t)),np.array([-.1,0,.25,1.5,3,3.1]),1.)
np.testing.assert_array_equal(valid,[False,True,True,False,True,False])
print('PASS: SPAN-point geometry, WGS84/ENU axes, known translation metrics, 10 s pairing and interpolation-gap boundaries')
