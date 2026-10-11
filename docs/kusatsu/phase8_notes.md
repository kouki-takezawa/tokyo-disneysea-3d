# 草津計画 フェーズ8 メモ(区域D 光泉寺の境内・石段の周り・駐車場、2026-10-12)

## 作った・変えたファイル
| パス | 内容 |
|---|---|
| `kusatsu/kd_zone_D.py`(新規) | 区域D の全 spec(`specs()`)。手作り+石灯籠・像・碑(小さな spec)+推定(`kd_zone_C._generic` を zone='D' で流用)。区域内の部品: `zD='gate'`(山門)・`'bell'`(鐘楼)・`'chozu'`(手水舎)・`'item'`(石灯籠・碑・像)の `walls`、`att_zD_sorin`(五重塔の相輪)。`--count` / `--list` |
| `kusatsu/kd_field.py` | `NOFLAT_ZONES = {'A','B','C','D'}`。`FLAT_IDS` に区域D の 2 棟(948490098・954629645)を追加 |
| `kusatsu-diorama/app.js`, `index.html` | モデルのキャッシュ既定 `?v=8`、`app.js?v=12` |
| `kusatsu-diorama/models/terrain.glb`, `buildings_D.glb`, `buildings_index.json`, `meta.json` | 更新。**buildings_A/B/C.glb・yubatake.glb は未変更(md5 で確認)** |
| `output/kusatsu/` | `run_D.log`、スクショ `p8_*.jpg` |

## 実行
```
tasklist | grep -i blender
python kusatsu/kd_zone_D.py --count        # Blender 無し、約 20 秒
"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" -b --python kusatsu/kd_terrain.py -- --zones=D > output/kusatsu/run_D.log 2>&1   # 約 60 秒
python -m http.server 8796 --bind 127.0.0.1    # http://127.0.0.1:8796/kusatsu-diorama/?shot&q=standard
```
確認の視点(Three 座標 = Blender (x, z, -y)): 境内の俯瞰 `[-60,62,55]→[-110,24,112]`、山門と石段 `[-56,22,80]→[-72,16,94]`。

## 数値
- 区域D: 38 spec(手作り 13+石灯籠・像・碑 15+推定 10)、**63,344 三角形**、buildings_D.glb 509,272 B。予算 15〜20 万に対して余裕あり(境内は本堂 12.6k・五重塔 10.9k・ぬ志勇旅館 9.0k・庫裏 6.3k・釈迦堂 6.0k)。
- ジオラマ全体(meta.json): terrain 96,949 + yubatake + A 231,667 + B 135,139 + C 196,581 + D 63,344(上限 1.5M)。

## 手作りした建物
本堂(試作のコピー)/ 山門(寄棟・灰銀のとんとん葺き、中央の板敷の通路、朱の室+金網の窓、通路の丸柱+貫+組物)/ 釈迦堂(茅葺き寄棟+千鳥破風、朱の縁と高欄が全周、向拝)/
五重塔(5 重を wings で積み、初重は白壁+朱の扉+緑の連子窓、二〜五重は朱の壁+高欄、金の相輪。高さ 約 17 m は推定)/ 不動堂(黒い宝形)/ 鐘楼(朱の 4 柱+貫+梵鐘)/ 手水舎 / 湯喜堂 /
お守り頒布所(OSM の 2 m 角を実物の 4.5x2.5 m に)/ 庫裏(北の長辺に沿う主棟+南の低い棟)/ ぬ志勇旅館(954629639、3 階の真壁+板葺きの急な切妻)/ 湯畑観光駐車場(3 層)。
小物: 石灯籠 12(OSM の lamp 6 点+釈迦堂の参道の両側 6)、弘法大師像、壹千參百年記念之碑、「草津山 光泉寺」の石碑。石段・擁壁・手すりはフェーズ2(terrain.glb)のまま。

## 地形
- `NOFLAT_ZONES` に 'D'。周回路の近くの D の棟は無い(差 0.000)。均しの縁が区域C の棟の敷地にかかる 2 棟を `FLAT_IDS` に入れ、他区域の敷地内の差は最大 0.002 m(確認済み)。
- 山門は石段の上に載るため、基礎(石積み)が段の低い側へ伸びる。

## 推定・未対応
- 庫裏・光泉寺 付属(OSM 1311927445)・ぐんまみらい信用組合・トイレ棟・ぬ志勇旅館の別の外形(r12857069_*)は推定の様式(動画に出ない)。慈照殿は小さな箱(同定できない)。
- 一茶句碑・筆塚・魚籃観音・仁王像・石の立像・絵馬掛け、本堂前の松、石段の幟、街灯、工事柵は作っていない(幟・街灯はフェーズ9、植物はフェーズ10)。
- 山門の扁額、本堂の扁額・各堂の名称板は文字なし。五重塔の工事用の柵は省いた。駐車場の看板塔は縦札で代用。
