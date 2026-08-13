# CUT06–CUT08 — 복도 → 엘리베이터 탑승 → B1 → 문 닫힘

> Higgsfield / Seedance 2.0 block-scaffold I2V prompt pack
> 기준: `OSideMedia/higgsfield-ai-prompt-skill` v3.31.0 — HARD RULES 1–8, § Official Prompt Architecture, § POSITIVE LOCKS, `templates/seedance/global-style-prefix.md`

---

## 0. 출력 설정 (UI 헤더 — 프롬프트 본문에 넣지 말 것)

| 항목 | 값 | 근거 |
|---|---|---|
| **Model** | Seedance 2.0 (`seedance_2_0`) | `start_image` 미디어 롤 지원 = I2V first_frame |
| **Aspect ratio** | `16:9` | 모델 enum: auto/16:9/9:16/4:3/3:4/1:1/21:9 |
| **Resolution** | `1080p` | 1920×1080. **`mode=std` 필수** (fast는 480p/720p만) |
| **Mode** | `std` | |
| **Duration** | `4` | enum min 4 / max 15 |
| **bitrate_mode** | `high` | |
| **genre** | `auto` | |
| **generate_audio** | `false` | ※ 기본값이 `true`. 끄지 않으면 Seedance가 사운드를 창작함 |
| **start_image** | `CUT06/07/08_FIRST_FRAME_CLEAN.png` | 컷마다 각각 |

> **HARD RULE 7** — 화면비·해상도는 모델별 enum이며 UI에서 설정한다. 프롬프트 본문의 `1920x1080` 같은 표기는 무시되거나 노이즈가 된다. `24 fps`는 파라미터가 아니므로 기술 스타일 선언으로 본문에 남긴다.

---

## 1. GLOBAL STYLE PREFIX (보강판)

> 컷 프롬프트마다 **맨 위에 그대로 복사해 붙인다.** 매 생성은 이전 생성의 기억이 없는 백지 상태다(context isolation). 한 번 고치면 전 컷에 다시 붙여넣는다.

```
Format: 16:9 widescreen, 24 fps, 180-degree shutter motion blur. Photorealistic live action - no 3D render, no game engine.
Camera: strict embodied POV, one operator, eye height 1.64 m, 63-degree FOV held constant with no drift mid-segment. The frame is exactly what the walker's eyes see; she exists in the shot only as that viewpoint.
Optics: physical cine lens. Sharp focus throughout, deep depth of field. Motion blur comes from gait alone.
Lighting: motivated sources only - daylight entering from the left and northwest, weak uneven ceiling fixtures at 4000K, exposure held 0.3 stop under key. White balance stays 4000K for the whole clip.
Color: desaturated institutional palette - ochre floor line, blue-gray steel, warm-white wall paint. One reserved accent: the red of the single streaked apple.
Texture: any visible skin renders at pore level - blemishes, flyaway hair, cloth wrinkles, fingerprints, scratches, scuffs, dust and unevenly rolled paint all hold full sharpness. Natural skin texture, subtle imperfections.
Physics: gravity, mass, inertia, friction, contact, weight transfer and joint limits all respected. The walker is 70 kg and every footfall lands with that weight. Props move only from a visible physical cause.
Carried items: ivory cuff, steel watch, clipboard, pencil and one red streaked apple enter the frame only at the lower edge, carried there by gait and inertia, each free to swing and settle on its own mass.
Continuity: characters, props, architecture and floor markings stay identical across every cut, exactly as the reference frame shows. Consistent appearance, same outfit and features throughout.
Audio: diegetic environmental sound only - footsteps, room tone, mechanical events. No music, no voice, no subtitles.
```

## 2. POSITIVE LOCKS (기존 `[NEGATIVE]` 대체)

> 컷 프롬프트마다 **맨 아래에 그대로 복사해 붙인다.**

```
The set contains only what the reference frame shows - no added corridors, doors, rooms, furniture or geography beyond the reference. Architecture stays fixed in place for the whole clip; walls, doors, rails and floor markings hold their exact positions.
The viewpoint stays first-person from first frame to last, and every surface keeps a matte non-reflective finish.
Exactly one of each present element - one person, one cart, one cassette, one apple, one pair of hands. The counts hold for the whole clip.
Hands stay anatomically correct, all limbs visible and naturally positioned, five separated fingers, natural joint limits.
Feet keep full contact with the floor on every step and the floor holds still beneath them. Wheels rotate in proportion to the distance travelled.
Props rest on their supports with correct contact shadows and stay held by whatever holds them.
Chimpanzees stay quadrupedal and load their front knuckles first.
Motion runs at variable speed throughout - accelerate, hold, decelerate. The camera moves only as the walking body moves it, and holds level.
Cuts only at the specified points; the camera does not cut on its own.
Every surface stays free of text, numbers, signage, logos, captions, interface overlays and watermarks.
Skin, fur and metal keep real material response - subsurface scatter in skin, irregular fur direction, brushed metal with micro-scratches and uneven specular.
```

---

## 3. CUT06 — CORRIDOR RUN-OUT / CALL BUTTON

```
SCENE CONTEXT
A north-south service corridor ends at a closed elevator opening in the east wall. Daylight from a window off to the left rakes across the floor; the ochre guide line runs east along the base of the wall toward the sill.

ACTIVE REFERENCES
@image1 - the first frame, CUT06_FIRST_FRAME_CLEAN.png. It carries the whole set: corridor width, door position, call plate, floor line. 100% matches the reference.

LOCATION MAP
Closed elevator doors ahead at the east end. Call plate on the south jamb, screen-right of the opening at 1.1 m. Blank wall screen-left. The corridor ends here; nothing continues past the doors.

FORMAT MODE
One continuous shot.

OPTICS
63-degree FOV, held constant, no drift mid-segment.

CAMERA
Embodied POV, eye height 1.64 m. The camera advances east only by the walking body, then stops. Horizon holds level. The move ends with the closed doors filling the centre of the frame and the call plate at the lower right.

ACTION
0.00-1.20s: three strides east at 4 km/h; the doors grow in frame with each footfall.
1.20-2.30s: strides progressively shorten and the body decelerates to a full stop one arm's length from the doors. The apple hand swings slightly forward on inertia, then settles.
2.30-3.10s: the right hand rises into the lower right of frame and the index finger extends toward the call plate.
3.10-4.00s: a full mechanical press - contact, 2-3 mm of travel, a click, then spring-back. The call lamp lights only AFTER the click. The hand withdraws to the lower edge.

PHYSICS
70 kg of body weight transfers heel-to-toe on every step and the deceleration loads the forward foot. The clipboard and cuff lag a beat behind each change of speed and settle on their own mass.

LIGHTING
Daylight from the left and northwest rakes the floor; weak uneven ceiling fixtures at 4000K fill the rest. Exposure sits 0.3 stop under key.

AUDIO
Four footfalls on hard floor with the last one shortest, corridor room tone, one plastic button click.

STYLE
24 fps, 180-degree shutter motion blur, physical cine lens, photorealistic live action.

POSITIVE LOCKS
[위 §2 블록을 그대로 붙여넣기]
The call lamp is dark until the click and stays lit afterwards. The elevator doors stay fully closed for the entire clip.
```

---

## 4. CUT07 — CAR ENTRY / TURN WEST

```
SCENE CONTEXT
The elevator doors open onto an empty car. The walker steps in from the corridor and turns to face back the way she came.

ACTIVE REFERENCES
@image1 - the first frame, CUT07_FIRST_FRAME_CLEAN.png. It carries the door leaves, sill, car interior and light fixture. 100% matches the reference.

LOCATION MAP
Two door leaves ahead, closed at the centre line, retracting north and south into their pockets. Grooved sill at the threshold. Car interior beyond: brushed steel walls, one ceiling fixture, control panel on the north wall.

FORMAT MODE
One continuous shot.

OPTICS
63-degree FOV, held constant, no drift mid-segment.

CAMERA
Embodied POV, eye height 1.64 m. The camera crosses the sill on the walking body, then yaws through a single curved 180-degree turn and stops. The turn ends with the open doorway and the corridor beyond centred in frame, horizon level.

ACTION
0.00-0.50s: the two leaves slide apart from the centre line on one rigid guide path, retracting north and south with believable mass and a slight settle at full open.
0.50-0.95s: one breath and a weight shift; a brief 6-8 degree downward glance checks the sill.
0.95-1.85s: two steps east across the grooved sill. A small contact bob as the car floor takes the weight, and a faint vibration through the frame.
1.85-2.95s: one curved 180-degree turn to the left, yaw easing into a stop, feet pivoting in two placements against the car floor.
2.95-4.00s: everything settles. Only breathing and minute eye motion remain.

PHYSICS
The door leaves carry real mass - they accelerate, run, and decelerate into the pocket rather than snapping. The step down onto the car floor loads 70 kg through one foot. The clipboard and apple swing outward on the turn and settle inward as the yaw stops.

LIGHTING
Daylight from the left and northwest falls off sharply as the body enters the car; inside, only the weak 4000K ceiling fixture remains. White balance holds 4000K throughout.

AUDIO
Door mechanism running and seating, two footfalls with a hollow car-floor resonance, the shoe pivot, room tone dropping to a tighter enclosed space.

STYLE
24 fps, 180-degree shutter motion blur, physical cine lens, photorealistic live action.

POSITIVE LOCKS
[위 §2 블록을 그대로 붙여넣기]
The car interior contains only its steel walls, ceiling fixture and control panel. The doors open once and stay open for the rest of the clip. The turn runs once, in one direction, to a stop.
```

---

## 5. CUT08 — B1 SELECTION / DOORS CLOSE

```
SCENE CONTEXT
Inside the car, facing the open doorway. One floor is selected and the doors close.

ACTIVE REFERENCES
@image1 - the first frame, CUT08_FIRST_FRAME_CLEAN.png. It carries the car interior, the control panel column and the open doorway. 100% matches the reference.

LOCATION MAP
Open doorway ahead to the west with the corridor visible beyond. Control panel on the north wall, screen-right, a single vertical column of round buttons with the B1 button one position below the ground-floor button. Brushed steel walls left and right.

FORMAT MODE
One continuous shot.

OPTICS
63-degree FOV, held constant, no drift mid-segment.

CAMERA
Embodied POV, eye height 1.64 m. The camera yaws right once to bring the panel into frame, then yaws back once to square on the doorway and holds there. The clip ends on the closed doors filling the centre of the frame.

ACTION
0.00-0.55s: near-still. One breath; the open doorway and the corridor beyond hold in frame.
0.55-1.35s: a single 20-25 degree yaw to the right brings the panel column into the frame.
1.35-2.10s: the right hand rises into the lower right of frame and the index finger extends to the B1 button.
2.10-2.60s: a full mechanical press - contact, 2-3 mm of travel, a click, then spring-back. The B1 lamp lights only AFTER the click and stays lit.
2.60-3.20s: the hand withdraws to the lower edge and a single 20-25 degree yaw to the left squares the frame back on the doorway.
3.20-4.00s: the two leaves run toward each other from north and south at matched speed and meet at the centre line with one soft gasket compression. The daylight from the corridor narrows to a vertical seam and goes out.

PHYSICS
The button travels 2-3 mm under finger pressure and springs back on release. The door leaves carry real mass, accelerating off their stops and decelerating into the seal.

LIGHTING
Corridor daylight reaches into the car through the open doorway and narrows with the closing gap until only the weak 4000K ceiling fixture lights the car. White balance holds 4000K throughout.

AUDIO
One breath, cloth movement at the sleeve, one firm button click, door mechanism running and sealing, room tone closing in.

STYLE
24 fps, 180-degree shutter motion blur, physical cine lens, photorealistic live action.

POSITIVE LOCKS
[위 §2 블록을 그대로 붙여넣기]
The gaze turns right once and returns left once, each in a single continuous move, and holds still between them. The B1 lamp is dark until the click and lit for the rest of the clip. The doors are open from the first frame and close once, meeting at the centre line.
```

---

## 6. 편집 노트 (프롬프트 본문 밖 — 절대 붙여넣지 말 것)

- CUT06 / CUT07 — 4초 생성, **0.0–3.0s 사용.**
- CUT08 — **4.0초 전체 사용.** 문이 닫히는 페이오프가 3.20–4.00s 구간에 있으므로 3초로 자르면 씬이 없어진다.
- 컷 순서: CUT06 → CUT07 → CUT08.
