# 草津計画 申し送り(フェーズ8 → 9)

- 済: フェーズ0〜8(区域A〜D の建物がすべて BuildingSpec)。読む: `phase4_notes.md`(部品)、`phase5/6/7/8_notes.md`(区域ごとの作り方・未対応)。
- 次: フェーズ9 看板・小物・電線(実名の看板=読めたものだけ、提灯、のれん、自販機、街灯、電柱・電線、標識、幟)。各区域の notes の「未対応」と `cards/*` の看板・電柱の記述が材料。看板の面は spec の `Attach('sign', text=…)`(`signs` に text/中心/法線が出る)に文字を貼る。
- 地形: 4 区域とも NOFLAT。`FLAT_IDS` は kd_field.py の注釈を読むこと(他区域の glb を作り直さないための棟の一覧)。
- 予算: 全体 1.5M 以下(今 約 0.74M)。Blender は同時に 1 つだけ(tasklist で確認)。
- 公開前の確認: `?v=` のキャッシュ既定(app.js)と `app.js?v=`(index.html)を更新してから Vercel へ(公開はユーザーに確認)。
