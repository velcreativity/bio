"""화면에 특정 RGB 색이 나타나면 컴퓨터를 끄는 도구.

사용법은 README.md 참고.

  python rgb_shutdown.py            감시 시작
  python rgb_shutdown.py --pick     마우스 위치/색 확인
  python rgb_shutdown.py --check    지금 화면에서 한 번만 검사
  python rgb_shutdown.py --test-switchbot   SwitchBot Bot 한 번 누르기

논리 함수(count_matches, Trigger, switchbot_headers, load_config)는
화면 없이도 테스트할 수 있도록 mss/tkinter 를 함수 안에서만 import 한다.
"""

import argparse
import base64
import hashlib
import hmac
import json
import logging
import os
import platform
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime

try:
    import numpy as np
except ImportError:  # pragma: no cover - numpy 없이도 import 는 되게 한다
    np = None

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(SCRIPT_DIR, "config.json")
LOG_PATH = os.path.join(SCRIPT_DIR, "rgb_shutdown.log")
EVIDENCE_DIR = os.path.join(SCRIPT_DIR, "evidence")

SWITCHBOT_API = "https://api.switch-bot.com/v1.1"

VALID_ACTIONS = ("shutdown", "switchbot", "test")

DEFAULT_CONFIG = {
    "target_rgb": [255, 0, 0],
    "tolerance": 10,
    "min_pixels": 50,
    "region": None,
    "interval_sec": 0.5,
    "consecutive_hits": 3,
    "countdown_sec": 10,
    "cooldown_sec": 30,  # 취소하거나 test 로 한 번 기록한 뒤 다시 감지하기까지 쉬는 시간
    "action": "shutdown",
    "switchbot": {"token": "", "secret": "", "device_id": ""},
    "save_evidence": True,
}

log = logging.getLogger("rgb_shutdown")


class ConfigError(Exception):
    """config.json 내용이 잘못되었을 때."""


# ---------------------------------------------------------------- 설정

def load_config(path=CONFIG_PATH):
    """config.json 을 읽어 기본값과 합치고 검사한 dict 를 돌려준다."""
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            user = json.load(f)
    except FileNotFoundError:
        raise ConfigError("설정 파일이 없습니다: %s" % path)
    except json.JSONDecodeError as e:
        raise ConfigError("config.json 형식이 잘못되었습니다 (%s). 따옴표/쉼표를 확인하세요." % e)
    if not isinstance(user, dict):
        raise ConfigError("config.json 최상위는 { } 형태여야 합니다.")

    cfg = json.loads(json.dumps(DEFAULT_CONFIG))  # deep copy
    for key, value in user.items():
        if key == "switchbot" and isinstance(value, dict):
            cfg["switchbot"].update(value)
        else:
            cfg[key] = value
    validate_config(cfg)
    return cfg


def validate_config(cfg):
    rgb = cfg["target_rgb"]
    if (not isinstance(rgb, (list, tuple)) or len(rgb) != 3
            or not all(isinstance(v, int) and not isinstance(v, bool) and 0 <= v <= 255 for v in rgb)):
        raise ConfigError("target_rgb 는 0~255 정수 3개여야 합니다. 예: [255, 0, 0]")
    cfg["target_rgb"] = [int(v) for v in rgb]

    for key, minimum in (("tolerance", 0), ("min_pixels", 1), ("consecutive_hits", 1),
                         ("countdown_sec", 0), ("cooldown_sec", 0)):
        v = cfg[key]
        if isinstance(v, bool) or not isinstance(v, int) or v < minimum:
            raise ConfigError("%s 는 %d 이상의 정수여야 합니다." % (key, minimum))
    v = cfg["interval_sec"]
    if isinstance(v, bool) or not isinstance(v, (int, float)) or v <= 0:
        raise ConfigError("interval_sec 는 0보다 큰 숫자여야 합니다.")

    region = cfg["region"]
    if region is not None:
        if not isinstance(region, dict):
            raise ConfigError("region 은 null 또는 {left, top, width, height} 여야 합니다.")
        for k in ("left", "top", "width", "height"):
            if k not in region or isinstance(region[k], bool) or not isinstance(region[k], int):
                raise ConfigError("region.%s 가 없거나 정수가 아닙니다." % k)
        if region["width"] <= 0 or region["height"] <= 0:
            raise ConfigError("region.width/height 는 1 이상이어야 합니다.")

    if cfg["action"] not in VALID_ACTIONS:
        raise ConfigError('action 은 "shutdown", "switchbot", "test" 중 하나여야 합니다.')
    if not isinstance(cfg["save_evidence"], bool):
        raise ConfigError("save_evidence 는 true 또는 false 여야 합니다.")
    if cfg["action"] == "switchbot":
        require_switchbot(cfg["switchbot"])


def require_switchbot(sb):
    for k in ("token", "secret", "device_id"):
        if not isinstance(sb.get(k), str) or not sb[k].strip():
            raise ConfigError("switchbot.%s 를 config.json 에 입력하세요." % k)


# ---------------------------------------------------------------- 순수 로직

def count_matches(frame_bgra, rgb, tolerance):
    """frame_bgra(H x W x 4+, mss 의 BGRA 순서)에서 rgb 와 채널별 차이가
    tolerance 이하인 픽셀 수를 센다."""
    if np is None:
        raise RuntimeError("numpy 가 설치되어 있지 않습니다. pip install -r requirements.txt")
    r, g, b = rgb
    target_bgr = np.array([b, g, r], dtype=np.int16)
    diff = np.abs(frame_bgra[..., :3].astype(np.int16) - target_bgr)
    return int(np.count_nonzero((diff <= tolerance).all(axis=-1)))


class Trigger:
    """연속 required 번 True 가 들어오면 update() 가 True 를 돌려준다.
    False 가 한 번이라도 들어오면 카운트는 0 으로 돌아간다.
    발동하면 카운트도 0 으로 돌아간다."""

    def __init__(self, required):
        self.required = max(1, int(required))
        self.count = 0

    def update(self, found):
        if found:
            self.count += 1
        else:
            self.count = 0
        if self.count >= self.required:
            self.count = 0
            return True
        return False

    def reset(self):
        self.count = 0


def switchbot_headers(token, secret, t_ms, nonce):
    """SwitchBot API v1.1 서명 헤더."""
    string_to_sign = "{}{}{}".format(token, t_ms, nonce).encode("utf-8")
    digest = hmac.new(secret.encode("utf-8"), msg=string_to_sign, digestmod=hashlib.sha256).digest()
    return {
        "Authorization": token,
        "sign": base64.b64encode(digest).decode("utf-8"),
        "t": str(t_ms),
        "nonce": nonce,
        "Content-Type": "application/json; charset=utf8",
    }


# ---------------------------------------------------------------- 동작(액션)

def press_switchbot(sb):
    """SwitchBot Bot 을 한 번 누른다. sb = {token, secret, device_id}. 응답 dict 반환."""
    require_switchbot(sb)
    url = "%s/devices/%s/commands" % (SWITCHBOT_API, sb["device_id"].strip())
    headers = switchbot_headers(sb["token"].strip(), sb["secret"].strip(),
                                int(round(time.time() * 1000)), str(uuid.uuid4()))
    body = json.dumps({"command": "press", "parameter": "default", "commandType": "command"}).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")
        raise RuntimeError("SwitchBot HTTP 오류 %s: %s" % (e.code, detail))
    except urllib.error.URLError as e:
        raise RuntimeError("SwitchBot 서버에 연결할 수 없습니다: %s" % e.reason)
    if data.get("statusCode") != 100:
        raise RuntimeError("SwitchBot 응답 오류: %s" % json.dumps(data, ensure_ascii=False))
    return data


def shutdown():
    """Windows 에서만 실제로 종료한다. 다른 OS 에서는 아무것도 하지 않는다."""
    if platform.system() != "Windows":
        log.warning("Windows 가 아니므로 종료 명령을 실행하지 않습니다 (shutdown /s /t 0).")
        return False
    subprocess.run(["shutdown", "/s", "/t", "0"])
    return True


# ---------------------------------------------------------------- 화면/카운트다운 (mss, tkinter)

def region_to_monitor(sct, region):
    if region is None:
        return sct.monitors[1]  # 주 모니터
    return {"left": region["left"], "top": region["top"],
            "width": region["width"], "height": region["height"]}


def grab(sct, monitor):
    """(frame BGRA ndarray, mss 스크린샷 객체)"""
    shot = sct.grab(monitor)
    return np.asarray(shot), shot


def save_evidence(shot):
    import mss.tools
    os.makedirs(EVIDENCE_DIR, exist_ok=True)
    path = os.path.join(EVIDENCE_DIR, "trigger_%s.png" % datetime.now().strftime("%Y%m%d_%H%M%S"))
    mss.tools.to_png(shot.rgb, shot.size, output=path)
    return path


def countdown(seconds):
    """카운트다운을 보여주고 끝까지 가면 True, 취소하면 False."""
    if seconds <= 0:
        return True
    try:
        import tkinter as tk
        root = tk.Tk()
    except Exception:
        return countdown_console(seconds)

    result = {"ok": True}
    root.title("자동 종료")
    root.attributes("-topmost", True)
    root.resizable(False, False)
    label = tk.Label(root, font=("Malgun Gothic", 24, "bold"), padx=40, pady=20)
    label.pack()

    def cancel():
        result["ok"] = False
        root.destroy()

    tk.Button(root, text="취소", font=("Malgun Gothic", 28, "bold"), bg="#d9534f", fg="white",
              command=cancel, padx=30, pady=10).pack(padx=30, pady=(0, 30))
    root.protocol("WM_DELETE_WINDOW", cancel)

    remaining = [int(seconds)]

    def tick():
        if remaining[0] <= 0:
            root.destroy()
            return
        label.config(text="%d초 후 컴퓨터가 꺼집니다" % remaining[0])
        remaining[0] -= 1
        root.after(1000, tick)

    root.update_idletasks()
    w, h = root.winfo_reqwidth(), root.winfo_reqheight()
    root.geometry("+%d+%d" % ((root.winfo_screenwidth() - w) // 2, (root.winfo_screenheight() - h) // 3))
    root.lift()
    root.focus_force()
    tick()
    root.mainloop()
    return result["ok"]


def countdown_console(seconds):
    print("(창을 띄울 수 없어 콘솔로 표시합니다. 취소: Ctrl+C)")
    try:
        for n in range(int(seconds), 0, -1):
            print("%d초 후 컴퓨터가 꺼집니다" % n, flush=True)
            time.sleep(1)
    except KeyboardInterrupt:
        return False
    return True


# ---------------------------------------------------------------- 실행 모드

def setup_logging():
    log.setLevel(logging.INFO)
    if log.handlers:
        return
    fmt = logging.Formatter("%(asctime)s %(message)s", "%Y-%m-%d %H:%M:%S")
    fh = logging.FileHandler(LOG_PATH, encoding="utf-8")
    fh.setFormatter(fmt)
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    log.addHandler(fh)
    log.addHandler(sh)


def print_summary(cfg):
    sb = cfg["switchbot"]
    print("=" * 50)
    print(" 설정 요약")
    print("  target_rgb      :", cfg["target_rgb"])
    print("  tolerance       :", cfg["tolerance"])
    print("  min_pixels      :", cfg["min_pixels"])
    print("  region          :", cfg["region"] if cfg["region"] else "주 모니터 전체")
    print("  interval_sec    :", cfg["interval_sec"])
    print("  consecutive_hits:", cfg["consecutive_hits"])
    print("  countdown_sec   :", cfg["countdown_sec"])
    print("  action          :", cfg["action"])
    if cfg["action"] == "switchbot":
        print("  switchbot       : device_id=%s, token=%s" % (sb["device_id"], "설정됨" if sb["token"] else "없음"))
    print("  save_evidence   :", cfg["save_evidence"])
    print("=" * 50)
    print(" ※ 처음이라면 먼저 'start.bat --check' 로 확인하고,")
    print("   action 을 \"test\" 로 둔 채 시험해 보세요.")
    print(" ※ 중지: 이 창에서 Ctrl+C")
    print("=" * 50)


def run_action(cfg):
    if cfg["action"] == "switchbot":
        log.info("SwitchBot Bot 을 누릅니다.")
        resp = press_switchbot(cfg["switchbot"])
        log.info("SwitchBot 응답: %s", json.dumps(resp, ensure_ascii=False))
    else:
        log.info("컴퓨터를 종료합니다.")
        shutdown()


def watch(cfg):
    import mss
    print_summary(cfg)
    trig = Trigger(cfg["consecutive_hits"])
    log.info("감시 시작 (action=%s)", cfg["action"])
    with mss.mss() as sct:
        monitor = region_to_monitor(sct, cfg["region"])
        while True:
            frame, shot = grab(sct, monitor)
            n = count_matches(frame, cfg["target_rgb"], cfg["tolerance"])
            found = n >= cfg["min_pixels"]
            if found:
                log.info("색 감지: %d 픽셀 (연속 %d/%d)", n, trig.count + 1, cfg["consecutive_hits"])
            if trig.update(found):
                log.info("조건 충족: 연속 %d회 감지", cfg["consecutive_hits"])
                if cfg["save_evidence"]:
                    try:
                        log.info("증거 화면 저장: %s", save_evidence(shot))
                    except Exception as e:
                        log.warning("증거 화면 저장 실패: %s", e)
                if cfg["action"] == "test":
                    log.info("[test] 아무 동작도 하지 않습니다. %d초 쉬고 계속 감시합니다.", cfg["cooldown_sec"])
                    time.sleep(cfg["cooldown_sec"])
                    continue
                if countdown(cfg["countdown_sec"]):
                    run_action(cfg)
                    log.info("동작 완료. 감시를 종료합니다.")
                    return 0
                log.info("사용자가 취소했습니다. %d초 쉬고 계속 감시합니다.", cfg["cooldown_sec"])
                trig.reset()
                time.sleep(cfg["cooldown_sec"])
                continue
            time.sleep(cfg["interval_sec"])


def cursor_pos():
    import ctypes
    from ctypes import wintypes
    pt = wintypes.POINT()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
    return pt.x, pt.y


def pick():
    if platform.system() != "Windows":
        print("--pick 은 Windows 에서만 동작합니다.")
        return 1
    import ctypes
    import mss
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass
    print("마우스를 원하는 곳에 올려 보세요. (종료: Ctrl+C)")
    with mss.mss() as sct:
        try:
            while True:
                x, y = cursor_pos()
                shot = sct.grab({"left": x, "top": y, "width": 1, "height": 1})
                r, g, b = shot.rgb[0], shot.rgb[1], shot.rgb[2]
                print("위치 x=%d y=%d   RGB=[%d, %d, %d]" % (x, y, r, g, b), flush=True)
                time.sleep(0.5)
        except KeyboardInterrupt:
            print("끝.")
    return 0


def check(cfg):
    import mss
    with mss.mss() as sct:
        monitor = region_to_monitor(sct, cfg["region"])
        frame, _ = grab(sct, monitor)
    n = count_matches(frame, cfg["target_rgb"], cfg["tolerance"])
    would = n >= cfg["min_pixels"]
    print("검사 영역: %s" % (monitor,))
    print("목표 색 %s (허용 오차 %d) 와 일치하는 픽셀: %d 개 (기준 %d 개)"
          % (cfg["target_rgb"], cfg["tolerance"], n, cfg["min_pixels"]))
    print("지금 화면이면 감지됨 -> %s" % ("예 (연속 %d회 이어지면 동작)" % cfg["consecutive_hits"] if would else "아니오"))
    return 0


def test_switchbot(cfg):
    resp = press_switchbot(cfg["switchbot"])
    print("SwitchBot 응답:", json.dumps(resp, ensure_ascii=False))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="화면에서 특정 색이 보이면 컴퓨터를 끕니다.")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--pick", action="store_true", help="마우스 위치와 그 아래 색(RGB)을 계속 표시")
    g.add_argument("--check", action="store_true", help="지금 화면을 한 번 검사하고 결과 출력")
    g.add_argument("--test-switchbot", action="store_true", help="SwitchBot Bot 을 한 번 눌러 보기")
    ap.add_argument("--config", default=CONFIG_PATH, help="config.json 경로 (기본: 스크립트 옆)")
    args = ap.parse_args(argv)

    setup_logging()
    try:
        if args.pick:
            return pick()
        cfg = load_config(args.config)
        if args.check:
            return check(cfg)
        if args.test_switchbot:
            return test_switchbot(cfg)
        return watch(cfg)
    except ConfigError as e:
        print("설정 오류:", e)
        return 2
    except KeyboardInterrupt:
        log.info("사용자가 중지했습니다.")
        return 0
    except Exception as e:
        log.exception("오류: %s", e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
