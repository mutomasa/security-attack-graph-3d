# TODO

設計書 §15 MVP 開発順に沿って、機能ごとにブランチ → PR で進める。
問題点・制約は GitHub Issues に記録する。

## Step 0: リポジトリ準備
- [x] uv プロジェクト初期化 / README / todo.md

## Step 1: Graph モデル (`feature/ontology-seed`, `feature/neo4j-graph-store`)
- [ ] オントロジー定義（ノード種別・エッジ種別を一元管理）
- [ ] Pydantic スキーマ（Node / Edge / Graph / Path）
- [ ] Seed YAML: Scenario A / B / C
- [ ] Seed ローダ + バリデーション
- [ ] docker-compose で Neo4j 起動（ポート 17474/17687）
- [ ] GraphRepository: Neo4j 実装 + インメモリ実装
- [ ] seed スクリプト

## Step 2: Attack Path 探索 (`feature/attack-path-engine`)
- [ ] 経路探索（Cypher variable length path / networkx）
- [ ] リスクスコアリング（設計書 §9.2）
- [ ] Top N ランキング

## Step 3: LLM 統合 (`feature/llm-intent`)
- [ ] intent 抽出（vLLM + Qwen, structured JSON）
- [ ] ルールベース fallback（LLM 未起動時）
- [ ] intent → Cypher 生成（テンプレート）
- [ ] Cypher ガードレール（読み取り専用・ラベル/エッジ許可リスト・深さ制限）
- [ ] 結果説明文生成
- [ ] プロンプトを `backend/prompts/` に分離

## Step 4: Backend API (`feature/backend-api`)
- [ ] `POST /query`
- [ ] `GET /graph/scenario/{scenario_id}`
- [ ] `GET /node/{node_id}`
- [ ] `POST /seed`
- [ ] API テスト

## Step 5: Three.js 可視化 (`feature/threejs-viewer`)
- [ ] ノード色・形状（設計書 §11.3）
- [ ] Attack Path 太赤線ハイライト
- [ ] hover / click（詳細表示）

## Step 6: Streamlit UI (`feature/streamlit-ui`)
- [ ] サイドバー（シナリオ / クエリ例 / しきい値 / 最大深さ）
- [ ] 3D ビュー埋め込み・結果サマリ・経路一覧・ノード詳細・Cypher 表示

## Step 7: デモ仕上げ (`feature/demo-polish`)
- [ ] 起動スクリプト（vLLM / backend / streamlit）
- [ ] docs: ontology.md / api_spec.md / demo_script.md
- [ ] README 手順
