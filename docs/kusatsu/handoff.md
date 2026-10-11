# 草津計画 申し送り(フェーズ7 → 8)

- 済: フェーズ0〜7。読む: `phase4_notes.md`(BuildingSpec と部品)、`phase5/6/7_notes.md`(区域の作り方・地形・申し送り)。
- 次: フェーズ8 区域D(光泉寺の境内・石段など)。`kusatsu/kd_zone_D.py` を kd_zone_B / kd_zone_C の形(手作り関数+`_generic()`+`specs()`)で作る。試作の本堂(`kd_parts_test.honden()`)を入れる。カードは `cards/D_*.md`。
- 地形: `kd_field.NOFLAT_ZONES` に 'D' を足し、`kd_terrain.py -- --zones=D` で再生成。他区域の glb と yubatake.glb の md5 が変わらないこと、周回路・A/B/C の棟の敷地の差が 0 であることを確認(phase7 の確認方法: Field を 2 回作って E の差を測り、影響する D の棟を `FLAT_IDS` へ)。石段(HOSEN)は D の地形に依存。
- 湯路広場の南の黄土色の 5 階(954629639 付近)は区域D 側の建物(phase6_notes 参照)。
- 予算: 区域D 15〜20 万三角形、全体 1.5M 以下(今 約 674k)。
- ユーザー指示: フェーズ8まで続けて実装(8 を 1 コミット)。Blender は同時に 1 つだけ(tasklist で確認)。
