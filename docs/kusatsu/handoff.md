# 草津計画 申し送り(フェーズ6 → 7)

- 済: フェーズ0〜6。読む: `phase4_notes.md`(BuildingSpec と部品)、`phase5_notes.md`・`phase6_notes.md`(区域の作り方・地形・申し送り)。
- 次: フェーズ7 区域C(西の河原通りの店並び)。`kusatsu/kd_zone_C.py` を kd_zone_A / kd_zone_B の形(手作り関数+`_generic()`+`specs()`)で作る。試作の山本館(`kd_parts_test.yamamotokan()`)をコピーして入れる(入れないと箱に戻る)。山本館・益成屋は C のカード(C_yamamotokan / C_masunariya)が正。
- ホテル一井 別館(954965075)は重心が区域C なので区域C で作る(B_hotel_ichii の「別館」: 9 階、白い吹付、横長のベランダ帯)。
- 地形: `kd_field.NOFLAT_ZONES` に 'C' を足し、`kd_terrain.py -- --zones=C` で terrain.glb と buildings_C.glb を再生成。周回路の舗装(yubatake.glb)と区域A・B・D の棟の足元が変わらないよう、影響する区域C の棟は `FLAT_IDS` に入れる(確認方法は phase6_notes の「落とし穴」)。buildings_A/B/D.glb・yubatake.glb の md5 が変わらないことを確かめる。
- 予算: 区域C 15〜20 万三角形、全体 1.5M 以下(今 約 611k)。
- ユーザー指示: フェーズ8まで続けて実装(7→8、各1コミット)。Blender は同時に 1 つだけ(tasklist で確認)。
