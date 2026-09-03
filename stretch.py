import argparse
import ctypes
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


def run_powershell(command):
    prefix = "[Console]::OutputEncoding=[System.Text.Encoding]::UTF8; "
    return subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", prefix + command],
        capture_output=True,
        text=True,
        errors="replace",
    )


def list_monitors():
    result = run_powershell(
        "Get-PnpDevice -Class Monitor | ForEach-Object { "
        "Write-Output ($_.FriendlyName + \"`t\" + $_.InstanceId + \"`t\" + $_.Status) }"
    )
    if result.returncode != 0:
        raise RuntimeError(f"모니터 목록 조회 실패: {result.stderr.strip()}")
    monitors = []
    for line in result.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) >= 3:
            monitors.append({"name": parts[0], "id": parts[1], "status": parts[2]})
    return monitors


def monitor_status(instance_id):
    escaped = instance_id.replace("'", "''")
    result = run_powershell(
        f"(Get-PnpDevice -InstanceId '{escaped}' -ErrorAction SilentlyContinue).Status"
    )
    return result.stdout.strip()


def set_monitor_enabled(instance_id, enabled):
    escaped = instance_id.replace("'", "''")
    verb = "Enable-PnpDevice" if enabled else "Disable-PnpDevice"
    result = run_powershell(
        f"{verb} -InstanceId '{escaped}' -Confirm:$false -ErrorAction Stop"
    )
    if result.returncode != 0:
        action = "/enable-device" if enabled else "/disable-device"
        result = subprocess.run(
            ["pnputil.exe", action, instance_id], capture_output=True, timeout=20
        )
        if result.returncode != 0:
            raise RuntimeError(f"모니터 {'활성화' if enabled else '비활성화'} 실패")
    time.sleep(2)
    if enabled and monitor_status(instance_id).upper() != "OK":
        raise RuntimeError("활성화 명령 후에도 모니터 상태가 OK가 아닙니다.")


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
