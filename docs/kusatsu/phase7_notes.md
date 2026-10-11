# 草津計画 フェーズ7 メモ(区域C 西の河原通りの店並び・旅館・湯滝通り・湯畑北、2026-10-12)

## 作った・変えたファイル
| パス | 内容 |
|---|---|
| `kusatsu/kd_zone_C.py`(新規) | 区域C の全 spec(`specs()`)。kd_zone_B と同じ形(手作り+`_generic()`)。`--count` / `--list` |
| `kusatsu/kd_field.py` | `NOFLAT_ZONES = {'A','B','C'}`。`FLAT_IDS` に区域C の 4 棟(954629633・954786840・954795983・954965075)を追加 |
| `kusatsu-diorama/app.js`, `index.html` | モデルのキャッシュ既定 `?v=7`、`app.js?v=11` |
| `kusatsu-diorama/models/terrain.glb`, `buildings_C.glb`, `buildings_index.json`, `meta.json` | 更新。**buildings_A/B/D.glb・yubatake.glb は未変更(md5 で確認)** |
| `output/kusatsu/` | `run_C.log`、スクショ `p7_*.jpg` |

## 実行
```
tasklist | grep -i blender
python kusatsu/kd_zone_C.py --count        # Blender 無し、約 25 秒
"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" -b --python kusatsu/kd_terrain.py -- --zones=C > output/kusatsu/run_C.log 2>&1   # 約 80 秒
python -m http.server 8796 --bind 127.0.0.1    # http://127.0.0.1:8796/kusatsu-diorama/?shot&q=standard
```

## 数値
- 区域C: 73 spec(OSM 69 外形を、山本館の別棟・益成屋・極楽館で分割)、**196,581 三角形**、buildings_C.glb 1,542,108 B。予算 15〜20 万以内。
- ジオラマ全体(meta.json の total_tris): 674k(上限 1.5M)。

## 手作りした建物(根拠はカード C_*)
山本館(試作のコピー、床を通りの高さ+0.95 m)/ 山本館 別棟(本館の背面に接する棟+北北東の腕、推定の 3 階・入母屋)/ 益成屋(玄関棟=入母屋+提灯、客室棟=白+薄茶のタイル帯 3 階、西の棟)/
奈良屋(3 階、木のバルコニー、寄棟の下屋、紺の暖簾)/ 群龍館(御影の腰、片持ち庇、縦ルーバー窓)/ 松むら饅頭・山形屋・富貴堂 / 湯畑泉水(縦ルーバー全面、陸屋根)/
関乃湯(溶岩石の腰+白い幕、外形の割り当ては低確度)/ するがや / 極楽館(レンガの腰・ハーフティンバー・吹付、手前と奥に分割)/ ドラゴン / 湯滝通りの黄色い漆喰の棟(位置は推定)/ ホテル一井 別館(9 階、ベランダ帯)。
残り約 55 棟は推定(様式 row_e=入口側の黒柱白壁の旅館並び、row_w=西の店並び、ryokan、back。看板は枠だけ)。

## 地形
- `NOFLAT_ZONES` に 'C'。周回路の近くの C の棟は無い(loop_out+1.5 m の差 0.000)。均しの縁が区域A・B の棟の敷地にかかる 4 棟を `FLAT_IDS` に入れ、他区域の敷地内の差は 0.000 m(確認済み)。確認は A/B/D の glb と yubatake.glb の md5 が不変。
- 1 階の床は正面の道の高さ(`face_z`/`base_for`)+基礎。裏が低い棟は石積みの基礎が伸びる。

## 見比べ(p7_yamamoto.jpg ほか)
- 山本館は黒柱白壁・3 段の庇とバルコニー・唐破風の玄関・石積みの基礎が R 29:18 と合う。区域は通りの並びに入ったが、他は推定の様式なので細部は動画と照合していない。

## 未対応
- 看板・提灯の文字、街灯・電柱・白線(フェーズ9)、奈良屋・益成屋の前庭(石畳・石灯籠・柵)、湯畑泉水のデッキとパラソル、関乃湯の湯だまり。
- 益成屋の客室棟の階数(3 か 4)、奈良屋・群龍館の屋根、湯畑泉水の屋根と上階の窓は推定。
