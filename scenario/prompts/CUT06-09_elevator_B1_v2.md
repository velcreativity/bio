# CUT06–CUT09 — 복도 → 호출 버튼 → 탑승 → B1 → 하강 (v2, 실제 플레이트 기준)

> Higgsfield / Seedance 2.0 block-scaffold I2V prompt pack
> 기준: `OSideMedia/higgsfield-ai-prompt-skill` v3.31.0
> **v1(`CUT06-08_elevator_B1.md`) 폐기** — POV / 주광 / 황토색 바닥선을 전제했으나 실제 플레이트에 셋 다 없음.

---

## 0. 플레이트 판독 → 컷 배치

| 플레이트 | 내용 | 배치 |
|---|---|---|
| **A** (복도 뒷모습) | 좁은 스틸 복도, 천장 형광 스트립, 흰 가운 뒷모습, 우측 손에 붉은 사과, 낮게 묶은 머리 | **CUT06 start_image** — 3인칭 팔로우 |
| **B** (차내) | 문 닫힘, 패널 우측(2/1/B1/B2), **B1 이미 점등**, 인디케이터 `↓2`, 좌우 핸드레일, 문 상단 라인 조명 | **CUT09 start_image** — 하강 |

**플레이트 B는 "이미 누르고, 이미 닫힌" 상태입니다.** 그래서 버튼을 누르는 컷의 시작 프레임이 될 수 없습니다. 남은 동작은 하강뿐이므로 하강 컷에 배치했습니다.

**CUT07 / CUT08은 시작 프레임이 없습니다.** §6에 이미지 생성 프롬프트를 넣었습니다.

### 카메라 문법 — 관찰 → 주관 전환

플레이트 A는 **3인칭 뒷모습**, 플레이트 B는 **차내 1인칭 시점**(빈 차, 눈높이, 문 정중앙, 양쪽 핸드레일이 손 높이)입니다. 두 판을 문자 그대로 받으면 이 씬은 복도에서 관찰하다가 **문턱을 넘는 순간 주관으로 넘어갑니다.** 3분 단편의 카메라 규칙(관찰 대상 → 주관 시점 전환)과 같은 문법이라 그대로 채택했습니다. 전 컷 3인칭으로 통일하려면 CUT08·09의 CAMERA 블록만 교체하면 됩니다.

---

## 1. 출력 설정 (UI 헤더 — 프롬프트 본문에 넣지 말 것)

| 항목 | 값 |
|---|---|
| **Model** | Seedance 2.0 (`seedance_2_0`) |
| **Aspect ratio** | `16:9` |
| **Resolution** | `1080p` — **`mode=std` 필수** |
| **Mode** | `std` |
| **Duration** | `4` |
| **bitrate_mode** | `high` / **genre** `auto` |
| **generate_audio** | `false` (기본값 true — 끄지 않으면 사운드를 창작함) |
| **start_image** | CUT06 = 플레이트 A · CUT07/08 = §6으로 생성 · CUT09 = 플레이트 B |

---

## 2. GLOBAL STYLE PREFIX (플레이트 기준 재작성)

> 컷 프롬프트마다 **맨 위에 그대로 복사해 붙인다.** 매 생성은 백지 상태다.

```
Format: 16:9 widescreen, 24 fps, 180-degree shutter motion blur. Photorealistic live action - no 3D render, no game engine.
Subject: one figure in a white belted lab coat, dark hair gathered in a low bun at the nape, carrying one red apple in the right hand at hip height. She is 165 cm and 55 kg. She is seen from behind or not at all; her face never turns toward the lens. 100% matches the reference.
Optics: physical cine lens. Sharp focus throughout, deep depth of field. Motion blur comes from her gait and from mechanical travel only.
Lighting: practical sources only - recessed linear ceiling fluorescents at 4000K and nothing else. No daylight, no window, no exterior source. White balance holds 4000K for the whole clip. Exposure sits 0.3 stop under key, shadows retain detail.
Color: cold desaturated institutional palette - gunmetal wall panels, brushed steel, warm-gray floor, off-white coat. One reserved accent, the red of the single apple.
Surfaces: brushed steel returns soft diffuse specular streaks along its grain direction and holds every scratch, fingerprint, seam and scuff at full sharpness. Cloth wrinkles, flyaway hair and uneven paint all read.
Physics: gravity, mass, inertia, friction, contact, weight transfer and joint limits all respected. Every footfall lands with her real weight. Props and mechanisms move only from a visible physical cause. The apple stays held in the right hand and swings on its own mass with her gait.
Continuity: the corridor, the car interior, the handrails, the panel legends and the floor identical across every cut, exactly as the reference frame shows. Consistent appearance, same coat and hair throughout.
Audio: diegetic environmental sound only - footsteps, room tone, mechanical events. No music, no voice, no subtitles.
```

## 3. POSITIVE LOCKS

> 컷 프롬프트마다 **맨 아래에 그대로 복사해 붙인다.**

```
The set contains only what the reference frame shows - no added corridors, doors, rooms, furniture or geography beyond the reference. Architecture stays fixed in place for the whole clip; walls, seams, handrails and floor hold their exact positions.
Brushed steel and painted panels return soft diffuse specular streaks only, and never resolve a mirror image of the figure or the room.
Exactly one figure and exactly one apple are present, and the counts hold from first frame to last.
Hands stay anatomically correct, all limbs visible and naturally positioned, five separated fingers, natural joint limits.
Feet keep full contact with the floor on every step and the floor holds still beneath them.
Her face stays away from the lens for the entire clip.
Every legend on the control panel reads exactly as the reference shows it and stays unchanged. No new text, numbers, signage, logos, captions, interface overlays or watermarks appear on any surface.
Motion runs at variable speed throughout - accelerate, hold, decelerate. Camera and mechanism each move once, in one direction, to a stop.
One continuous shot; the camera does not cut on its own.
Skin, cloth and metal keep real material response - subsurface scatter in skin, woven texture in the coat, brushed metal with micro-scratches and uneven specular.
```

---

## 4. CUT06 — CORRIDOR APPROACH  *(start_image = 플레이트 A)*

```
SCENE CONTEXT
A narrow steel-clad service corridor. Recessed linear fluorescents run overhead down its length. A figure in a white lab coat walks away from the camera toward the elevator at the far end.

ACTIVE REFERENCES
@image1 - the first frame. It carries the corridor width, wall seams, ceiling fixture spacing, the coat, the hair and the apple. 100% matches the reference.

LOCATION MAP
Steel wall panels with vertical seams left and right, closing in toward a vanishing point. Recessed linear fluorescents overhead in a receding row. Warm-gray floor. The elevator doors sit at the far end, ahead of her and beyond the current frame.

FORMAT MODE
One continuous shot.

OPTICS
47-degree FOV, held constant, no drift mid-segment.

CAMERA
Third person, following from behind at 1.5 m eye height, trailing her at a fixed distance on a smooth path. Horizon holds level. The move ends with her decelerating in the centre of the frame and the closed elevator doors filling the far end.

ACTION
0.00-1.60s: four strides away from camera at 4 km/h. The coat hem swings behind each leg, the apple swings forward and back in the right hand, and the ceiling fixtures pass overhead in an even rhythm.
1.60-2.80s: the elevator doors resolve at the end of the corridor as she closes the distance. Her strides hold pace.
2.80-4.00s: strides progressively shorten and she decelerates to a stop an arm's length from the doors. The coat hem and the apple carry forward on inertia, then settle.

PHYSICS
55 kg transfers heel-to-toe on every step and the deceleration loads the forward foot. The coat lags a beat behind each change of speed. The apple stays gripped and never leaves the hand.

LIGHTING
Recessed linear fluorescents at 4000K overhead, each one throwing a soft pool that passes across her shoulders as she walks under it. Steel walls carry vertical specular streaks along the grain.

AUDIO
Eight footfalls on hard floor with the last two shortest, a tight enclosed corridor room tone, faint ballast hum from the fixtures.

STYLE
24 fps, 180-degree shutter motion blur, physical cine lens, photorealistic live action.

POSITIVE LOCKS
[§3 블록 그대로 붙여넣기]
The elevator doors stay fully closed for the entire clip. She walks away from the lens for the whole clip and never turns back toward it.
```

---

## 5. CUT07 — CALL BUTTON / DOORS OPEN  *(start_image = §6-A로 생성)*

```
SCENE CONTEXT
She stands at the closed elevator doors at the end of the corridor, presses the call button, and the doors open.

ACTIVE REFERENCES
@image1 - the first frame. It carries the closed doors, the call plate, the corridor walls and her stance from behind. 100% matches the reference.

LOCATION MAP
Closed brushed-steel elevator doors filling the centre of frame, meeting at a vertical centre seam. Call plate on the wall to the right of the opening at 1.1 m. Steel corridor walls left and right.

FORMAT MODE
One continuous shot.

OPTICS
47-degree FOV, held constant, no drift mid-segment.

CAMERA
Third person, locked off behind her at 1.5 m eye height. The camera holds still for the whole clip and lets the doors do the moving.

ACTION
0.00-0.70s: she stands still. One breath lifts and drops her shoulders; the apple hangs steady in the right hand.
0.70-1.40s: her left arm lifts and the index finger extends to the call plate.
1.40-1.90s: a full mechanical press - contact, 2-3 mm of travel, a click, then spring-back. The call lamp lights only AFTER the click and stays lit. The arm lowers back to her side.
1.90-3.10s: the two door leaves slide apart from the centre seam on one rigid guide path, retracting left and right into their pockets with believable mass, accelerating off the stops and decelerating into full open. Brighter car light spills out across the corridor floor and up her coat.
3.10-4.00s: she takes one step forward toward the open car; the coat hem swings and settles.

PHYSICS
The door leaves carry real mass and run rather than snap. The button travels 2-3 mm under finger pressure and springs back on release. Her shoulder drops slightly as the arm lowers.

LIGHTING
Corridor fluorescents at 4000K throughout. As the doors open, the car's own ceiling fixture adds a second 4000K pool that widens across the floor with the gap.

AUDIO
One breath, cloth movement at the sleeve, one firm button click, door mechanism running and seating, one footfall.

STYLE
24 fps, 180-degree shutter motion blur, physical cine lens, photorealistic live action.

POSITIVE LOCKS
[§3 블록 그대로 붙여넣기]
The call lamp is dark until the click and stays lit afterwards. The doors are closed at the first frame, open once, and stay open for the rest of the clip. The camera holds locked off and still.
```

---

## 6-1. CUT08 — SELECT B1 / DOORS CLOSE  *(start_image = §6-B로 생성 · end_image = 플레이트 B)*

> Seedance 2.0은 `end_image`를 지원합니다. **플레이트 B를 end_image로 넣으면** B1 소등→점등, 문 열림→닫힘이 클립 안에서 진행되어 공급하신 판 그대로 착지합니다. 이게 이 플레이트의 가장 정확한 사용법입니다.

```
SCENE CONTEXT
Inside the car, facing the open doors. One floor is selected and the doors close.

ACTIVE REFERENCES
@image1 - the first frame: the car interior from standing eye height, doors open, control panel to the right, B1 unlit.
@image2 - the last frame: the same car with the doors closed and the B1 button lit amber. The clip lands exactly on this state. 100% matches the references.

LOCATION MAP
Open doorway ahead with the corridor visible beyond. Gunmetal wall panels left and right, a brushed steel handrail along each at 0.9 m. Control panel on the right wall as a single column - indicator display at the top, then a round call icon, then square buttons reading 2, 1, B1, B2 downward, then the two door-control buttons. One linear ceiling fixture above the door header.

FORMAT MODE
One continuous shot.

OPTICS
63-degree FOV, held constant, no drift mid-segment.

CAMERA
Embodied first person at 1.55 m eye height, standing in the middle of the car. The camera yaws right once to bring the panel column into frame, then yaws back once to square on the doorway and holds there. The clip ends on the closed doors centred in frame.

ACTION
0.00-0.55s: near-still. One breath; the open doorway and the corridor beyond hold in frame.
0.55-1.30s: a single 25-degree yaw to the right brings the panel column fully into frame.
1.30-2.00s: the left hand rises into the lower right of frame and the index finger extends to the B1 button, the third square down in the column.
2.00-2.50s: a full mechanical press - contact, 2-3 mm of travel, a click, then spring-back. The B1 legend lights amber only AFTER the click and stays lit. The hand withdraws to the lower edge.
2.50-3.15s: a single 25-degree yaw to the left squares the frame back on the open doorway.
3.15-4.00s: the two door leaves run toward each other from left and right at matched speed and meet at the centre seam with one soft gasket compression. The corridor light narrows to a vertical seam and goes out, leaving only the car's own ceiling fixture.

PHYSICS
The button travels 2-3 mm under finger pressure and springs back on release. The door leaves carry real mass, accelerating off their stops and decelerating into the seal. The apple stays gripped in the right hand at the lower edge of frame.

LIGHTING
The car's linear ceiling fixture at 4000K is the constant key, throwing a bright band across the door header. Corridor light reaches in through the open doorway and narrows away with the closing gap.

AUDIO
One breath, cloth movement at the sleeve, one firm button click, door mechanism running and sealing, room tone closing into a tighter enclosed space.

STYLE
24 fps, 180-degree shutter motion blur, physical cine lens, photorealistic live action.

POSITIVE LOCKS
[§3 블록 그대로 붙여넣기]
The gaze turns right once and returns left once, each in a single continuous move, and holds still between them. The B1 legend is unlit until the click and lit amber for the rest of the clip; every other button legend stays unlit and unchanged. The doors are open at the first frame and close once, meeting at the centre seam.
```

---

## 6-2. CUT09 — DESCENT  *(start_image = 플레이트 B)*

```
SCENE CONTEXT
The car begins its descent. Nothing moves but the car itself.

ACTIVE REFERENCES
@image1 - the first frame. It carries the closed doors, the panel column with B1 lit amber, the indicator display, both handrails and the floor. 100% matches the reference.

LOCATION MAP
Closed brushed-steel doors filling the centre of frame, meeting at a vertical centre seam. Gunmetal wall panels left and right with a steel handrail along each. Control panel on the right wall, B1 lit amber. One linear ceiling fixture above the door header.

FORMAT MODE
One continuous shot.

OPTICS
63-degree FOV, held constant, no drift mid-segment.

CAMERA
Embodied first person at 1.55 m eye height, locked in place. The camera holds still and moves only with the car.

ACTION
0.00-0.60s: the car takes up its load and settles a few millimetres; the whole frame drops and recovers once.
0.60-3.20s: a continuous fine vibration runs through the frame as the car descends. The ceiling fixture's reflection creeps slowly along the grain of the door panels. The apple in the lower edge of frame trembles faintly against the hand.
3.20-4.00s: the vibration steadies into a constant hum and the frame holds.

PHYSICS
The initial acceleration downward unloads body weight for a fraction of a second, which reads as one small settle of the whole frame. Everything not fixed to the car - the coat hem, the apple, loose hair - lags that settle by a beat.

LIGHTING
The car's linear ceiling fixture at 4000K is the only source and holds constant. The B1 legend holds its amber glow.

AUDIO
Hoist machinery taking load, a low continuous travel hum, faint structural creak, tight enclosed room tone.

STYLE
24 fps, 180-degree shutter motion blur, physical cine lens, photorealistic live action.

POSITIVE LOCKS
[§3 블록 그대로 붙여넣기]
The doors stay fully closed for the entire clip. The indicator display and every button legend hold exactly the characters the reference shows and do not change. The B1 legend stays lit amber throughout. The camera stays locked and the only movement in frame is vibration.
```

> **인디케이터 숫자를 바꾸지 않는 이유** — 생성 모델은 화면 속 글자·숫자가 *변하는* 것을 제대로 못 그립니다(뭉개지거나 다른 글자로 morph). 2 → 1 → B1 카운트다운이 필요하면 별도 인서트 컷으로 찍거나 후반에서 합성하십시오. 하강감은 진동·설렘·사운드로 충분히 전달됩니다.

---

## 6. 누락 프레임 생성 프롬프트 (Nano Banana Pro / Seedream 등 스틸 모델용)

### A. `CUT07_FIRST_FRAME.png`

```
Photorealistic still frame, 16:9. A figure in a white belted lab coat with dark hair gathered in a low bun stands with her back to the lens, an arm's length from a pair of closed brushed-steel elevator doors at the end of a narrow steel-clad corridor. She holds one red apple in her right hand at hip height. Her face is not visible. A call plate with a single round button sits on the wall to the right of the doors at 1.1 m, its lamp unlit. Steel wall panels with vertical seams run left and right; recessed linear fluorescents at 4000K run overhead. Warm-gray floor. Cold desaturated institutional palette, gunmetal and brushed steel, the apple the only saturated colour. Sharp focus throughout, deep depth of field, natural skin texture, subtle imperfections. Practical ceiling light only, no daylight, exposure 0.3 stop under key.
```

### B. `CUT08_FIRST_FRAME.png`

```
Photorealistic still frame, 16:9. Interior of an elevator car photographed from standing eye height at 1.55 m in the middle of the car, facing a pair of open brushed-steel doors with a dim steel corridor visible beyond. Gunmetal wall panels left and right, one brushed-steel handrail along each at 0.9 m. A control panel on the right wall runs as a single vertical column - an indicator display at the top, a round call icon below it, then four square buttons reading 2, 1, B1, B2 downward, then two door-control buttons. Every button legend is unlit. One linear ceiling fixture at 4000K above the door header throws a bright band across it. Textured warm-gray floor. Cold desaturated institutional palette. Sharp focus throughout, deep depth of field, brushed metal with micro-scratches and uneven specular. Practical ceiling light only, no daylight, exposure 0.3 stop under key.
```

---

## 7. 편집 노트 (프롬프트 본문 밖 — 붙여넣지 말 것)

- 컷 순서: CUT06 → CUT07 → CUT08 → CUT09.
- **CUT07·CUT08·CUT09는 4.0초 전체를 쓴다.** 각각의 페이오프(문 열림 / 문 닫힘 / 하강 안착)가 3초 이후에 있다.
- CUT06만 3.0초에서 잘라도 무방하다.
- 4컷 16초가 길면 **CUT09를 먼저 버린다.** CUT08이 문 닫힘으로 끝나므로 씬은 그대로 성립한다.
