"""
core/autostart.py - Windows 開機自動啟動

在 Windows Startup 資料夾建立 .lnk 捷徑，開機時啟動排程器 .exe。

優先寫入 Common Startup（系統層級，所有使用者）；
若無權限（需管理員），自動降級到 User Startup（當前使用者）。

使用 PowerShell 的 WScript.Shell COM 物件建立捷徑，
無需 pywin32 等額外 Python 套件，中文路徑也能正確處理。
舊版的 .vbs 啟動檔會在 disable/sync 時一併清除。
"""

import base64
import os
import subprocess
import sys

from scheduler import branding

_FILENAME = branding.AUTOSTART_SHORTCUT_NAME
_LEGACY_VBS = branding.AUTOSTART_LEGACY_VBS_NAME


# ------------------------------------------------------------------
# 資料夾路徑
# ------------------------------------------------------------------


def _common_startup_dir() -> str:
    """C:\\ProgramData\\Microsoft\\Windows\\Start Menu\\Programs\\StartUp"""
    program_data = os.environ.get("ProgramData", r"C:\ProgramData")
    return os.path.join(
        program_data, "Microsoft", "Windows", "Start Menu", "Programs", "StartUp"
    )


def _user_startup_dir() -> str:
    """%APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs\\Startup"""
    appdata = os.environ.get("APPDATA", "")
    return os.path.join(
        appdata, "Microsoft", "Windows", "Start Menu", "Programs", "Startup"
    )


def _lnk_candidates() -> list[str]:
    """目前可能存在的 .lnk 路徑（兩個 startup 資料夾）。"""
    return [
        os.path.join(_common_startup_dir(), _FILENAME),
        os.path.join(_user_startup_dir(), _FILENAME),
    ]


def _legacy_vbs_candidates() -> list[str]:
    """舊版 .vbs 路徑（用於清理）。"""
    return [
        os.path.join(_common_startup_dir(), _LEGACY_VBS),
        os.path.join(_user_startup_dir(), _LEGACY_VBS),
    ]


def _exe_path() -> str | None:
    """取得排程器 .exe 路徑。dev 模式回傳 None。"""
    if not getattr(sys, "frozen", False):
        return None
    return os.path.abspath(sys.executable)


# ------------------------------------------------------------------
# PowerShell 互動
# ------------------------------------------------------------------


def _run_powershell(script: str) -> tuple[bool, str]:
    """執行 PowerShell script，透過 -EncodedCommand 避開字元編碼問題。

    PowerShell 的 -EncodedCommand 接受 Base64 編碼的 UTF-16 LE，
    能正確處理中文字元與特殊符號。
    """
    encoded = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
    try:
        result = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy",
                "Bypass",
                "-EncodedCommand",
                encoded,
            ],
            capture_output=True,
            text=True,
            timeout=15,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
        if result.returncode != 0:
            return False, (result.stderr or result.stdout).strip()
        return True, result.stdout.strip()
    except (OSError, subprocess.TimeoutExpired) as e:
        return False, str(e)


def _create_shortcut(lnk_path: str, target_exe: str) -> tuple[bool, str]:
    """呼叫 PowerShell 建立 .lnk 捷徑。"""
    working_dir = os.path.dirname(target_exe)
    # PowerShell script：變數用 $env 與字串安全傳遞
    script = (
        '$lnk = @"\n'
        f"{lnk_path}\n"
        '"@\n'
        '$target = @"\n'
        f"{target_exe}\n"
        '"@\n'
        '$workDir = @"\n'
        f"{working_dir}\n"
        '"@\n'
        "$sh = New-Object -ComObject WScript.Shell\n"
        "$sc = $sh.CreateShortcut($lnk)\n"
        "$sc.TargetPath = $target\n"
        "$sc.WorkingDirectory = $workDir\n"
        '$sc.IconLocation = "$target,0"\n'
        "$sc.Save()\n"
    )
    return _run_powershell(script)


# ------------------------------------------------------------------
# Public API
# ------------------------------------------------------------------


def is_supported() -> bool:
    """是否支援自動啟動（僅 Windows 編譯後的 exe 適用）。"""
    return sys.platform == "win32" and getattr(sys, "frozen", False)


def is_enabled() -> bool:
    """檢查是否已設定自動啟動（任一候選路徑存在 .lnk 即視為已啟用）。"""
    if not is_supported():
        return False
    return any(os.path.isfile(p) for p in _lnk_candidates())


def enable() -> tuple[bool, str]:
    """建立 .lnk 捷徑。回傳 (success, message)。"""
    if not is_supported():
        return False, "目前環境不支援自動啟動（僅編譯後的 .exe 可用）"

    exe = _exe_path()
    if not exe or not os.path.isfile(exe):
        return False, "找不到排程器 .exe 路徑"

    # 清理舊版 .vbs
    _remove_legacy_vbs()

    # 先嘗試 Common Startup（系統層級）
    common_path = os.path.join(_common_startup_dir(), _FILENAME)
    try:
        os.makedirs(os.path.dirname(common_path), exist_ok=True)
        ok, err = _create_shortcut(common_path, exe)
        if ok and os.path.isfile(common_path):
            return True, f"已加入開機啟動（系統層級）\n{common_path}"
    except OSError:
        pass

    # 降級到 User Startup
    user_path = os.path.join(_user_startup_dir(), _FILENAME)
    try:
        os.makedirs(os.path.dirname(user_path), exist_ok=True)
        ok, err = _create_shortcut(user_path, exe)
        if ok and os.path.isfile(user_path):
            return True, f"已加入開機啟動（當前使用者）\n{user_path}"
        return False, f"無法建立捷徑：{err}"
    except OSError as e:
        return False, f"無法建立捷徑：{e}"


def disable() -> tuple[bool, str]:
    """刪除所有 .lnk 與舊版 .vbs 啟動檔。回傳 (success, message)。"""
    removed: list[str] = []
    errors: list[str] = []

    targets = _lnk_candidates() + _legacy_vbs_candidates()
    for path in targets:
        if os.path.isfile(path):
            try:
                os.remove(path)
                removed.append(path)
            except OSError as e:
                errors.append(f"{path}: {e}")

    if errors and not removed:
        return False, "無法移除：\n" + "\n".join(errors)
    if errors:
        return True, "部分移除成功，下列失敗：\n" + "\n".join(errors)
    if removed:
        return True, "已移除開機啟動：\n" + "\n".join(removed)
    return True, "原本就未設定開機啟動"


def sync() -> None:
    """啟動時呼叫：清除舊版 .vbs；若 .lnk 存在但指向錯誤路徑則重建。"""
    if not is_supported():
        return

    # 清理舊版 .vbs（無論目前是否啟用）
    _remove_legacy_vbs()

    exe = _exe_path()
    if not exe or not os.path.isfile(exe):
        return

    # 檢查現有 .lnk 目標是否正確，不正確則重寫
    for lnk_path in _lnk_candidates():
        if not os.path.isfile(lnk_path):
            continue
        if not _lnk_target_matches(lnk_path, exe):
            try:
                _create_shortcut(lnk_path, exe)
            except OSError:
                pass


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _remove_legacy_vbs() -> None:
    """移除舊版 .vbs 啟動檔。"""
    for path in _legacy_vbs_candidates():
        if os.path.isfile(path):
            try:
                os.remove(path)
            except OSError:
                pass


def _lnk_target_matches(lnk_path: str, expected_exe: str) -> bool:
    """讀取 .lnk 的 TargetPath，比對是否與目前 exe 一致。"""
    script = (
        '$lnk = @"\n'
        f"{lnk_path}\n"
        '"@\n'
        "$sh = New-Object -ComObject WScript.Shell\n"
        "$sc = $sh.CreateShortcut($lnk)\n"
        "[Console]::Out.Write($sc.TargetPath)\n"
    )
    ok, output = _run_powershell(script)
    if not ok:
        return False
    return os.path.normcase(output.strip()) == os.path.normcase(expected_exe)
