# Tiên Lộ Độ Kiếp 2D CV

**Tiên Lộ Độ Kiếp 2D CV** là game tu tiên 2D top-down kết hợp **combat RPG**, **đột phá cảnh giới**, **boss theo màn**, **VFX pháp thuật**, và mục tiêu chính là điều khiển bằng **Computer Vision / webcam gesture**.

Bản hiện tại có 2 chế độ:

- **Keyboard + Mouse**: dùng để test gameplay nhanh.
- **Computer Vision**: dùng webcam để điều khiển bằng cử chỉ tay.


## Điểm Nổi Bật

- **Không khí tu tiên**: cảnh giới, thiền, đột phá, linh khí, pháp trận, kiếm quang, thiên lôi.
- **3 map chính**: rừng linh mộc, đảo linh thảo, cổ điện địa cung.
- **Wave quái + boss battle**: farm đủ quái để gọi boss, hạ boss để mở màn tiếp theo.
- **8 skill pháp thuật**: mỗi skill có hiệu ứng, vai trò, mana cost và cooldown riêng.
- **Computer Vision**: chọn skill bằng số ngón tay, nắm tay để thi triển, chắp tay để thiền.
- **QA preview**: có ảnh sinh tự động để kiểm tra map, quái, boss, aura và skill VFX.


## Luồng Chơi

1. Vào map và tiêu diệt quái thường.
2. Quái xuất hiện theo wave, có máu vừa phải để combat nhanh.
3. Khi đạt đủ số kill yêu cầu, boss của map xuất hiện.
4. Hạ boss để hoàn thành màn và mở cổng sang map tiếp theo.
5. Khi đủ EXP, thiền/chắp tay để đột phá cảnh giới.
6. Cảnh giới càng cao thì HP, mana, aura và sức mạnh càng tăng.

## Hệ Cảnh Giới

| Cấp | Cảnh giới | Vai trò |
|---:|---|---|
| 1 | Luyện Khí | Nhập môn, học combat cơ bản |
| 2 | Trúc Cơ | Tăng chỉ số, aura rõ hơn |
| 3 | Kết Đan | Mana và sát thương ổn định hơn |
| 4 | Nguyên Anh | Đủ sức đối đầu boss mạnh |
| 5 | Hóa Thần | Aura và sức mạnh tăng mạnh |
| 6 | Vấn Đỉnh | Cảnh giới cao, combat áp đảo hơn |
| 7 | Âm Dương Hư Thực | Mốc demo tối đa hiện tại |

## Skill Người Chơi

![Skill VFX Detail](previews_auto/skills_vfx.png)

| CV / Phím | Skill | Mô tả | Vai trò |
|---:|---|---|---|
| 1 ngón / `1` | Nhất Chỉ Linh Đan | Linh khí bắn nhanh | Đánh đơn mục tiêu |
| 2 ngón / `2` | Nhị Chỉ Kết Giới | Năng lượng tỏa nhiều hướng | Dọn quái gần |
| 3 ngón / `3` | Tam Chỉ Kiếm Quang | Kiếm quang theo hướng ngắm | Đánh tuyến thẳng |
| 4 ngón / `4` | Tứ Chỉ Lôi Ảnh | Lôi ảnh / chain lightning | Đánh nhiều mục tiêu gần nhau |
| 5 ngón / `5` | Ngũ Chỉ Đại Trận | Pháp trận tồn tại nhiều giây, có sét đen | Khống chế vùng lớn |
| `6` | Lục Chỉ Lưu Quang | Lưu quang tỏa rộng | Skill phụ bản phím/chuột |
| `7` | Thất Chỉ Lôi Trận | Lôi trận đánh chuỗi | Skill phụ bản phím/chuột |
| `8` | Bát Chỉ Vân Tinh | Diện rộng cấp cao | Skill phụ bản phím/chuột |

> Chế độ CV tập trung vào 5 skill chính để giảm nhầm gesture. Skill 6–8 dùng được trong Keyboard + Mouse để test combat.

## Điều Khiển Keyboard + Mouse

| Input | Hành động |
|---|---|
| `WASD` | Di chuyển |
| Chuột | Ngắm hướng đánh / skill |
| Chuột trái | Đánh thường |
| Chuột phải | Dùng skill đang chọn |
| `1`–`8` | Chọn và thi triển skill |
| `Space` | Đổi skill đang chọn |
| `C` | Thiền / mô phỏng chắp tay để hồi mana và đột phá |
| `J` | Mua đan hồi HP |
| `K` | Mua đan hồi mana |
| `L` | Mua đan hồi cả HP và mana |
| `N` | Sang map tiếp theo sau khi hạ boss |
| `Esc` | Thoát game |

## Điều Khiển Computer Vision

| Gesture | Hành động |
|---|---|
| Tay trái chỉ hướng | Di chuyển |
| Tay phải chỉ hướng | Ngắm |
| Tay phải dơ 1–5 ngón | Chọn skill 1–5 |
| Nắm tay phải sau khi chọn skill | Thi triển skill |
| Nắm tay phải khi chưa chọn skill | Đánh thường |
| Hai tay gần nhau / chắp tay | Thiền, hồi mana, đột phá |

Góc phải dưới có `CV Preview` kèm landmark bàn tay và debug:

- `F:x`: số ngón game đang đọc.
- `N:y`: điểm nắm tay.
- Nếu `F` đúng nhưng skill chưa đổi, lỗi nằm ở state chọn skill.
- Nếu `F` sai, cần chỉnh thuật toán nhận diện hoặc tư thế tay trong camera.

## Cài Đặt

Khuyến nghị dùng **Python 3.11**.

```powershell
git clone https://github.com/Ngo-Miingg/GameTuTien.git
cd GameTuTien
pip install -r requirements.txt
```

## Chạy Game

```powershell
cd GameTuTien
.\run_2d.ps1
```

Khi vào game, chọn:

- `Keyboard + Mouse`: test gameplay.
- `Computer Vision`: chơi bằng webcam gesture.

## Kiểm Thử

```powershell
cd GameTuTien
python -m py_compile .\*.py
python .\qa_checks.py
python .\preview_snapshots.py
```

Kết quả QA mong đợi:

```text
[QA] passed=75 failed=0 total=75
```

## Đóng Gói EXE

```powershell
cd GameTuTien
.\build_2d.ps1
```

File sau khi build:

```text
GameTuTien\dist\TienLoDoKiep2D\TienLoDoKiep2D.exe
```

Đây là build dạng `onedir`; khi gửi cho máy khác cần giữ nguyên cả thư mục:

```text
dist\TienLoDoKiep2D\
```

## Cấu Trúc Project

| File / thư mục | Vai trò |
|---|---|
| `game_2d.py` | Entry point và game loop bản 2D |
| `game_config.py` | Cấu hình cảnh giới, skill, chỉ số, spawn, cân bằng |
| `game_entities.py` | Entity runtime như quái, boss, projectile |
| `game_combat.py` | Spawn quái/boss, projectile, boss skill |
| `game_vfx.py` | Aura, skill effect, đột phá, telegraph, overlay |
| `game_assets.py` | Load map, sprite, UI, audio và particle assets |
| `game_audio.py` | Chuẩn bị âm thanh runtime |
| `game_input.py` | Điều khiển Keyboard + Mouse |
| `game_cv.py` | Nhận diện tay và xuất raw `move/aim/fingers/fist/clasp` |
| `qa_checks.py` | Kiểm thử tự động asset, map, boss, VFX và flow |
| `preview_snapshots.py` | Xuất ảnh preview để kiểm tra đồ họa |
| `assets/` | Asset game |
| `previews_auto/` | Ảnh preview sinh tự động cho README / QA |

## Asset Sử Dụng

Project tận dụng nhiều asset pack local đã tải về:

- `Valley Ruin Asset Pack`: nền map pixel-art.
- `Ninja Adventure Asset Pack`: quái, boss, actor sprite.
- `Kenney Particle Pack`: hiệu ứng skill, lôi, pháp trận, slash, magic.
- Một số UI/audio asset phụ trong `assets/`.

> Nếu public GitHub hoặc phát hành thương mại, cần tự kiểm lại license của từng asset ngoài đã tải về và giữ attribution theo yêu cầu của từng pack.

## Ghi Chú

- `run_2d.ps1` là entrypoint chính của game 2D.
- `main.py` và `run.ps1` là prototype webcam/thiền đời thực cũ, không phải entrypoint chính của bản game 2D.
- Bản này là demo/prototype, ưu tiên thể hiện ý tưởng **game tu tiên điều khiển bằng Computer Vision**.
