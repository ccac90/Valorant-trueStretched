# Valorant True Stretch

Windows에서 VALORANT의 스트레치 해상도 전환을 도와주는 간단한 GUI 도구입니다. 선택한 모니터 장치를 일시적으로 비활성화하고, 등록된 사용자 지정 해상도를 단축키로 전환합니다.

> Riot Games 및 NVIDIA와 관련 없는 비공식 오픈 소스 프로젝트입니다. 모니터, 드라이버 및 게임 버전에 따라 작동 방식이 다를 수 있습니다.

## 다운로드

GitHub의 [Releases](https://github.com/ccac90/Valorant-trueStretched/releases)에서 최신 ZIP 또는 EXE를 내려받으세요.

1. ZIP을 내려받았다면 먼저 압축을 해제합니다.
2. `ValorantTrueStretch.exe`를 실행합니다.
3. Windows 관리자 권한 요청을 허용합니다.

별도의 Python 설치는 필요하지 않습니다.

## 지원 환경

- Windows 10/11
- NVIDIA GPU 및 NVIDIA 제어판
- 일반 16:9 모니터 권장
- 1920×1080, 2560×1440, 3840×2160 등 해상도 지원

모니터의 인치 크기는 설정값에 영향을 주지 않습니다. 울트라와이드, 노트북 내장 디스플레이, AMD 및 Intel GPU 환경은 충분히 검증되지 않았습니다.

## 최초 준비

NVIDIA 제어판의 **바탕 화면 크기 및 위치 조정**에서 다음과 같이 설정하세요.

- 스케일링 모드: `전체 화면`
- 스케일링 수행: `GPU`
- 게임 및 프로그램에 의해 설정된 스케일링 모드 재정의: 필요하면 활성화

그다음 **해상도 변경 → 사용자 정의**에서 사용할 해상도를 한 번 등록합니다. 이 프로그램은 사용자 지정 해상도를 새로 생성하지 않고, NVIDIA 드라이버에 이미 등록된 해상도로 전환합니다.

대표 프리셋:

| 기본 해상도 | 강한 스트레치 | 균형 스트레치 | 약한 스트레치 |
|---|---:|---:|---:|
| 1920×1080 | 1456×1080 | 1568×1080 | 1620×1080 |
| 2560×1440 | 1944×1440 | 2088×1440 | 2160×1440 |
| 3840×2160 | 2912×2160 | 3136×2160 | 3240×2160 |

## 사용법

1. 프로그램에서 게임용 모니터를 선택합니다.
2. 원하는 프리셋과 전환 단축키를 선택합니다.
3. **해상도 등록 확인**을 눌러 해당 해상도를 사용할 수 있는지 확인합니다.
4. **설정 저장 및 시작**을 누릅니다.
5. VALORANT를 `전체 화면 창 모드`와 `채우기`로 설정합니다.
6. 사격장 또는 경기에 완전히 진입한 뒤 지정한 단축키를 누릅니다.
7. 같은 단축키를 다시 누르면 기본 해상도로 돌아옵니다.

**완전 복구**를 누르면 기본 해상도를 복원하고 선택한 모니터 장치를 다시 활성화합니다. 프로그램 창을 정상적으로 닫아도 실행 전 해상도로 자동 복원됩니다.

## 주의 사항 및 복구

- 장치 관리자의 **모니터** 장치만 일시적으로 비활성화합니다.
- **디스플레이 어댑터 또는 GPU를 비활성화하지 마세요.**
- 모니터 상태가 바뀌면서 바탕화면 아이콘이나 열려 있던 창이 다른 화면으로 이동할 수 있습니다.
- 프로그램 실행 중 작업 관리자에서 강제 종료하거나 컴퓨터 전원을 끄지 마세요.
- 문제가 생기면 프로그램을 다시 실행해 **완전 복구**를 누르세요.
- 그래도 복구되지 않으면 장치 관리자에서 해당 모니터를 활성화하고 Windows 디스플레이 설정에서 권장 해상도를 선택하세요.

설정 및 복구 정보는 `%LOCALAPPDATA%\ValorantTrueStretch`에 저장됩니다.

## 소스에서 실행 및 빌드

```powershell
py -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe .\gui.py
```

실행 파일 빌드:

```powershell
.\build.ps1
```

## English

Valorant True Stretch is a Windows GUI utility that temporarily disables the selected monitor device and switches between the native resolution and an NVIDIA custom resolution with a configurable hotkey.

Download the latest build from [Releases](https://github.com/ccac90/Valorant-trueStretched/releases). NVIDIA users should first set scaling to **Full-screen / GPU** and register the desired custom resolution in NVIDIA Control Panel. Select the monitor and preset, save the configuration, enter a VALORANT match, and press the configured hotkey to toggle the resolution. Use **Complete Restore** if you need to restore both the native resolution and monitor device.

This is an unofficial project and is not affiliated with Riot Games or NVIDIA. Standard 16:9 displays are recommended; ultrawide, laptop, AMD, and Intel configurations are not fully tested. Use at your own risk.

## License

[MIT License](LICENSE)
