import base64
import hashlib
import hmac
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np

import rgb_shutdown as rs


def frame(h, w, bgra):
    f = np.zeros((h, w, 4), dtype=np.uint8)
    f[:, :] = bgra
    return f


class CountMatchesTest(unittest.TestCase):
    def test_exact_match(self):
        f = frame(4, 5, [30, 20, 10, 255])  # RGB (10,20,30)
        self.assertEqual(rs.count_matches(f, (10, 20, 30), 0), 20)

    def test_within_tolerance(self):
        f = frame(2, 2, [33, 18, 14, 255])  # RGB (14,18,33)
        self.assertEqual(rs.count_matches(f, (10, 20, 30), 4), 4)

    def test_outside_tolerance(self):
        f = frame(2, 2, [36, 20, 10, 255])  # B 차이 6
        self.assertEqual(rs.count_matches(f, (10, 20, 30), 5), 0)

    def test_tolerance_is_per_channel_max(self):
        f = frame(1, 1, [30, 20, 15, 255])  # R 차이 5, 나머지 0
        self.assertEqual(rs.count_matches(f, (10, 20, 30), 5), 1)
        self.assertEqual(rs.count_matches(f, (10, 20, 30), 4), 0)

    def test_bgr_order_red(self):
        red_bgra = frame(3, 3, [0, 0, 255, 255])
        blue_bgra = frame(3, 3, [255, 0, 0, 255])
        self.assertEqual(rs.count_matches(red_bgra, (255, 0, 0), 0), 9)
        self.assertEqual(rs.count_matches(blue_bgra, (255, 0, 0), 0), 0)

    def test_alpha_ignored_and_partial(self):
        f = frame(2, 3, [0, 0, 0, 255])
        f[0, 0] = [0, 0, 255, 0]
        f[1, 2] = [1, 2, 250, 255]
        self.assertEqual(rs.count_matches(f, (255, 0, 0), 5), 2)

    def test_no_uint8_wraparound(self):
        f = frame(1, 1, [250, 250, 250, 255])
        self.assertEqual(rs.count_matches(f, (0, 0, 0), 10), 0)
        f = frame(1, 1, [0, 0, 0, 255])
        self.assertEqual(rs.count_matches(f, (255, 255, 255), 10), 0)


class TriggerTest(unittest.TestCase):
    def test_fires_after_n_consecutive(self):
        t = rs.Trigger(3)
        self.assertEqual([t.update(True) for _ in range(3)], [False, False, True])

    def test_miss_resets(self):
        t = rs.Trigger(3)
        self.assertFalse(t.update(True))
        self.assertFalse(t.update(True))
        self.assertFalse(t.update(False))
        self.assertFalse(t.update(True))
        self.assertFalse(t.update(True))
        self.assertTrue(t.update(True))

    def test_requires_again_after_fire(self):
        t = rs.Trigger(2)
        t.update(True)
        self.assertTrue(t.update(True))
        self.assertFalse(t.update(True))
        self.assertTrue(t.update(True))

    def test_reset(self):
        t = rs.Trigger(2)
        t.update(True)
        t.reset()
        self.assertFalse(t.update(True))

    def test_one(self):
        self.assertTrue(rs.Trigger(1).update(True))
        self.assertFalse(rs.Trigger(1).update(False))


class SwitchbotHeadersTest(unittest.TestCase):
    def test_known_vector(self):
        token, secret, t, nonce = "tok123", "sec456", 1700000000000, "abc-nonce"
        expected = base64.b64encode(
            hmac.new(b"sec456", msg=("tok123" + "1700000000000" + "abc-nonce").encode(),
                     digestmod=hashlib.sha256).digest()).decode()
        h = rs.switchbot_headers(token, secret, t, nonce)
        self.assertEqual(h["sign"], expected)
        self.assertEqual(h["Authorization"], token)
        self.assertEqual(h["t"], "1700000000000")
        self.assertEqual(h["nonce"], nonce)
        self.assertEqual(h["Content-Type"], "application/json; charset=utf8")


class PressSwitchbotTest(unittest.TestCase):
    SB = {"token": "t", "secret": "s", "device_id": "DEV1"}

    def _resp(self, payload):
        m = mock.MagicMock()
        m.__enter__.return_value.read.return_value = json.dumps(payload).encode()
        return m

    def test_success_and_request(self):
        with mock.patch("urllib.request.urlopen", return_value=self._resp({"statusCode": 100})) as uo:
            self.assertEqual(rs.press_switchbot(self.SB)["statusCode"], 100)
        req = uo.call_args[0][0]
        self.assertTrue(req.full_url.endswith("/v1.1/devices/DEV1/commands"))
        self.assertEqual(req.get_method(), "POST")
        self.assertEqual(json.loads(req.data),
                         {"command": "press", "parameter": "default", "commandType": "command"})

    def test_bad_status_raises(self):
        with mock.patch("urllib.request.urlopen", return_value=self._resp({"statusCode": 190})):
            with self.assertRaises(RuntimeError):
                rs.press_switchbot(self.SB)

    def test_missing_credentials(self):
        with self.assertRaises(rs.ConfigError):
            rs.press_switchbot({"token": "", "secret": "s", "device_id": "d"})


class ConfigTest(unittest.TestCase):
    def _load(self, obj):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "config.json")
            with open(p, "w", encoding="utf-8") as f:
                json.dump(obj, f)
            return rs.load_config(p)

    def test_defaults(self):
        cfg = self._load({})
        self.assertEqual(cfg["tolerance"], 10)
        self.assertEqual(cfg["min_pixels"], 50)
        self.assertIsNone(cfg["region"])
        self.assertEqual(cfg["interval_sec"], 0.5)
        self.assertEqual(cfg["consecutive_hits"], 3)
        self.assertEqual(cfg["countdown_sec"], 10)
        self.assertEqual(cfg["action"], "shutdown")
        self.assertTrue(cfg["save_evidence"])
        self.assertEqual(set(cfg["switchbot"]), {"token", "secret", "device_id"})

    def test_override_and_partial_switchbot(self):
        cfg = self._load({"target_rgb": [1, 2, 3], "tolerance": 0, "region":
                          {"left": 0, "top": 1, "width": 2, "height": 3},
                          "switchbot": {"token": "x"}})
        self.assertEqual(cfg["target_rgb"], [1, 2, 3])
        self.assertEqual(cfg["tolerance"], 0)
        self.assertEqual(cfg["switchbot"], {"token": "x", "secret": "", "device_id": ""})

    def test_example_file_is_valid(self):
        cfg = rs.load_config(os.path.join(rs.SCRIPT_DIR, "config.example.json"))
        self.assertEqual(cfg["action"], "test")

    def test_invalid_values(self):
        for bad in ({"target_rgb": [256, 0, 0]}, {"target_rgb": [1, 2]}, {"action": "boom"},
                    {"region": {"left": 0}}, {"min_pixels": 0}, {"interval_sec": 0},
                    {"action": "switchbot"}):
            with self.assertRaises(rs.ConfigError, msg=str(bad)):
                self._load(bad)

    def test_missing_file(self):
        with self.assertRaises(rs.ConfigError):
            rs.load_config("/nonexistent/config.json")


class ShutdownGuardTest(unittest.TestCase):
    @unittest.skipIf(sys.platform == "win32", "non-Windows only")
    def test_does_not_run_on_non_windows(self):
        with mock.patch("subprocess.run") as run:
            self.assertFalse(rs.shutdown())
            run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
