"""pytest 配置：把插件根目录的父目录加入 sys.path，使测试可按包导入
（插件内部使用相对导入，需以 `liufeng_sanguo_game.xxx` 形式导入）。"""

import os
import sys

_PLUGIN_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_WORKSPACE_PARENT = os.path.dirname(_PLUGIN_ROOT)
if _WORKSPACE_PARENT not in sys.path:
    sys.path.insert(0, _WORKSPACE_PARENT)
