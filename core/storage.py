"""数据存储层。

- 每个 QQ 号一个独立文件夹：players/<qq>/player.json
- 全局跨群数据：global/<name>.json
- 原子写入（临时文件 + os.replace）+ 进程内读写锁
- 数据根目录优先使用 AstrBot 插件数据目录；本地测试时回退到插件目录下 local_data/
"""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

PLUGIN_NAME = "liufeng_sanguo_game"
_PLUGIN_NAME: str = PLUGIN_NAME


def set_plugin_name(name: str) -> None:
    """由插件实例传入 self.name（AstrBot >= 4.9.2），用于数据目录命名。"""
    global _PLUGIN_NAME
    if name:
        _PLUGIN_NAME = name


def _try_astrbot_root() -> "Path | None":
    # 官方推荐：Path(get_astrbot_data_path())/"plugin_data"/<plugin_name>
    try:  # pragma: no cover - 仅在 astrbot 环境中可用
        from astrbot.core.utils.astrbot_path import get_astrbot_data_path

        return Path(get_astrbot_data_path()) / "plugin_data" / _PLUGIN_NAME
    except Exception:  # noqa: BLE001
        pass
    try:  # pragma: no cover
        from astrbot.core.utils.astrbot_path import get_astrbot_plugin_data_path

        return Path(get_astrbot_plugin_data_path()) / _PLUGIN_NAME
    except Exception:  # noqa: BLE001
        return None


def _default_root() -> Path:
    root = _try_astrbot_root()
    if root is not None:
        return root
    # 本地无 astrbot 时回退（仅用于开发/测试）
    return Path(__file__).resolve().parent.parent / "local_data"


_LOCK = threading.RLock()
_ROOT_OVERRIDE: Optional[Path] = None


def set_data_root(path: str | os.PathLike[str] | None) -> None:
    """测试用：覆盖数据根目录。传 None 恢复默认。"""
    global _ROOT_OVERRIDE
    _ROOT_OVERRIDE = Path(path) if path is not None else None


def data_root() -> Path:
    root = _ROOT_OVERRIDE if _ROOT_OVERRIDE is not None else _default_root()
    root.mkdir(parents=True, exist_ok=True)
    return root


def players_dir() -> Path:
    path = data_root() / "players"
    path.mkdir(parents=True, exist_ok=True)
    return path


def global_dir() -> Path:
    path = data_root() / "global"
    path.mkdir(parents=True, exist_ok=True)
    return path


def player_dir(qq: str) -> Path:
    path = players_dir() / str(qq)
    path.mkdir(parents=True, exist_ok=True)
    return path


def player_file(qq: str) -> Path:
    return player_dir(qq) / "player.json"


def _atomic_write(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return default


# ---------------------------------------------------------------------------
# 玩家数据
# ---------------------------------------------------------------------------


def load_player(qq: str) -> Optional[Dict[str, Any]]:
    with _LOCK:
        path = player_file(qq)
        if not path.exists():
            return None
        return _read_json(path, None)


def save_player(qq: str, data: Dict[str, Any]) -> None:
    with _LOCK:
        _atomic_write(player_file(qq), data)


def player_exists(qq: str) -> bool:
    return player_file(qq).exists()


def delete_player(qq: str) -> bool:
    with _LOCK:
        path = player_file(qq)
        if path.exists():
            path.unlink()
            return True
        return False


def list_players() -> List[str]:
    """返回所有已注册 QQ 号。"""
    root = players_dir()
    result: List[str] = []
    for child in root.iterdir():
        if child.is_dir() and (child / "player.json").exists():
            result.append(child.name)
    return result


def iter_players():
    """遍历 (qq, data)。用于排行榜等跨用户聚合。"""
    for qq in list_players():
        data = load_player(qq)
        if data is not None:
            yield qq, data


# ---------------------------------------------------------------------------
# 全局数据
# ---------------------------------------------------------------------------


def load_global(name: str, default: Any = None) -> Any:
    with _LOCK:
        return _read_json(global_dir() / f"{name}.json", default)


def save_global(name: str, data: Any) -> None:
    with _LOCK:
        _atomic_write(global_dir() / f"{name}.json", data)


# ---------------------------------------------------------------------------
# 玩家子文件（邮件等）
# ---------------------------------------------------------------------------


def load_player_sub(qq: str, name: str, default: Any = None) -> Any:
    with _LOCK:
        return _read_json(player_dir(qq) / f"{name}.json", default)


def save_player_sub(qq: str, name: str, data: Any) -> None:
    with _LOCK:
        _atomic_write(player_dir(qq) / f"{name}.json", data)
