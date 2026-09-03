# Valorant True Stretch Helper

Windows에서 VALORANT용 비표준 스트레치 해상도 전환과 모니터 장치 상태 복구를 돕는 오픈 소스 도구입니다.

> Riot Games, NVIDIA와 관련 없는 비공식 프로젝트입니다. 게임 업데이트나 드라이버에 따라 작동하지 않을 수 있으며 사용 책임은 사용자에게 있습니다.

“ZIP 압축 해제 후 EXE 실행”

## 준비 사항

- Windows 10/11
- NVIDIA GPU 및 최신 드라이버
- NVIDIA 제어판에서 `전체 화면` / `GPU 스케일링` 설정
- NVIDIA 제어판에 사용자 지정 해상도를 최초 한 번 등록

프로그램은 기본 해상도의 세로값을 기준으로 4:3에 가까운 비표준 해상도를 추천합니다.

- 1920x1080 모니터: 1456x1080
- 2560x1440 모니터: 1944x1440

정확한 4:3 대신 비표준 값을 쓰는 이유는 일부 VALORANT 버전이 표준 4:3에서 게임 월드를 16:9로 유지하기 때문입니다.

## 사용법

1. `ValorantTrueStretch.exe`를 실행하고 UAC 요청을 허용합니다.
2. GUI에서 게임용 모니터, 목표 해상도와 전환 단축키를 선택합니다.
3. `Check resolution`로 등록 여부를 확인하고, 없다면 NVIDIA 제어판에 사용자 지정 해상도를 등록합니다.
4. VALORANT를 `전체 화면 창 모드`와 `채우기`로 설정합니다.
5. 설정을 저장하면 다음 실행부터 선택한 모니터를 자동으로 사용 안 함 처리합니다.
6. 사격장이나 경기 진입 후 지정한 단축키를 눌러 적용합니다.
7. 같은 단축키를 다시 누르면 기본 해상도로 돌아갑니다. 모니터 장치는 사용 안 함 상태를 유지합니다.
8. `완전 복구` 버튼을 누르면 기본 해상도와 모니터 사용 상태를 함께 복구합니다.

## 사용자 지정 해상도

이 도구는 GPU 드라이버가 이미 알고 있는 해상도로 전환합니다. NVIDIA 사용자 지정 해상도를 직접 생성하지는 않습니다. `Open NVIDIA Control Panel` 버튼으로 제어판을 열어 최초 한 번 등록하세요.

## 설정 및 긴급 복구

```powershell
ValorantTrueStretch.exe --setup
ValorantTrueStretch.exe --restore
```

설정과 복구 상태는 `%LOCALAPPDATA%\ValorantTrueStretch`에 저장됩니다. 비정상 종료 후 다음 실행 시 이전 상태를 우선 복구합니다.

## 주의 사항

- 장치 관리자의 **모니터** 장치를 일시적으로 비활성화합니다.
- **디스플레이 어댑터/GPU는 절대 비활성화하지 않습니다.**
- 모니터 연결 상태가 바뀌면서 바탕화면 아이콘과 창이 다른 화면으로 이동할 수 있습니다.
- 노트북에서는 밝기, HDR, VRR 및 주사율 선택이 일시적으로 달라질 수 있습니다.
- 프로그램을 강제 종료하지 말고 `F9`으로 종료하세요.
- 화면이나 장치 상태가 복구되지 않으면 `--restore`를 사용하거나 장치 관리자에서 모니터를 다시 활성화하세요.

## 소스에서 실행

```powershell
py -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe .\stretch.py
```

## 빌드

```powershell
.\build.ps1
```

결과물은 `dist\ValorantTrueStretch.exe`에 생성됩니다.

## 라이선스

MIT License
