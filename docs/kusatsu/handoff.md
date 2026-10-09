# 草津計画 申し送り(フェーズ2 → 3)

- 済: フェーズ0〜2。詳細は `docs/kusatsu/phase2_notes.md`(座標 Z=標高−1153、実行コマンド、落とし穴)を必ず読む。
- 次: フェーズ3 湯畑(Opus)。池: 南西端 (-11.95,-21.81)、北東端 (10.81,26.71)、縁(周回路)Z 0.87、水面 Z 0.42、底 Z -0.23。現在の池は仮の瓢箪形、周回路の舗装と池の縁は未作成。
- 流れ: `blender.exe -b --python kusatsu/kd_terrain.py`(約6秒)→ `kusatsu-diorama/models/` → `python -m http.server <port>` で `/kusatsu-diorama/`。Blender は1つずつ(tasklist で確認)。
- ユーザー指示: フェーズ8まで続けて実装。
