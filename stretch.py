import argparse
import ctypes
from ctypes import wintypes
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import win32api
import win32con


APP_NAME = "ValorantTrueStretch"
CONFIG_DIR = Path(os.environ.get("LOCALAPPDATA", Path.home())) / APP_NAME
CONFIG_PATH = CONFIG_DIR / "config.json"
STATE_PATH = CONFIG_DIR / "recovery.json"
VK_F8 = 0x77
VK_F9 = 0x78


class GUID(ctypes.Structure):
    _fields_ = [("Data1", wintypes.DWORD),
                ("Data2", wintypes.WORD),
                ("Data3", wintypes.WORD),
                ("Data4", ctypes.c_ubyte * 8)]


class SP_DEVINFO_DATA(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.DWORD),
                ("ClassGuid", GUID),
                ("DevInst", wintypes.DWORD),
                ("Reserved", ctypes.c_void_p)]


GUID_DEVCLASS_MONITOR = GUID(
    0x4D36E96E, 0xE325, 0x11CE,
    (ctypes.c_ubyte * 8)(0xBF, 0xC1, 0x08, 0x00, 0x2B, 0xE1, 0x03, 0x18),
)
DIGCF_PRESENT = 0x00000002
SPDRP_DEVICEDESC = 0x00000000
SPDRP_FRIENDLYNAME = 0x0000000C
DN_STARTED = 0x00000008
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value
_setupapi = ctypes.WinDLL("setupapi", use_last_error=True)
_cfgmgr32 = ctypes.WinDLL("cfgmgr32", use_last_error=True)
_setupapi.SetupDiGetClassDevsW.restype = wintypes.HANDLE
_setupapi.SetupDiGetClassDevsW.argtypes = [ctypes.POINTER(GUID), wintypes.LPCWSTR,
                                           wintypes.HWND, wintypes.DWORD]
_setupapi.SetupDiEnumDeviceInfo.argtypes = [wintypes.HANDLE, wintypes.DWORD,
                                            ctypes.POINTER(SP_DEVINFO_DATA)]
_setupapi.SetupDiGetDeviceInstanceIdW.argtypes = [
    wintypes.HANDLE, ctypes.POINTER(SP_DEVINFO_DATA), wintypes.LPWSTR,
    wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
_setupapi.SetupDiGetDeviceRegistryPropertyW.argtypes = [
    wintypes.HANDLE, ctypes.POINTER(SP_DEVINFO_DATA), wintypes.DWORD,
    ctypes.POINTER(wintypes.DWORD), ctypes.POINTER(ctypes.c_ubyte),
    wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
_setupapi.SetupDiDestroyDeviceInfoList.argtypes = [wintypes.HANDLE]
_cfgmgr32.CM_Get_DevNode_Status.argtypes = [ctypes.POINTER(wintypes.ULONG),
                                            ctypes.POINTER(wintypes.ULONG),
                                            wintypes.DWORD, wintypes.ULONG]
_cfgmgr32.CM_Locate_DevNodeW.argtypes = [ctypes.POINTER(wintypes.DWORD),
                                         wintypes.LPWSTR, wintypes.ULONG]
_cfgmgr32.CM_Enable_DevNode.argtypes = [wintypes.DWORD, wintypes.ULONG]
_cfgmgr32.CM_Disable_DevNode.argtypes = [wintypes.DWORD, wintypes.ULONG]
CM_DISABLE_PERSIST = 0x00000008


def _device_property(device_set, device_info, prop):
    buffer = ctypes.create_unicode_buffer(512)
    reg_type = wintypes.DWORD()
    required = wintypes.DWORD()
    ok = _setupapi.SetupDiGetDeviceRegistryPropertyW(
        device_set, ctypes.byref(device_info), prop, ctypes.byref(reg_type),
        ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte)),
        ctypes.sizeof(buffer), ctypes.byref(required),
    )
    return buffer.value if ok else ""


def _device_started(devinst):
    status = wintypes.ULONG()
    problem = wintypes.ULONG()
    result = _cfgmgr32.CM_Get_DevNode_Status(
        ctypes.byref(status), ctypes.byref(problem), devinst, 0
    )
    return result == 0 and bool(status.value & DN_STARTED)


def _locate_device(instance_id):
    devinst = wintypes.DWORD()
    result = _cfgmgr32.CM_Locate_DevNodeW(
        ctypes.byref(devinst), instance_id, 0
    )
    if result != 0:
        raise RuntimeError("저장된 모니터 장치를 찾지 못했습니다.")
    return devinst.value


def is_admin():
    return bool(ctypes.windll.shell32.IsUserAnAdmin())


def relaunch_as_admin():
    if getattr(sys, "frozen", False):
        executable = sys.executable
        arguments = sys.argv[1:]
    else:
        executable = sys.executable
        arguments = [str(Path(__file__).resolve()), *sys.argv[1:]]
    params = subprocess.list2cmdline(arguments)
    result = ctypes.windll.shell32.ShellExecuteW(
        None, "runas", executable, params, str(Path.cwd()), 1
    )
    if result <= 32:
        raise RuntimeError("관리자 권한 실행이 취소되었거나 실패했습니다.")


def list_monitors(present_only=True):
    flags = DIGCF_PRESENT if present_only else 0
    device_set = _setupapi.SetupDiGetClassDevsW(
        ctypes.byref(GUID_DEVCLASS_MONITOR), None, None, flags
    )
    if device_set == INVALID_HANDLE_VALUE:
        raise RuntimeError("Windows 장치 API에서 모니터 목록 조회에 실패했습니다.")
    monitors = []
    try:
        index = 0
        while True:
            info = SP_DEVINFO_DATA()
            info.cbSize = ctypes.sizeof(SP_DEVINFO_DATA)
            if not _setupapi.SetupDiEnumDeviceInfo(
                    device_set, index, ctypes.byref(info)):
                break
            instance_buffer = ctypes.create_unicode_buffer(512)
            required = wintypes.DWORD()
            if _setupapi.SetupDiGetDeviceInstanceIdW(
                    device_set, ctypes.byref(info), instance_buffer,
                    len(instance_buffer), ctypes.byref(required)):
                name = (_device_property(device_set, info, SPDRP_FRIENDLYNAME)
                        or _device_property(device_set, info, SPDRP_DEVICEDESC)
                        or "Generic Monitor")
                monitors.append({"name": name, "id": instance_buffer.value,
                                 "status": "OK" if _device_started(info.DevInst) else "Error"})
            index += 1
    finally:
        _setupapi.SetupDiDestroyDeviceInfoList(device_set)
    return monitors


def reset_monitor_devices():
    """등록된 모니터 장치 노드를 제거하고 연결된 장치를 다시 검색한다."""
    monitors = list_monitors(present_only=False)
    removed = 0
    for monitor in monitors:
        try:
            result = subprocess.run(
                ["pnputil.exe", "/remove-device", monitor["id"], "/force"],
                capture_output=True, timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            if result.returncode == 0:
                removed += 1
        except subprocess.TimeoutExpired:
            continue
    try:
        subprocess.run(["pnputil.exe", "/scan-devices"], capture_output=True,
                       timeout=20, creationflags=subprocess.CREATE_NO_WINDOW)
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("모니터 장치 재검색 시간이 초과되었습니다.") from exc
    subprocess.Popen(["DisplaySwitch.exe", "/extend"],
                     creationflags=subprocess.CREATE_NO_WINDOW)
    time.sleep(3)
    return removed


def monitor_status(instance_id):
    return "OK" if _device_started(_locate_device(instance_id)) else "Error"


def set_monitor_enabled(instance_id, enabled):
    def state_matches():
        try:
            is_enabled = monitor_status(instance_id).upper() == "OK"
        except RuntimeError:
            is_enabled = False
        return is_enabled == enabled

    # 이미 원하는 상태라면 pnputil을 다시 호출하지 않는다.
    if state_matches():
        return

    devinst = _locate_device(instance_id)
    if enabled:
        api_result = _cfgmgr32.CM_Enable_DevNode(devinst, 0)
    else:
        api_result = _cfgmgr32.CM_Disable_DevNode(devinst, CM_DISABLE_PERSIST)

    result = None
    if api_result != 0:
        action = "/enable-device" if enabled else "/disable-device"
        try:
            result = subprocess.run(
                ["pnputil.exe", action, instance_id], capture_output=True,
                timeout=8, creationflags=subprocess.CREATE_NO_WINDOW
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError("모니터 장치 변경 응답 시간이 초과되었습니다.") from exc

    # pnputil 종료 직후에는 장치 관리자 상태 반영이 늦을 수 있다.
    # 반환 코드보다 실제 상태를 우선하며 최대 8초 동안 재확인한다.
    deadline = time.monotonic() + 8
    while time.monotonic() < deadline:
        if state_matches():
            return
        time.sleep(0.5)

    if result is not None and result.returncode != 0:
        raise RuntimeError(f"모니터 {'활성화' if enabled else '비활성화'} 명령 실패")
    raise RuntimeError(
        f"모니터 {'활성화' if enabled else '비활성화'} 상태 확인 시간이 초과되었습니다."
    )


def get_mode():
    mode = win32api.EnumDisplaySettings(None, win32con.ENUM_CURRENT_SETTINGS)
    return mode.PelsWidth, mode.PelsHeight, mode.DisplayFrequency


def get_registry_mode():
    """Windows에 저장된 기본 디스플레이 모드를 읽는다."""
    mode = win32api.EnumDisplaySettings(None, win32con.ENUM_REGISTRY_SETTINGS)
    return mode.PelsWidth, mode.PelsHeight, mode.DisplayFrequency


def mode_exists(width, height):
    index = 0
    while True:
        try:
            mode = win32api.EnumDisplaySettings(None, index)
        except win32api.error:
            return False
        if mode.PelsWidth == width and mode.PelsHeight == height:
            return True
        index += 1


def widest_mode_for_height(height):
    """같은 세로 해상도에서 가장 넓은 등록 모드를 기본 해상도 후보로 삼는다."""
    index = 0
    candidates = []
    while True:
        try:
            mode = win32api.EnumDisplaySettings(None, index)
        except win32api.error:
            break
        if mode.PelsHeight == height:
            candidates.append((mode.PelsWidth, mode.PelsHeight, mode.DisplayFrequency))
        index += 1
    if not candidates:
        raise RuntimeError(f"세로 {height}px의 기본 해상도 후보를 찾지 못했습니다.")
    return max(candidates, key=lambda item: (item[0], item[2]))


def set_resolution(width, height, frequency=None):
    mode = win32api.EnumDisplaySettings(None, win32con.ENUM_CURRENT_SETTINGS)
    mode.PelsWidth = width
    mode.PelsHeight = height
    mode.Fields = win32con.DM_PELSWIDTH | win32con.DM_PELSHEIGHT
    if frequency:
        mode.DisplayFrequency = frequency
        mode.Fields |= win32con.DM_DISPLAYFREQUENCY
    result = win32api.ChangeDisplaySettings(mode, 0)
    if result != win32con.DISP_CHANGE_SUCCESSFUL and frequency:
        mode.Fields = win32con.DM_PELSWIDTH | win32con.DM_PELSHEIGHT
        result = win32api.ChangeDisplaySettings(mode, 0)
    if result != win32con.DISP_CHANGE_SUCCESSFUL:
        raise RuntimeError(f"해상도 {width}x{height} 적용 실패(코드 {result})")


def save_json(path, data):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(path)


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def setup():
    monitors = list_monitors()
    if not monitors:
        raise RuntimeError("장치 관리자에서 모니터를 찾지 못했습니다.")
    print("\n비활성화할 게임 모니터를 선택하세요.")
    for index, monitor in enumerate(monitors, 1):
        print(f"[{index}] {monitor['name']} ({monitor['status']})")
        print(f"    {monitor['id']}")
    while True:
        try:
            selected = int(input("번호: ")) - 1
            monitor = monitors[selected]
            break
        except (ValueError, IndexError):
            print("올바른 번호를 입력하세요.")

    native_width, native_height, native_hz = get_mode()
    recommended_width = round((native_height * 1.348) / 8) * 8
    print(f"\n현재 기본 해상도: {native_width}x{native_height} {native_hz}Hz")
    print(f"권장 비표준 해상도: {recommended_width}x{native_height}")
    raw_width = input(f"목표 가로 해상도 [{recommended_width}]: ").strip()
    raw_height = input(f"목표 세로 해상도 [{native_height}]: ").strip()
    target_width = int(raw_width) if raw_width else recommended_width
    target_height = int(raw_height) if raw_height else native_height

    config = {
        "monitor_name": monitor["name"],
        "monitor_instance_id": monitor["id"],
        "target_width": target_width,
        "target_height": target_height,
    }
    save_json(CONFIG_PATH, config)
    print(f"\n설정 저장: {CONFIG_PATH}")
    if not mode_exists(target_width, target_height):
        print("\nNVIDIA 제어판에서 아래 사용자 지정 해상도를 먼저 생성하세요.")
        print(f"가로 {target_width} / 세로 {target_height} / 주사율 {native_hz}Hz / 타이밍 자동")
        print("스케일링 모드: 전체 화면 / 스케일링 수행: GPU")
    return config


def restore_from_state(quiet=False):
    if not STATE_PATH.exists():
        if not quiet:
            print("복구할 이전 실행 상태가 없습니다.")
        return True
    state = load_json(STATE_PATH)
    errors = []
    # 모니터를 먼저 되살린 뒤 해상도를 적용해야 장치 재인식 과정에서
    # NVIDIA가 스트레치 해상도를 다시 덮어쓰지 않는다.
    if state.get("monitor_was_enabled"):
        try:
            set_monitor_enabled(state["monitor_instance_id"], True)
        except Exception as exc:
            errors.append(str(exc))
    try:
        time.sleep(1)
        set_resolution(state["native_width"], state["native_height"], state.get("native_hz"))
        time.sleep(1)
        current = get_mode()
        if current[:2] != (state["native_width"], state["native_height"]):
            set_resolution(state["native_width"], state["native_height"], None)
    except Exception as exc:
        errors.append(str(exc))
    if not errors:
        STATE_PATH.unlink(missing_ok=True)
        if not quiet:
            print("해상도와 모니터 상태를 복구했습니다.")
        return True
    print("복구 중 오류: " + " / ".join(errors))
    return False


def key_pressed(vk):
    return bool(win32api.GetAsyncKeyState(vk) & 1)


def run(config):
    if STATE_PATH.exists():
        print("이전 비정상 종료 상태를 발견해 먼저 복구합니다.")
        if not restore_from_state():
            raise RuntimeError("이전 상태를 복구하지 못했습니다. --restore를 실행하세요.")

    monitor_id = config["monitor_instance_id"]
    target_width = int(config["target_width"])
    target_height = int(config["target_height"])
    native_width, native_height, native_hz = get_mode()

    if not any(m["id"] == monitor_id for m in list_monitors()):
        raise RuntimeError("저장된 모니터를 찾지 못했습니다. --setup으로 다시 선택하세요.")
    if not mode_exists(target_width, target_height):
        raise RuntimeError(
            f"{target_width}x{target_height}가 등록되지 않았습니다. "
            "NVIDIA 제어판에서 사용자 지정 해상도를 생성하세요."
        )

    was_enabled = monitor_status(monitor_id).upper() == "OK"
    state = {
        "monitor_instance_id": monitor_id,
        "monitor_was_enabled": was_enabled,
        "native_width": native_width,
        "native_height": native_height,
        "native_hz": native_hz,
    }
    save_json(STATE_PATH, state)

    print(f"모니터: {config['monitor_name']}")
    print(f"기본: {native_width}x{native_height} / 스트레치: {target_width}x{target_height}")
    print("VALORANT를 전체 화면 창 모드 + 채우기로 설정하세요.")
    print("F8: 적용/복원    F9: 안전 복구 후 종료")
    stretched = False
    try:
        if was_enabled:
            set_monitor_enabled(monitor_id, False)
            print("모니터 장치 사용 안 함 완료")
        while True:
            if key_pressed(VK_F8):
                if stretched:
                    set_resolution(native_width, native_height, native_hz)
                    stretched = False
                    print("기본 해상도로 복원")
                else:
                    set_resolution(target_width, target_height, native_hz)
                    stretched = True
                    print("트루 스트레치 적용")
                time.sleep(0.5)
            if key_pressed(VK_F9):
                break
            time.sleep(0.03)
    finally:
        restore_from_state()


def parse_args():
    parser = argparse.ArgumentParser(description="VALORANT true-stretch helper")
    parser.add_argument("--setup", action="store_true", help="모니터/해상도 다시 설정")
    parser.add_argument("--restore", action="store_true", help="이전 실행 상태 긴급 복구")
    return parser.parse_args()


def main():
    args = parse_args()
    if args.restore:
        restore_from_state()
        input("Enter를 누르면 종료합니다.")
        return
    config = setup() if args.setup or not CONFIG_PATH.exists() else load_json(CONFIG_PATH)
    run(config)


if __name__ == "__main__":
    try:
        if not is_admin():
            relaunch_as_admin()
            raise SystemExit
        ctypes.windll.user32.SetProcessDPIAware()
        main()
    except SystemExit:
        raise
    except Exception as exc:
        print(f"\n프로그램 오류: {exc}")
        print("필요하면 이 프로그램을 --restore 옵션으로 실행하세요.")
        input("Enter를 누르면 종료합니다.")
