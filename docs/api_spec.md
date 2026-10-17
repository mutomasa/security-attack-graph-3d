# API 仕様

起動: `uv run uvicorn backend.main:app --port 8010` — OpenAPI は `http://localhost:8010/docs`

## POST /query

自然言語の質問から Attack Path を返す。

Request
```json
{"question": "顧客データに到達する最も危険な経路は？", "scenario": "demo_company_a",
 "top_n": 3, "max_depth": 8, "min_score": 0}
```
| field | 制約 |
|---|---|
| `question` | 1〜500 文字 |
| `top_n` | 1〜50（既定 3。intent が一覧なら最低 10） |
| `max_depth` | 1〜10（省略時 8） |
| `min_score` | このスコア未満の経路を除外 |

Response（抜粋）
```json
{
  "intent": "find_highest_risk_path",
  "intent_detail": {"intent": "find_highest_risk_path", "source": "Internet", "target": "Customer Data",
                    "max_depth": 8, "path_types": ["EXPOSED_TO", "..."], "parsed_by": "llm"},
  "cypher": "MATCH p = (start {scenario: \"demo_company_a\"}) ...",
  "paths": [{"score": 16.19,
             "score_breakdown": {"Asset": 5, "Vulnerability": 8.19, "Identity": 4, "Data": 5,
                                 "edge_ease": 1.0, "length_penalty": -6},
             "nodes": [{"id": "a_internet", "label": "Internet", "type": "NetworkZone", "zone": "external"}],
             "edges": [{"source": "a_internet", "target": "a_web", "type": "EXPOSED_TO", "weight": 1.0}]}],
  "summary": "最も危険な経路（スコア 16.19）は、Internet から公開された Web Server に到達し、…",
  "explanation": "（LLM による解説。LLM 停止時は null）",
  "permissions": [],
  "reached": []
}
```

intent の種類

| intent | 例 | 追加フィールド |
|---|---|---|
| `find_highest_risk_path` | 顧客データに到達する最も危険な経路は？ | — |
| `list_attack_paths` | Internet から侵入可能な経路だけ表示して | — |
| `blast_radius` | Service Account が漏洩した場合の影響範囲は？ | `reached`（到達可能な Asset / Data / Identity / Secret） |
| `required_permissions` | S3 Bucket に到達するまでに必要な権限は？ | `permissions`（Top1 経路上の Identity が持つ権限） |

エラー: 未知のシナリオ 404、入力検証エラー 422。

## GET /graph/scenario/{scenario_id}
シナリオ全体のグラフ `{scenario: {...}, nodes: [...], edges: [...]}`。未投入なら 404。

## GET /node/{node_id}?scenario={scenario_id}
`{node, scenario_id, outgoing, incoming, neighbors}`。`scenario` 省略時は全シナリオを探す。

## POST /seed
`data/seed/*.yaml` を投入（シナリオ単位で置き換え）。`{"seeded": ["demo_company_a", ...]}`

## GET /scenarios / GET /ontology / GET /health
シナリオ一覧、ノード・エッジ種別の説明、ヘルスチェック。

## LLM とガードレール
- LLM（vLLM + Qwen）は intent の種類と起点・終点の抽出、説明文だけを担当する。Cypher は `cypher_builder` がテンプレートから組み立てる
- 実行前に `cypher_guard` が書き込み・CALL・LOAD・複数文・許可外ラベル/エッジ・深さ上限超過を拒否し、READ access mode のセッションで実行する
- LLM が使えない・不正な出力のときはルールベースの解析に切り替わる
