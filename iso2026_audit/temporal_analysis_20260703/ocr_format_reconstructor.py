#!/usr/bin/env python3
"""
ocr_format_reconstructor.py — geometry-first OCR reconstruction of scanned form
pages into editable HWPX, for pages with NO editable donor file.

Method (closed measurement loop):
  1. rasterize + deskew scan page (300 DPI)
  2. detect table grid from pixel rules (OpenCV morphology) -> cells + merges
  3. convert px -> HWPU exactly (1 px @300dpi = 24 HWPU)
  4. OCR per detected cell (text lands in right cell by construction)
  5. build table via Hancom COM (valid style closure by construction; never raw XML)
  6. render built HWPX (hancom_render_hook) -> overlay-diff vs source scan
  7. iterate until grid lines converge within tolerance
  8. graphs/stamps/signatures -> cropped IMAGE_REGION inserts, inventoried

Deps: opencv-python, numpy, pytesseract (+ tesseract-ocr w/ kor), pypdfium2, pillow
Windows-only for stage 5/6 (pywin32 + Hancom). Stages 1-4 run anywhere.

Safety: works only on copies in an output workspace; never fabricates text —
low-confidence OCR becomes [UNCERTAIN_OCR] cells for human fill; graphics are
never redrawn as fake content, only inserted as measured image crops.
"""
from __future__ import annotations
import json, sys
from dataclasses import dataclass, asdict, field
from pathlib import Path

import numpy as np

DPI = 300
PX_TO_HWPU = 7200 // DPI            # 24 at 300 DPI (HWPUNIT = 1/7200 inch)
A4_W_HWPU, A4_H_HWPU = 59528, 84188
GRID_TOLERANCE_PX = 2               # convergence tolerance for the verify loop
OCR_CONF_FLOOR = 60                 # below this -> [UNCERTAIN_OCR]

# --------------------------------------------------------------------------
@dataclass
class Cell:
    row: int; col: int
    x_px: int; y_px: int; w_px: int; h_px: int
    row_span: int = 1; col_span: int = 1
    text: str = ""; ocr_conf: float = 0.0
    uncertain: bool = False
    align_guess: str = "left"; approx_pt: float = 10.0; bold_guess: bool = False

@dataclass
class PageModel:
    source_image: str
    n_rows: int = 0; n_cols: int = 0
    col_widths_hwpu: list = field(default_factory=list)
    row_heights_hwpu: list = field(default_factory=list)
    margin_hwpu: dict = field(default_factory=dict)
    landscape: bool = False
    cells: list = field(default_factory=list)
    image_regions: list = field(default_factory=list)   # graphs/stamps -> crops

# --------------------------------------------------------------------------
# Stage 1+2: grid extraction from scan
# --------------------------------------------------------------------------
def extract_grid(image_path: str) -> PageModel:
    import cv2
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    img = _deskew(cv2, img)
    bw = cv2.adaptiveThreshold(~img, 255, cv2.ADAPTIVE_THRESH_MEAN_C,
                               cv2.THRESH_BINARY, 15, -2)
    h_size = max(10, img.shape[1] // 40)      # horizontal rule detector
    v_size = max(10, img.shape[0] // 40)      # vertical rule detector
    horiz = cv2.morphologyEx(bw, cv2.MORPH_OPEN,
        cv2.getStructuringElement(cv2.MORPH_RECT, (h_size, 1)), iterations=2)
    vert = cv2.morphologyEx(bw, cv2.MORPH_OPEN,
        cv2.getStructuringElement(cv2.MORPH_RECT, (1, v_size)), iterations=2)

    ys = _cluster(sorted(_line_positions(horiz, axis=0)))   # row boundaries
    xs = _cluster(sorted(_line_positions(vert, axis=1)))    # col boundaries
    model = PageModel(source_image=image_path,
                      n_rows=len(ys) - 1, n_cols=len(xs) - 1,
                      landscape=img.shape[1] > img.shape[0])
    # margins: table bbox vs page edges, in HWPU
    model.margin_hwpu = {
        "left": xs[0] * PX_TO_HWPU, "top": ys[0] * PX_TO_HWPU,
        "right": (img.shape[1] - xs[-1]) * PX_TO_HWPU,
        "bottom": (img.shape[0] - ys[-1]) * PX_TO_HWPU,
    }
    model.col_widths_hwpu = [(xs[i+1] - xs[i]) * PX_TO_HWPU for i in range(model.n_cols)]
    model.row_heights_hwpu = [(ys[i+1] - ys[i]) * PX_TO_HWPU for i in range(model.n_rows)]

    grid_mask = cv2.add(horiz, vert)
    for r in range(model.n_rows):
        c = 0
        while c < model.n_cols:
            span = _col_span(grid_mask, xs, ys, r, c)       # merged-cell detection:
            rspan = _row_span(grid_mask, xs, ys, r, c)      # absent divider = span
            model.cells.append(Cell(
                row=r, col=c, x_px=xs[c], y_px=ys[r],
                w_px=xs[c+span] - xs[c], h_px=ys[r+rspan] - ys[r],
                row_span=rspan, col_span=span))
            c += span
    return model

def _line_positions(mask, axis):
    proj = mask.sum(axis=1 - axis)
    thresh = proj.max() * 0.4 if proj.max() else 0
    pos, run = [], []
    for i, v in enumerate(proj):
        if v > thresh: run.append(i)
        elif run: pos.append(sum(run)//len(run)); run = []
    if run: pos.append(sum(run)//len(run))
    return pos

def _cluster(vals, gap=6):
    out = []
    for v in vals:
        if out and v - out[-1] <= gap: out[-1] = (out[-1] + v)//2
        else: out.append(v)
    return out

def _col_span(mask, xs, ys, r, c):
    span = 1
    while c + span < len(xs) - 1:
        x = xs[c + span]
        seg = mask[ys[r]+3:ys[r+1]-3, max(0,x-1):x+2]
        if seg.size and seg.mean() > 20: break     # divider exists -> stop
        span += 1
    return span

def _row_span(mask, xs, ys, r, c):
    span = 1
    while r + span < len(ys) - 1:
        y = ys[r + span]
        seg = mask[max(0,y-1):y+2, xs[c]+3:xs[c+1]-3]
        if seg.size and seg.mean() > 20: break
        span += 1
    return span

def _deskew(cv2, img):
    edges = cv2.Canny(img, 50, 150)
    lines = cv2.HoughLinesP(edges, 1, np.pi/180, 200,
                            minLineLength=img.shape[1]//3, maxLineGap=8)
    if lines is None: return img
    angles = [np.degrees(np.arctan2(y2-y1, x2-x1))
              for x1,y1,x2,y2 in lines[:,0] if abs(y2-y1) < abs(x2-x1)]
    if not angles: return img
    angle = float(np.median(angles))
    if abs(angle) < 0.05: return img
    M = cv2.getRotationMatrix2D((img.shape[1]//2, img.shape[0]//2), angle, 1)
    return cv2.warpAffine(img, M, (img.shape[1], img.shape[0]),
                          flags=cv2.INTER_CUBIC, borderValue=255)

# --------------------------------------------------------------------------
# Stage 3: per-cell OCR + typography measurement
# --------------------------------------------------------------------------
def ocr_cells(model: PageModel, lang="kor+eng"):
    import cv2, pytesseract
    img = cv2.imread(model.source_image, cv2.IMREAD_GRAYSCALE)
    for cell in model.cells:
        pad = 3
        crop = img[cell.y_px+pad:cell.y_px+cell.h_px-pad,
                   cell.x_px+pad:cell.x_px+cell.w_px-pad]
        if crop.size == 0: continue
        data = pytesseract.image_to_data(crop, lang=lang,
                                         output_type=pytesseract.Output.DICT)
        words, confs, heights, lefts = [], [], [], []
        for i, w in enumerate(data["text"]):
            if w.strip():
                words.append(w); confs.append(float(data["conf"][i]))
                heights.append(data["height"][i]); lefts.append(data["left"][i])
        cell.text = " ".join(words)
        cell.ocr_conf = float(np.mean(confs)) if confs else 0.0
        if cell.text and cell.ocr_conf < OCR_CONF_FLOOR:
            cell.uncertain = True
            cell.text = f"[UNCERTAIN_OCR]{cell.text}"     # never silently guess
        if heights:
            cell.approx_pt = round(float(np.median(heights)) / DPI * 72, 1)
        if lefts and crop.shape[1] > 0:
            center_off = (min(lefts) + (max(lefts) - min(lefts)) / 2) / crop.shape[1]
            cell.align_guess = ("center" if 0.35 < center_off < 0.65
                                else "right" if center_off >= 0.65 else "left")
    return model

# --------------------------------------------------------------------------
# Stage 5: build via Hancom COM (Windows) — style closure valid by construction
# --------------------------------------------------------------------------
def build_hwpx_via_com(model: PageModel, out_path: str):
    import win32com.client as win32
    hwp = win32.gencache.EnsureDispatch("HWPFrame.HwpObject")
    hwp.RegisterModule("FilePathCheckDLL", "FilePathCheckerModule")
    try:
        hwp.XHwpWindows.Item(0).Visible = False
        # page setup from measurements
        _set_page(hwp, model)
        # create table with measured structure
        act = hwp.CreateAction("TableCreate"); ps = act.CreateSet()
        ps.SetItem("Rows", model.n_rows); ps.SetItem("Cols", model.n_cols)
        ps.SetItem("WidthType", 2); ps.SetItem("HeightType", 1)
        act.Execute(ps)
        # per-cell: size, merge, text  (navigate cells via TableCellBlock actions)
        for cell in sorted(model.cells, key=lambda c: (c.row, c.col)):
            _goto_cell(hwp, cell.row, cell.col)
            if cell.col_span > 1 or cell.row_span > 1:
                _merge(hwp, cell.row_span, cell.col_span)
            if cell.text:
                hwp.HAction.GetDefault("InsertText",
                                       hwp.HParameterSet.HInsertText.HSet)
                hwp.HParameterSet.HInsertText.Text = cell.text
                hwp.HAction.Execute("InsertText",
                                    hwp.HParameterSet.HInsertText.HSet)
        _apply_geometry(hwp, model)   # set col widths / row heights in HWPU
        hwp.SaveAs(out_path, "HWPX")
    finally:
        hwp.Quit()

# (COM navigation helpers: implement with TableColBegin/TableRightCell moves,
#  TableCellBlockExtend + TableMergeCell for merges, and Table properties
#  P Set "Table" -> cell width/height items for geometry. Kept as functions
#  so the codex session can fill exact action names against its Hancom version.)
def _set_page(hwp, model): ...
def _goto_cell(hwp, row, col): ...
def _merge(hwp, rspan, cspan): ...
def _apply_geometry(hwp, model): ...

# --------------------------------------------------------------------------
# Stage 6: closed-loop verification — render and overlay against the scan
# --------------------------------------------------------------------------
def verify_against_scan(built_hwpx: str, model: PageModel, workdir: str) -> dict:
    """Render built HWPX (via hancom_render_hook -> PDF -> raster), re-run
    extract_grid on the rendering, and compare line positions to the model."""
    rendered_png = _render_first_page(built_hwpx, workdir)      # uses render hook
    rebuilt = extract_grid(rendered_png)
    report = {"rows_match": rebuilt.n_rows == model.n_rows,
              "cols_match": rebuilt.n_cols == model.n_cols,
              "col_drift_px": [], "row_drift_px": [], "converged": False}
    if report["rows_match"] and report["cols_match"]:
        cw_a = np.cumsum([0] + model.col_widths_hwpu) / PX_TO_HWPU
        cw_b = np.cumsum([0] + rebuilt.col_widths_hwpu) / PX_TO_HWPU
        report["col_drift_px"] = list(np.abs(cw_a - cw_b).round(1))
        rh_a = np.cumsum([0] + model.row_heights_hwpu) / PX_TO_HWPU
        rh_b = np.cumsum([0] + rebuilt.row_heights_hwpu) / PX_TO_HWPU
        report["row_drift_px"] = list(np.abs(rh_a - rh_b).round(1))
        report["converged"] = (max(report["col_drift_px"], default=0) <= GRID_TOLERANCE_PX
                           and max(report["row_drift_px"], default=0) <= GRID_TOLERANCE_PX)
    return report

def _render_first_page(hwpx, workdir) -> str: ...

# --------------------------------------------------------------------------
if __name__ == "__main__":
    image = sys.argv[1]                 # 300-DPI scan page PNG
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("page_model.json")
    m = extract_grid(image)
    m = ocr_cells(m)
    out.write_text(json.dumps(asdict(m), ensure_ascii=False, indent=2), encoding="utf-8")
    uncertain = sum(1 for c in m.cells if c.uncertain)
    print(f"grid: {m.n_rows}x{m.n_cols}, cells={len(m.cells)}, "
          f"uncertain_ocr={uncertain}, margins={m.margin_hwpu}")
