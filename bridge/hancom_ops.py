"""Hancom (한글) COM operations for the local Windows agent. Requires pywin32 + 한컴오피스.

Only operations the ISO pipeline already relies on (lessons 1, 6; R-LINESEG-3; S10):
open/SaveAs roundtrip, format conversion, PDF export, page count, text extraction,
InsertFile (section/style preserving). No raw-XML authoring here, ever.
"""
import contextlib
import os

FORMATS = {".hwp": "HWP", ".hwpx": "HWPX", ".pdf": "PDF", ".txt": "TEXT"}


def _fmt(path):
    ext = os.path.splitext(path)[1].lower()
    if ext not in FORMATS:
        raise ValueError("unsupported extension: " + ext)
    return FORMATS[ext]


@contextlib.contextmanager
def hwp_session(visible=False):
    import pythoncom
    import win32com.client
    pythoncom.CoInitialize()
    hwp = win32com.client.gencache.EnsureDispatch("HWPFrame.HwpObject")
    try:
        # Suppresses the file-access approval popup; needs the FilePathCheckerModule
        # DLL registered under HKCU\Software\HNC\HwpAutomation\Modules (see README).
        hwp.RegisterModule("FilePathCheckDLL", "FilePathCheckerModule")
        hwp.XHwpWindows.Item(0).Visible = bool(visible)
        yield hwp
    finally:
        with contextlib.suppress(Exception):
            hwp.Clear(1)
        with contextlib.suppress(Exception):
            hwp.Quit()
        pythoncom.CoUninitialize()


def _open(hwp, path):
    if not os.path.isfile(path):
        raise FileNotFoundError(path)
    if not hwp.Open(path, _fmt(path), "forceopen:true"):
        raise RuntimeError("Hancom failed to open " + path)


def _save_as(hwp, path):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    if not hwp.SaveAs(path, _fmt(path), ""):
        raise RuntimeError("Hancom failed to save " + path)


def _text(hwp, limit=200000):
    hwp.InitScan()
    parts, total = [], 0
    try:
        while True:
            state, text = hwp.GetText()
            if state in (0, 1):  # 0 = end of doc, 1 = no more text
                break
            parts.append(text)
            total += len(text)
            if total >= limit:
                break
    finally:
        hwp.ReleaseScan()
    return "".join(parts)[:limit]


def page_count(src):
    with hwp_session() as hwp:
        _open(hwp, src)
        return {"pages": hwp.PageCount}


def roundtrip(src, dst=None):
    """R-LINESEG-3: open + SaveAs regenerates layout caches. dst defaults to src."""
    with hwp_session() as hwp:
        _open(hwp, src)
        _save_as(hwp, dst or src)
        return {"pages": hwp.PageCount, "saved": dst or src}


def convert(src, dst):
    with hwp_session() as hwp:
        _open(hwp, src)
        pages = hwp.PageCount
        _save_as(hwp, dst)
        return {"pages": pages, "saved": dst}


def export_pdf(src, dst):
    return convert(src, dst)


def extract_text(src, limit=200000):
    with hwp_session() as hwp:
        _open(hwp, src)
        text = _text(hwp, limit)
        return {"pages": hwp.PageCount, "chars": len(text), "text": text}


def insert_file(target, donor, dst, keep_section=True):
    """Append `donor` at the end of `target` via Hancom InsertFile; save to `dst`."""
    if not os.path.isfile(donor):
        raise FileNotFoundError(donor)
    with hwp_session() as hwp:
        _open(hwp, target)
        before = hwp.PageCount
        hwp.MovePos(3)  # moveDocEnd
        act = hwp.HParameterSet.HInsertFile
        hwp.HAction.GetDefault("InsertFile", act.HSet)
        act.filename = donor
        act.KeepSection = 1 if keep_section else 0
        act.KeepCharshape = 1
        act.KeepParashape = 1
        act.KeepStyle = 1
        if not hwp.HAction.Execute("InsertFile", act.HSet):
            raise RuntimeError("InsertFile failed for " + donor)
        _save_as(hwp, dst)
        return {"pages_before": before, "pages_after": hwp.PageCount, "saved": dst}
