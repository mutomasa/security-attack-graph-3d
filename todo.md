# TODO

設計書 §15 MVP 開発順に沿って、機能ごとにブランチ → PR で進める。
問題点・制約は GitHub Issues に記録する。

## Step 0: リポジトリ準備
- [x] uv プロジェクト初期化 / README / todo.md

## Step 1: Graph モデル (`feature/ontology-seed`, `feature/neo4j-graph-store`)
- [x] オントロジー定義（ノード種別・エッジ種別を一元管理）
- [x] Pydantic スキーマ（Node / Edge / Graph / Path）
- [x] Seed YAML: Scenario A / B / C
- [x] Seed ローダ + バリデーション
- [x] docker-compose で Neo4j 起動（ポート 17474/17687）
- [x] GraphRepository: Neo4j 実装 + インメモリ実装
- [x] seed スクリプト

## Step 2: Attack Path 探索 (`feature/attack-path-engine`)
- [x] 経路探索（Cypher variable length path / networkx）
- [x] リスクスコアリング（設計書 §9.2）
- [x] Top N ランキング

## Step 3: LLM 統合 (`feature/llm-intent`)
- [x] intent 抽出（vLLM + Qwen, structured JSON）
- [x] ルールベース fallback（LLM 未起動時）
- [x] intent → Cypher 生成（テンプレート）
- [x] Cypher ガードレール（読み取り専用・ラベル/エッジ許可リスト・深さ制限）
- [x] 結果説明文生成
- [x] プロンプトを `backend/prompts/` に分離

## Step 4: Backend API (`feature/backend-api`)
- [x] `POST /query`
- [x] `GET /graph/scenario/{scenario_id}`
- [x] `GET /node/{node_id}`
- [x] `POST /seed`
- [x] API テスト
- [x] 追加: `GET /scenarios`, `GET /ontology`, `GET /health`

## Step 5: Three.js 可視化 (`feature/threejs-viewer`)
- [x] ノード色・形状（設計書 §11.3）
- [x] Attack Path 太赤線ハイライト
- [x] hover / click（詳細表示）

## Step 6: Streamlit UI (`feature/streamlit-ui`)
- [x] サイドバー（シナリオ / クエリ例 / しきい値 / 最大深さ）
- [x] 3D ビュー埋め込み・結果サマリ・経路一覧・ノード詳細・Cypher 表示

## Step 7: デモ仕上げ (`feature/demo-polish`)
- [ ] 起動スクリプト（vLLM / backend / streamlit）
- [ ] docs: ontology.md / api_spec.md / demo_script.md
- [ ] README 手順

## Issues
- #2 Neo4j Community では読み取り専用ユーザー不可 → READ access mode + ガードレールで代替
- #4 スコア式（全Σ）だと迂回経路が高スコア → impact を max 集計に変更
- #5 Cypher LIMIT がスコアリング前に効く / ノード一意性の後段フィルタ
- #7 小型 Qwen のハルシネーション → depth/edge は LLM に決めさせない、説明はテンプレート + AI 解説の二本立て
- #10 components.html は一方向 → iframe 内詳細パネル + selectbox で代替
