import ctypes
import os
import subprocess
import shutil
import threading
import time

import webview

import stretch

APP_VERSION = "1.2.17"


HTML = r"""
<!doctype html><html lang="ko"><head><meta charset="utf-8"><style>
*{box-sizing:border-box}body{margin:0;padding:28px;background:#fff;color:#171717;font-family:"Malgun Gothic","Segoe UI",sans-serif}
h1{margin:0;font-size:28px}.sub{margin:5px 0 24px;color:#666}.card{border:1px solid #ddd;border-radius:10px;padding:18px;margin-bottom:14px;background:#fff}
label{display:block;font-size:13px;color:#555;margin:10px 0 6px}select,input{width:100%;border:1px solid #bbb;border-radius:6px;padding:10px;background:#fff;color:#111;font-size:14px}
.row{display:grid;grid-template-columns:1fr 1fr;gap:12px}.buttons{display:flex;gap:8px;flex-wrap:wrap;margin-top:16px}button{padding:10px 15px;border:1px solid #aaa;border-radius:6px;background:#fff;color:#111;font-weight:600;cursor:pointer}button:hover{background:#f2f2f2}button.primary{background:#111;color:#fff;border-color:#111}button.restore{border-color:#c33;color:#a00}button:disabled{opacity:.45;cursor:wait}
.presets{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-top:8px}.preset{padding:10px 6px;font-size:12px}.preset b{display:block;font-size:14px;margin-bottom:3px}
.native{display:inline-block;margin-top:12px;padding:6px 10px;border-radius:20px;background:#f1f1f1;font-size:12px;color:#444}.hint{font-size:12px;line-height:1.6;color:#855700}
.version{float:right;color:#777;font-size:12px;font-weight:400}
#status{height:90px;overflow:auto;white-space:pre-wrap;border:1px solid #ddd;background:#fafafa;border-radius:6px;padding:10px;font:12px Consolas,"Malgun Gothic",monospace;color:#165c2d}
#hotkey{font-weight:700;text-align:center;cursor:pointer}.notice{font-size:11px;color:#777;margin-top:10px}
#startupNotice{display:none;align-items:center;gap:9px;margin:-8px 0 16px;padding:10px 13px;border:1px solid #b8cce8;border-radius:7px;background:#eef5ff;color:#18549a;font-size:13px;font-weight:600}
body.starting #startupNotice{display:flex}.spinner{width:17px;height:17px;border:2px solid #b8cce8;border-top-color:#1670e8;border-radius:50%;animation:spin .8s linear infinite;flex:none}@keyframes spin{to{transform:rotate(360deg)}}
select:disabled,input:disabled,button:disabled{background:#f1f1f1;color:#999;border-color:#d5d5d5;cursor:wait}
</style></head><body>
<h1>발로란트 트루 스트레치 <span class="version" id="version"></span></h1><div class="sub">모니터 설정과 스트레치 해상도를 간편하게 전환합니다.</div>
<div id="startupNotice"><div class="spinner"></div><span id="startupText">모니터 설정 적용 중... 완료될 때까지 잠시 기다려 주세요.</span></div>
<div class="card"><b>기본 설정</b>
<label>게임용 모니터</label><select id="monitor"></select><div class="native" id="native">불러오는 중...</div>
<div class="row"><div><label>목표 가로</label><input id="width" type="number"></div><div><label>목표 세로</label><input id="height" type="number"></div></div>
<label>추천 화면비</label><div class="presets" id="presets"></div>
<label>전환 단축키 — 아래 칸을 누른 후 원하는 키를 누르세요</label><input id="hotkey" readonly value="F8" onclick="captureKey()">
<div class="buttons"><button onclick="recommend()">추천값</button><button class="primary" onclick="saveStart()">설정 저장 및 시작</button><button onclick="checkRes()">해상도 등록 확인</button><button onclick="nvidia()">NVIDIA 제어판</button></div>
<div class="notice">사용자 지정 해상도는 NVIDIA 제어판에 최초 한 번 등록해야 합니다.</div></div>
<div class="card"><b>실행</b><p class="hint">발로란트는 전체 화면 창 모드 + 채우기로 설정하세요. 실제 게임에 완전히 진입한 뒤 전환하세요.</p>
<div class="buttons"><button class="primary" id="toggle" onclick="toggle()">스트레치 전환</button><button class="restore" onclick="restoreAll()">완전 복구</button><button class="restore" onclick="resetMonitors()">모니터 설정 초기화</button></div></div>
<div class="card"><b>상태</b><div id="status">시작 중...</div></div>
<script>
let app=null,busy=false,capturing=false,hotkeyVk=119,hotkeyName='F8';
function log(s){const e=document.getElementById('status');e.textContent+=`\n${s}`;e.scrollTop=e.scrollHeight}
function setBusy(v){busy=v;document.querySelectorAll('button,select,input').forEach(x=>x.disabled=v)}
function values(){return{monitor_index:document.getElementById('monitor').selectedIndex,width:+document.getElementById('width').value,height:+document.getElementById('height').value,hotkey_vk:hotkeyVk,hotkey_name:hotkeyName}}
function captureKey(){capturing=true;document.getElementById('hotkey').value='키를 누르세요...'}
document.addEventListener('keydown',e=>{if(!capturing)return;e.preventDefault();if(['Shift','Control','Alt','Meta'].includes(e.key))return;hotkeyVk=e.keyCode;hotkeyName=e.key.length===1?e.key.toUpperCase():e.key.toUpperCase();document.getElementById('hotkey').value=hotkeyName;capturing=false});
function choosePreset(w,h,name){document.getElementById('width').value=w;document.getElementById('height').value=h;log(`${name}: ${w}×${h} 선택`)}
function painted(){return new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))}
async function autoStart(){if(!app.has_config)return;document.getElementById('startupText').textContent='모니터 설정 적용 중... 완료될 때까지 잠시 기다려 주세요.';document.body.classList.add('starting');setBusy(true);log('저장된 설정을 자동 적용하는 중...');await painted();try{const r=await pywebview.api.start_saved_session();log(r.message)}catch(e){log(`자동 적용 실패: ${e}`)}finally{document.body.classList.remove('starting');setBusy(false)}}
async function init(){app=await pywebview.api.get_state();document.getElementById('version').textContent=`v${app.version}`;const m=document.getElementById('monitor');m.innerHTML='';app.monitors.forEach((x,i)=>{const o=document.createElement('option');o.textContent=`${x.name} [${x.status}]`;m.appendChild(o)});m.selectedIndex=app.selected_index;document.getElementById('native').textContent=`기본: ${app.native_width} × ${app.native_height} @ ${app.native_hz}Hz`;document.getElementById('width').value=app.target_width;document.getElementById('height').value=app.target_height;const p=document.getElementById('presets');app.presets.forEach(x=>{const b=document.createElement('button');b.className='preset';b.innerHTML=`<b>${x.width}×${x.height}</b>${x.name}`;b.onclick=()=>choosePreset(x.width,x.height,x.name);p.appendChild(b)});hotkeyVk=app.hotkey_vk;hotkeyName=app.hotkey_name;document.getElementById('hotkey').value=hotkeyName;document.getElementById('status').textContent=app.message;await painted();setTimeout(autoStart,1000)}
async function recommend(){const r=await pywebview.api.recommend();document.getElementById('width').value=r.width;document.getElementById('height').value=r.height;log(`추천값: ${r.width}×${r.height}`)}
async function call(fn){if(busy)return;setBusy(true);try{return await fn()}catch(e){log(`오류: ${e}`);alert(e)}finally{setBusy(false)}}
async function saveStart(){await call(async()=>{const r=await pywebview.api.save_and_start(values());log(r.message)})}
async function checkRes(){await call(async()=>{const r=await pywebview.api.check_resolution(values());log(r.message);alert(r.message)})}
async function nvidia(){await pywebview.api.open_nvidia()}
async function toggle(){await call(async()=>{const r=await pywebview.api.toggle();document.getElementById('toggle').textContent=r.stretched?'기본 해상도로':'스트레치 전환';log(r.message)})}
async function restoreAll(){await call(async()=>{const r=await pywebview.api.restore_all();document.getElementById('toggle').textContent='스트레치 전환';log(r.message)})}
async function resetMonitors(){if(!confirm('Windows에 등록된 모니터 장치를 제거하고 다시 검색합니다. 화면이 잠시 깜빡일 수 있습니다. 계속할까요?'))return;document.getElementById('startupText').textContent='모니터 설정 초기화 중... 화면이 잠시 깜빡일 수 있습니다.';document.body.classList.add('starting');await call(async()=>{const r=await pywebview.api.reset_monitor_settings();document.getElementById('toggle').textContent='스트레치 전환';log(r.message);alert(r.message)});document.body.classList.remove('starting')}
function externalStatus(message,stretched){document.getElementById('toggle').textContent=stretched?'기본 해상도로':'스트레치 전환';log(message)}
window.addEventListener('pywebviewready',()=>setTimeout(init,50));
</script></body></html>
"""


class Api:
    def __init__(self):
        self.window = None
        self.lock = threading.RLock()
        self.config = None
        self.monitors = []
        self.session_started = False
        self.stretched = False
        self.running = True

    @staticmethod
    def recommended(native_width, native_height):
        known = {(1920, 1080): 1456, (2560, 1440): 1944}
        width = known.get((native_width, native_height))
        if width is None:
            width = round((native_width * 0.75) / 8) * 8 + 8
        return width, native_height

    @staticmethod
    def presets(native_width, native_height):
        # Ratios are based on the common 1080p presets 1456, 1568 and 1620.
        if native_height == 1080:
            widths = (1456, 1568, 1620)
        elif native_height == 1440:
            widths = (1944, 2088, 2160)
        else:
            ratios = (1456 / 1080, 1568 / 1080, 1.5)
            widths = tuple(round((native_height * ratio) / 8) * 8 for ratio in ratios)
        names = ("강한 스트레치", "균형 스트레치", "약한 스트레치")
        return [{"name": name, "width": width, "height": native_height}
                for name, width in zip(names, widths)]

    def get_state(self):
        message = "모니터와 해상도를 선택한 뒤 '설정 저장 및 시작'을 누르세요."
        if stretch.STATE_PATH.exists():
            message = "이전 실행 상태를 감지했습니다. 자동 복구 후 저장 설정을 적용합니다."
        selected_index, hotkey_vk, hotkey_name = 0, 119, "F8"
        if stretch.CONFIG_PATH.exists():
            self.config = stretch.load_json(stretch.CONFIG_PATH)
            cached = self.config.get("monitor_cache") or [{
                "name": self.config.get("monitor_name", "저장된 모니터"),
                "id": self.config.get("monitor_instance_id", ""),
            }]
            monitors = [{"name": item["name"], "id": item["id"], "status": "저장됨"}
                        for item in cached if item.get("id")]
            native_width = int(self.config.get("native_width", 1920))
            native_height = int(self.config.get("native_height", 1080))
            native_hz = int(self.config.get("native_hz", 60))
            target_width, target_height = self.recommended(native_width, native_height)
            target_width = int(self.config.get("target_width", target_width))
            target_height = int(self.config.get("target_height", target_height))
            hotkey_vk = int(self.config.get("hotkey_vk", 119))
            hotkey_name = self.config.get("hotkey_name", "F8")
            for index, monitor in enumerate(monitors):
                if monitor["id"] == self.config.get("monitor_instance_id"):
                    selected_index = index
                    break
        else:
            monitors = stretch.list_monitors()
            native_width, native_height, native_hz = stretch.get_mode()
            target_width, target_height = self.recommended(native_width, native_height)
        self.monitors = monitors
        return {"version": APP_VERSION, "monitors": monitors,
                "native_width": native_width, "native_height": native_height,
                "native_hz": native_hz, "target_width": target_width, "target_height": target_height,
                "selected_index": selected_index, "hotkey_vk": hotkey_vk,
                "hotkey_name": hotkey_name, "presets": self.presets(native_width, native_height),
                "has_config": bool(self.config),
                "message": message}

    def start_saved_session(self):
        with self.lock:
            if not self.config:
                return {"message": "저장된 설정이 없습니다."}
            self._start_session(self.config)
            return {"message": "저장된 설정을 자동 적용했습니다. 단축키로 전환할 수 있습니다."}

    def recommend(self):
        width, height, _ = stretch.get_mode()
        target_width, target_height = self.recommended(width, height)
        return {"width": target_width, "height": target_height}

    def _make_config(self, data):
        monitors = self.monitors or stretch.list_monitors()
        index = int(data["monitor_index"])
        if index < 0 or index >= len(monitors):
            raise ValueError("올바른 모니터를 선택하세요.")
        width, height = int(data["width"]), int(data["height"])
        if width < 640 or height < 480:
            raise ValueError("올바른 해상도를 입력하세요.")
        monitor = monitors[index]
        native_width, native_height, native_hz = stretch.get_mode()
        if (native_width, native_height) == (width, height):
            native_width, native_height, native_hz = stretch.get_registry_mode()
        return {"monitor_name": monitor["name"], "monitor_instance_id": monitor["id"],
                "target_width": width, "target_height": height,
                "hotkey_vk": int(data["hotkey_vk"]), "hotkey_name": data["hotkey_name"],
                "native_width": native_width, "native_height": native_height,
                "native_hz": native_hz,
                "monitor_cache": [{"name": item["name"], "id": item["id"]}
                                  for item in monitors]}

    def _start_session(self, config):
        if self.session_started:
            return
        if stretch.STATE_PATH.exists():
            if not stretch.restore_from_state(quiet=True):
                raise RuntimeError("이전 상태 복구에 실패했습니다. 완전 복구를 눌러주세요.")
        width, height = int(config["target_width"]), int(config["target_height"])
        if not stretch.mode_exists(width, height):
            raise RuntimeError(f"{width}×{height} 해상도를 NVIDIA 제어판에 먼저 등록하세요.")
        current_width, current_height, current_hz = stretch.get_mode()
        # 현재 화면이 목표 스트레치 모드가 아니고 와이드 비율이면 가장 신뢰할
        # 수 있는 원본값이다. 과거 config의 잘못된 native 값은 사용하지 않는다.
        if (current_width, current_height) != (width, height) and current_width / current_height >= 1.6:
            native_width, native_height, native_hz = current_width, current_height, current_hz
        else:
            native_width, native_height, native_hz = stretch.widest_mode_for_height(height)
        config["native_width"] = native_width
        config["native_height"] = native_height
        config["native_hz"] = native_hz
        stretch.save_json(stretch.CONFIG_PATH, config)
        monitor_id = config["monitor_instance_id"]
        was_enabled = stretch.monitor_status(monitor_id).upper() == "OK"
        stretch.save_json(stretch.STATE_PATH, {"monitor_instance_id": monitor_id,
            "monitor_was_enabled": was_enabled, "native_width": native_width,
            "native_height": native_height, "native_hz": native_hz})
        try:
            if was_enabled:
                stretch.set_monitor_enabled(monitor_id, False)
            # 모니터 장치를 끄면 NVIDIA가 마지막 사용자 지정 해상도를
            # 자동 재적용할 수 있다. 세션은 반드시 저장된 기본 해상도에서 시작한다.
            stretch.set_resolution(native_width, native_height, native_hz)
            time.sleep(1)
            current_width, current_height, _ = stretch.get_mode()
            if (current_width, current_height) != (native_width, native_height):
                stretch.set_resolution(native_width, native_height, None)
        except Exception:
            stretch.restore_from_state(quiet=True)
            raise
        self.session_started = True
        self.stretched = False

    def save_and_start(self, data):
        with self.lock:
            if self.session_started:
                self.restore_all()
            self.config = self._make_config(data)
            stretch.save_json(stretch.CONFIG_PATH, self.config)
            self._start_session(self.config)
            return {"message": "설정을 저장하고 모니터를 사용 안 함 처리했습니다."}

    def check_resolution(self, data):
        width, height = int(data["width"]), int(data["height"])
        exists = stretch.mode_exists(width, height)
        message = (f"{width}×{height} 해상도를 사용할 수 있습니다." if exists else
                   f"{width}×{height}가 없습니다. NVIDIA 제어판에서 먼저 생성하세요.")
        return {"exists": exists, "message": message}

    def open_nvidia(self):
        # `control.exe /name NVIDIA.Display`는 Store판 NVIDIA 제어판에서
        # 오류 없이 종료만 되는 경우가 있어 실행 파일/앱 ID를 직접 시도한다.
        candidates = [
            shutil.which("nvcplui.exe"),
            os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"),
                         "NVIDIA Corporation", "Control Panel Client", "nvcplui.exe"),
            os.path.join(os.environ.get("WINDIR", r"C:\Windows"),
                         "System32", "nvcplui.exe"),
        ]
        for path in candidates:
            if path and os.path.isfile(path):
                subprocess.Popen([path])
                return {"message": "NVIDIA 제어판을 실행했습니다."}

        # Microsoft Store(DCH) 버전의 앱 ID
        app_id = ("shell:AppsFolder\\"
                  "NVIDIACorp.NVIDIAControlPanel_56jybvy8sckqj!"
                  "NVIDIACorp.NVIDIAControlPanel")
        result = ctypes.windll.shell32.ShellExecuteW(None, "open", app_id,
                                                     None, None, 1)
        if result <= 32:
            raise RuntimeError("NVIDIA 제어판을 찾지 못했습니다. NVIDIA App/드라이버에서 제어판을 설치해 주세요.")
        return {"message": "NVIDIA 제어판을 실행했습니다."}

    def toggle(self):
        with self.lock:
            if not self.config:
                raise RuntimeError("설정을 먼저 저장하세요.")
            if not self.session_started:
                self._start_session(self.config)
            state = stretch.load_json(stretch.STATE_PATH)
            if self.stretched:
                stretch.set_resolution(state["native_width"], state["native_height"], state.get("native_hz"))
                self.stretched = False
                message = "기본 해상도로 전환했습니다. 모니터 장치는 계속 사용 안 함 상태입니다."
            else:
                stretch.set_resolution(int(self.config["target_width"]), int(self.config["target_height"]), state.get("native_hz"))
                self.stretched = True
                message = "스트레치 해상도로 전환했습니다."
            return {"stretched": self.stretched, "message": message}

    def restore_all(self):
        with self.lock:
            if stretch.STATE_PATH.exists():
                if not stretch.restore_from_state(quiet=True):
                    raise RuntimeError("자동 복구에 실패했습니다. 장치 관리자를 확인하세요.")
                if self.config:
                    # '완전 복구'는 시작 당시 상태와 관계없이 선택 모니터를 사용함으로 만든다.
                    # 함수가 현재 상태를 먼저 확인하므로 이미 활성화됐으면 즉시 끝난다.
                    stretch.set_monitor_enabled(self.config["monitor_instance_id"], True)
            elif self.config:
                # 상태 파일이 없어도 저장된 모니터와 가장 넓은 정상 해상도로 복구한다.
                monitor_id = self.config["monitor_instance_id"]
                stretch.set_monitor_enabled(monitor_id, True)
                height = int(self.config.get("native_height", self.config["target_height"]))
                native_width, native_height, native_hz = stretch.widest_mode_for_height(height)
                stretch.set_resolution(native_width, native_height, native_hz)
                self.config["native_width"] = native_width
                self.config["native_height"] = native_height
                self.config["native_hz"] = native_hz
                stretch.save_json(stretch.CONFIG_PATH, self.config)
            self.session_started = False
            self.stretched = False
            return {"stretched": False, "message": "기본 해상도와 모니터 사용 상태를 완전히 복구했습니다."}

    def reset_monitor_settings(self):
        with self.lock:
            native = None
            if self.config:
                native = (int(self.config.get("native_width", 1920)),
                          int(self.config.get("native_height", 1080)),
                          int(self.config.get("native_hz", 60)))
            try:
                self.restore_all()
            except Exception:
                # 장치 기록 자체가 꼬인 경우 복구 실패와 무관하게 초기화를 계속한다.
                pass
            if native:
                try:
                    stretch.set_resolution(*native)
                except Exception:
                    pass
            removed = stretch.reset_monitor_devices()
            if native:
                try:
                    stretch.set_resolution(*native)
                except Exception:
                    pass
            stretch.STATE_PATH.unlink(missing_ok=True)
            stretch.CONFIG_PATH.unlink(missing_ok=True)
            self.config = None
            self.monitors = []
            self.session_started = False
            self.stretched = False
            return {"message": (f"모니터 장치 {removed}개와 프로그램 설정을 초기화했습니다. "
                                "프로그램을 종료하고 다시 실행해 설정하세요.")}

    def close(self):
        self.running = False
        self.window.destroy()

    def on_closing(self):
        self.running = False
        if stretch.STATE_PATH.exists():
            stretch.restore_from_state(quiet=True)

    def hotkey_loop(self):
        while self.running:
            try:
                vk = int((self.config or {}).get("hotkey_vk", 119))
                if stretch.key_pressed(vk):
                    result = self.toggle()
                    if self.window:
                        message = result["message"].replace("\\", "\\\\").replace("'", "\\'").replace("\n", " ")
                        self.window.evaluate_js(f"externalStatus('{message}', {str(result['stretched']).lower()})")
                    time.sleep(0.45)
            except Exception as exc:
                if self.window:
                    message = str(exc).replace("\\", "\\\\").replace("'", "\\'").replace("\n", " ")
                    self.window.evaluate_js(f"externalStatus('오류: {message}', false)")
                time.sleep(0.5)
            time.sleep(0.04)


def main():
    if not stretch.is_admin():
        stretch.relaunch_as_admin()
        return
    ctypes.windll.user32.SetProcessDPIAware()
    # 임시 WebView2 프로필을 매번 새로 만들지 않도록 영구 프로필을 재사용한다.
    webview_data = stretch.CONFIG_DIR / "webview"
    webview_data.mkdir(parents=True, exist_ok=True)
    api = Api()
    window = webview.create_window("Valorant True Stretch", html=HTML, js_api=api,
                                   width=680, height=760, min_size=(620, 650),
                                   background_color="#ffffff")
    api.window = window
    window.events.closing += api.on_closing
    threading.Thread(target=api.hotkey_loop, daemon=True).start()
    webview.start(gui="edgechromium", debug=False, private_mode=False,
                  storage_path=str(webview_data))


if __name__ == "__main__":
    main()
