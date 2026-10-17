# Security Attack Graph 3D 設計書

## 1. 概要

**Security Attack Graph 3D** は、企業システム内の **資産・脆弱性・権限・シークレット・データ到達経路** を知識グラフとして表現し、  
**「どの脆弱性が危険か」ではなく「どの経路で顧客データまで到達できるか」** を可視化するデモ/プロトタイプである。

本デモでは以下を実現する。

- ダミー企業ネットワークを知識グラフとしてモデリング
- Neo4j 上にセキュリティ・オントロジーを定義
- Qwen を用いて自然言語クエリを Cypher / グラフ探索条件へ変換
- Attack Path を探索
- Three.js により 3D グラフとして可視化
- 最も危険な経路をハイライト表示
- Streamlit から操作可能な形でデモ化

---

## 2. 目的

### 2.1 目的

このデモの目的は、社内共有・顧客提案・将来のセキュリティ製品検討のために、以下の価値を短時間で伝えることである。

1. **脆弱性を点ではなく経路で捉える**
2. **情報漏洩リスクをグラフで説明可能にする**
3. **LLM + Graph + Visualization の組み合わせで意思決定を支援する**
4. **将来的な継続診断・ペンテスト・Attack Simulation 製品の原型とする**

### 2.2 伝えたいメッセージ

> 脆弱性一覧を見せるのではなく、  
> **「どこからどう侵入し、どの権限を奪い、最終的にどのデータへ到達するか」**  
> を可視化することで、経営・現場の両方に伝わるセキュリティ判断基盤を作る。

---

## 3. 想定ユースケース

### 3.1 基本ユースケース

ユーザーが以下のように質問する。

- 「顧客データに到達する最も危険な経路は？」
- 「Internet から侵入可能な経路だけ表示して」
- 「CVE-XXXX を起点にどの資産へ横展開できる？」
- 「S3 Bucket に到達するまでに必要な権限は？」
- 「Service Account が漏洩した場合の影響範囲は？」

### 3.2 デモシナリオ

以下のようなダミー企業構成を用意する。

```text
Internet
   ↓
Web Server
   │
   ├── CVE-XXXX
   │
   ▼
Application
   │
   ▼
Service Account
   │
   ▼
S3 Bucket
   │
   ▼
Customer Data
```

Attack Path の例:

```text
Internet
   ↓
CVE-XXXX
   ↓
Web Server
   ↓
Credential Leak
   ↓
Service Account
   ↓
S3 Bucket
   ↓
Customer Data
```

---

## 4. スコープ

### 4.1 対象範囲（MVP）

- ダミーデータを使った Attack Graph 構築
- Neo4j によるノード・エッジ管理
- Streamlit UI
- Qwen による自然言語 → 検索条件 / Cypher 変換
- Attack Path 探索
- Three.js による 3D グラフ表示
- 重要経路のハイライト
- ノード詳細パネル表示

### 4.2 対象外（初期版ではやらない）

- 実システムからの自動収集
- 本格的な脆弱性スキャナ連携
- リアルタイム脅威インテリジェンス統合
- 認証付きマルチユーザー機能
- 実際の Exploit 実行
- 本番運用レベルの継続監視

---

## 5. システム全体アーキテクチャ

```text
┌──────────────────────────────────────────┐
│                Streamlit UI               │
│  - 質問入力                               │
│  - シナリオ選択                           │
│  - リスク表示                             │
│  - 結果説明                               │
└──────────────────────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────┐
│              Backend (FastAPI)            │
│  - Query API                              │
│  - Graph Search API                       │
│  - Ontology API                           │
│  - Visualization API                      │
└──────────────────────────────────────────┘
         │                    │
         │                    │
         ▼                    ▼
┌────────────────┐   ┌──────────────────────┐
│ vLLM + Qwen     │   │ Attack Path Engine    │
│ - NL→Cypher     │   │ - path search         │
│ - NL→intent     │   │ - risk scoring        │
│ - result explain│   │ - path ranking        │
└────────────────┘   └──────────────────────┘
                                 │
                                 ▼
                      ┌──────────────────────┐
                      │ Neo4j Graph Database │
                      │ - ontology           │
                      │ - assets             │
                      │ - vulnerabilities    │
                      │ - identities         │
                      │ - permissions        │
                      │ - data paths         │
                      └──────────────────────┘
                                 │
                                 ▼
                      ┌──────────────────────┐
                      │ Three.js Graph View  │
                      │ - 3D nodes/edges     │
                      │ - path highlight     │
                      │ - node interaction   │
                      └──────────────────────┘
```

---

## 6. 技術スタック

### 6.1 フロントエンド

- **Streamlit**
  - デモ操作 UI
  - 入力フォーム
  - 結果表示
  - メトリクス表示
- **Three.js**
  - 3D グラフ描画
  - ノード/エッジのインタラクション
  - 攻撃経路の強調表示

### 6.2 バックエンド

- **FastAPI**
  - API 提供
  - Streamlit との連携
  - Graph Search 呼び出し
  - LLM 呼び出し統合

### 6.3 グラフデータベース

- **Neo4j**
  - Attack Graph 格納
  - Cypher による探索
  - Graph visualization 用データ提供

### 6.4 LLM

- **Qwen (小型モデル)**
  - 自然言語 → Cypher
  - 自然言語 → 検索意図
  - 結果説明文生成
- **vLLM**
  - ローカル推論サーバ
  - A1000 8GB で動かしやすい小型モデルを採用

### 6.5 Python ライブラリ候補

- `neo4j`
- `fastapi`
- `uvicorn`
- `streamlit`
- `pydantic`
- `networkx`（補助的なパス探索）
- `orjson`
- `jinja2`
- `httpx`

---

## 7. オントロジー設計

### 7.1 ノード種別

以下のオントロジーを定義する。

| ノード種別             | 説明                     | 例                                  |
| ----------------- | ---------------------- | ---------------------------------- |
| `Asset`           | サーバ、アプリ、クラウド資産など       | Web Server, API, S3 Bucket         |
| `Identity`        | ユーザー、サービスアカウント、IAM ロール | service-account-prod               |
| `Permission`      | 権限                     | s3:GetObject, AssumeRole           |
| `Vulnerability`   | 脆弱性、設定不備               | CVE-XXXX, Public Bucket            |
| `Secret`          | 認証情報、鍵、トークン            | API Key, Access Token              |
| `Data`            | 守るべきデータ                | Customer Data                      |
| `NetworkZone`     | ネットワーク境界               | Internet, DMZ, Internal            |
| `AttackTechnique` | 攻撃手法                   | Credential Theft, Lateral Movement |

### 7.2 エッジ種別

| エッジ                 | 説明                              |
| ------------------- | ------------------------------- |
| `EXPOSED_TO`        | 資産が外部公開されている                    |
| `HOSTS`             | 資産が別の資産やコンポーネントを保持              |
| `HAS_VULNERABILITY` | 資産が脆弱性を持つ                       |
| `CAN_EXPLOIT`       | 脆弱性が資産侵害につながる                   |
| `CAN_ACCESS`        | Identity が Asset / Data にアクセス可能 |
| `HAS_PERMISSION`    | Identity が権限を持つ                 |
| `USES_SECRET`       | 資産や Identity が Secret を使用       |
| `LEADS_TO`          | ある侵害が次の侵害に進展する                  |
| `CAN_REACH`         | ネットワーク的に到達可能                    |
| `PROTECTS`          | 資産がデータを保護/保持                    |
| `STORES`            | 資産がデータを格納している                   |

### 7.3 代表的なモデル

```text
(NetworkZone:Internet)
   └─ EXPOSED_TO → (Asset:WebServer)

(Asset:WebServer)
   └─ HAS_VULNERABILITY → (Vulnerability:CVE-XXXX)

(Vulnerability:CVE-XXXX)
   └─ LEADS_TO → (Secret:WebCredential)

(Secret:WebCredential)
   └─ LEADS_TO → (Identity:ServiceAccount)

(Identity:ServiceAccount)
   └─ HAS_PERMISSION → (Permission:s3:GetObject)

(Identity:ServiceAccount)
   └─ CAN_ACCESS → (Asset:S3Bucket)

(Asset:S3Bucket)
   └─ STORES → (Data:CustomerData)
```

---

## 8. グラフスキーマ例

### 8.1 Node 属性例

### Asset

```json
{
  "id": "asset_web_01",
  "label": "Web Server",
  "type": "Asset",
  "category": "Compute",
  "criticality": 4,
  "environment": "prod"
}
```

### Vulnerability

```json
{
  "id": "vuln_cve_xxxx",
  "label": "CVE-XXXX",
  "type": "Vulnerability",
  "severity": 9.1,
  "exploitability": 0.9,
  "description": "Remote Code Execution"
}
```

### Identity

```json
{
  "id": "id_svc_01",
  "label": "service-account-prod",
  "type": "Identity",
  "identity_type": "ServiceAccount",
  "criticality": 5
}
```

### Data

```json
{
  "id": "data_customer_01",
  "label": "Customer Data",
  "type": "Data",
  "sensitivity": "high",
  "confidentiality_impact": 5
}
```

### 8.2 Edge 属性例

```json
{
  "source": "asset_web_01",
  "target": "vuln_cve_xxxx",
  "type": "HAS_VULNERABILITY",
  "weight": 1.0
}
```

---

## 9. 攻撃経路探索ロジック

### 9.1 基本方針

「危険な経路」は単なる最短経路ではなく、以下の要素を加味してスコアリングする。

- 脆弱性 severity
- exploitability
- 資産 criticality
- 権限の強さ
- データ感度
- 経路長
- 攻撃成功の容易性

### 9.2 リスクスコアの考え方

各ノード・エッジに重みを持たせ、経路全体のスコアを計算する。

### 例

```text
Path Risk Score =
  Σ(Vulnerability Severity × Exploitability)
+ Σ(Identity Privilege Weight)
+ Σ(Data Sensitivity Weight)
+ Σ(Asset Criticality)
- Path Length Penalty
```

### 例の重み

- Vulnerability Severity: 1〜10
- Exploitability: 0.0〜1.0
- Asset Criticality: 1〜5
- Data Sensitivity: 1〜5
- Identity Privilege Weight: 1〜5

### 9.3 探索方式

初期版は以下で十分。

1. **Cypher の variable length path**
2. **重み付き経路スコアリング**
3. **上位 N 件を返す**

将来的には：

- Dijkstra / A\*
- k-shortest paths
- graph algorithm library
- attack simulation engine

### 9.4 Cypher のイメージ

```cypher
MATCH p = (start:NetworkZone {label: "Internet"})-[*1..8]->(target:Data {label: "Customer Data"})
RETURN p
LIMIT 20
```

さらに経路に含めるエッジ種別を制限する。

```cypher
MATCH p = (start:NetworkZone {label: "Internet"})
  -[:EXPOSED_TO|HAS_VULNERABILITY|LEADS_TO|CAN_ACCESS|STORES*1..8]->
  (target:Data {label: "Customer Data"})
RETURN p
LIMIT 20
```

---

## 10. LLM 利用設計

### 10.1 LLM の役割

Qwen の役割は以下。

1. 自然言語クエリの意図解釈
2. 意図に応じた Cypher 生成
3. 結果の要約・説明
4. 表示用の解説文生成

### 10.2 入出力

### 入力例

```text
顧客データに到達する最も危険な経路は？
```

### LLM 中間出力例

```json
{
  "intent": "find_highest_risk_path",
  "source": "Internet",
  "target": "Customer Data",
  "max_depth": 8,
  "path_types": [
    "EXPOSED_TO",
    "HAS_VULNERABILITY",
    "LEADS_TO",
    "CAN_ACCESS",
    "STORES"
  ]
}
```

### Cypher 生成例

```cypher
MATCH p = (start:NetworkZone {label: "Internet"})
  -[:EXPOSED_TO|HAS_VULNERABILITY|LEADS_TO|CAN_ACCESS|STORES*1..8]->
  (target:Data {label: "Customer Data"})
RETURN p
LIMIT 50
```

### 説明文生成例

```text
最も危険な経路は、
Internet から公開された Web Server を経由し、
CVE-XXXX の悪用で Web Server を侵害、
漏洩した認証情報により Service Account を取得し、
その権限で S3 Bucket にアクセスして Customer Data に到達する経路です。
```

### 10.3 ガードレール

初期版では、LLM が自由に Cypher を生成しすぎないように以下を入れる。

- 許可するラベルとエッジ種別を固定
- 読み取り専用 Cypher のみ許可
- システムプロンプトで DDL/DML 禁止
- 最大探索深さを制限
- 出力は structured JSON で受ける

---

## 11. UI 設計

### 11.1 画面構成

```text
┌─────────────────────────────────────────────────────┐
│ Security Attack Graph 3D                            │
├────────────────────┬────────────────────────────────┤
│ Left Panel         │ Main Panel                     │
│                    │                                │
│ - Scenario select  │ 3D Attack Graph (Three.js)     │
│ - Query input      │                                │
│ - Run button       │                                │
│ - Filters          │                                │
│                    │                                │
├────────────────────┴────────────────────────────────┤
│ Result Summary                                      │
│ - Top Risk Path                                     │
│ - Score                                              │
│ - Explanation                                        │
├─────────────────────────────────────────────────────┤
│ Detail Panel                                        │
│ - Selected Node detail                              │
│ - Node type / severity / permissions / data impact  │
└─────────────────────────────────────────────────────┘
```

### 11.2 Streamlit 構成

- サイドバー
  - シナリオ選択
  - クエリ例ボタン
  - リスクしきい値
  - 最大深さ
- メイン
  - 質問入力欄
  - 実行ボタン
  - 3D ビュー埋め込み
  - 結果サマリ
- 下部
  - 経路一覧
  - ノード詳細
  - Cypher 表示（デバッグ用）

### 11.3 Three.js 表現

### ノード色

- Asset: 青
- Vulnerability: 赤
- Identity: 紫
- Permission: 黄
- Secret: オレンジ
- Data: 緑
- NetworkZone: 灰

### ノード形状

- Asset: sphere
- Vulnerability: octahedron
- Identity: cube
- Secret: tetrahedron
- Data: glowing sphere

### エッジ表現

- 通常エッジ: 薄い線
- Attack Path: 太い赤線
- Hover 時: 強調表示
- 選択時: 周辺ノードを明るく表示

---

## 12. API 設計

### 12.1 `POST /query`

自然言語クエリを受け取り、Attack Path を返す。

### Request

```json
{
  "question": "顧客データに到達する最も危険な経路は？",
  "scenario": "demo_company_a"
}
```

### Response

```json
{
  "intent": "find_highest_risk_path",
  "cypher": "MATCH ...",
  "paths": [
    {
      "score": 24.5,
      "nodes": [
        {"id": "internet", "label": "Internet", "type": "NetworkZone"},
        {"id": "web", "label": "Web Server", "type": "Asset"},
        {"id": "cve", "label": "CVE-XXXX", "type": "Vulnerability"},
        {"id": "secret", "label": "Credential Leak", "type": "Secret"},
        {"id": "iam", "label": "Service Account", "type": "Identity"},
        {"id": "s3", "label": "S3 Bucket", "type": "Asset"},
        {"id": "data", "label": "Customer Data", "type": "Data"}
      ],
      "edges": [
        {"source": "internet", "target": "web", "type": "EXPOSED_TO"},
        {"source": "web", "target": "cve", "type": "HAS_VULNERABILITY"},
        {"source": "cve", "target": "secret", "type": "LEADS_TO"},
        {"source": "secret", "target": "iam", "type": "LEADS_TO"},
        {"source": "iam", "target": "s3", "type": "CAN_ACCESS"},
        {"source": "s3", "target": "data", "type": "STORES"}
      ]
    }
  ],
  "summary": "最も危険な経路は ... "
}
```

### 12.2 `GET /graph/scenario/{scenario_id}`

シナリオ全体グラフを返す。

### 12.3 `GET /node/{node_id}`

選択ノード詳細を返す。

### 12.4 `POST /seed`

ダミーデータ投入。

---

## 13. データ投入設計

### 13.1 初期シナリオ

初期版では 3 シナリオ程度でよい。

### Scenario A: Web侵入→S3到達

- Internet
- Web Server
- CVE-XXXX
- Application
- Service Account
- S3 Bucket
- Customer Data

### Scenario B: API Key 漏洩

- GitHub Repo
- Secret
- CI/CD
- Cloud Role
- DB
- Customer Data

### Scenario C: 認可過剰

- Internal User
- Over-privileged Role
- Data Lake
- Sensitive Table

### 13.2 Seed データ形式

YAML/JSON で管理する。

```yaml
nodes:
  - id: internet
    type: NetworkZone
    label: Internet
  - id: web
    type: Asset
    label: Web Server
  - id: cve_x
    type: Vulnerability
    label: CVE-XXXX
    severity: 9.1
  - id: svc
    type: Identity
    label: Service Account
  - id: s3
    type: Asset
    label: S3 Bucket
  - id: data_customer
    type: Data
    label: Customer Data

edges:
  - source: internet
    target: web
    type: EXPOSED_TO
  - source: web
    target: cve_x
    type: HAS_VULNERABILITY
  - source: cve_x
    target: svc
    type: LEADS_TO
  - source: svc
    target: s3
    type: CAN_ACCESS
  - source: s3
    target: data_customer
    type: STORES
```

---

## 14. 主要機能一覧

| 機能             | 説明               | 優先度 |
| -------------- | ---------------- | --- |
| シナリオ選択         | ダミー企業構成を選択       | 高   |
| 自然言語質問         | LLM で意図解釈        | 高   |
| Cypher 生成      | 意図から Neo4j クエリ生成 | 高   |
| Attack Path 探索 | データ漏洩経路を探索       | 高   |
| リスクスコアリング      | 経路を比較して上位表示      | 高   |
| 3D 表示          | Three.jsで可視化     | 高   |
| 経路ハイライト        | 最も危険な経路を強調表示     | 高   |
| ノード詳細表示        | クリックで詳細を見る       | 中   |
| 説明文生成          | LLMで説明文出力        | 中   |
| フィルタリング        | severityやタイプで絞る  | 中   |
| 経路比較           | Top N経路を比較       | 中   |
| エクスポート         | PNG/JSON         | 低   |

---

## 15. 実装方針

### 15.1 MVP 開発順

### Step 1: Graph モデル作成

- Neo4j 起動
- ノード/エッジスキーマ整理
- Seed データ投入

### Step 2: Attack Path 探索

- 固定 Cypher で経路検索
- スコアリング関数実装
- Top 1 / Top 3 path 表示

### Step 3: Streamlit UI

- 質問入力
- 結果表示
- 経路一覧
- ノード詳細

### Step 4: Three.js 可視化

- グラフ表示
- path highlight
- ノードクリック

### Step 5: Qwen 統合

- 自然言語 → intent
- intent → Cypher
- 結果説明生成

### Step 6: デモ仕上げ

- シナリオ追加
- UI polish
- 説明文調整
- デモ台本整備

---

## 16. リポジトリ構成案

```text
security-attack-graph-3d/
├── README.md
├── docs/
│   ├── design.md
│   ├── ontology.md
│   ├── demo_script.md
│   └── api_spec.md
├── app/
│   ├── streamlit_app.py
│   ├── pages/
│   │   ├── 01_overview.py
│   │   ├── 02_graph_view.py
│   │   └── 03_path_analysis.py
│   ├── components/
│   │   ├── graph_viewer.py
│   │   ├── summary_panel.py
│   │   └── node_detail.py
│   └── static/
│       └── threejs/
├── backend/
│   ├── main.py
│   ├── api/
│   │   ├── query.py
│   │   ├── graph.py
│   │   └── seed.py
│   ├── services/
│   │   ├── llm_service.py
│   │   ├── graph_service.py
│   │   ├── path_service.py
│   │   └── scoring_service.py
│   ├── models/
│   │   ├── schemas.py
│   │   └── ontology.py
│   └── prompts/
│       ├── intent_prompt.txt
│       ├── cypher_prompt.txt
│       └── summary_prompt.txt
├── data/
│   ├── seed/
│   │   ├── scenario_a.yaml
│   │   ├── scenario_b.yaml
│   │   └── scenario_c.yaml
│   └── samples/
├── scripts/
│   ├── seed_neo4j.py
│   ├── run_vllm.sh
│   ├── run_backend.sh
│   └── run_streamlit.sh
├── docker/
│   ├── docker-compose.yml
│   └── neo4j/
├── tests/
│   ├── test_graph_service.py
│   ├── test_path_service.py
│   ├── test_scoring_service.py
│   └── test_api.py
└── pyproject.toml
```

---

## 17. 開発環境

### 17.1 ローカル環境

- Ubuntu / macOS
- Python 3.11+
- uv
- Docker / Docker Compose
- Neo4j
- vLLM
- CUDA環境（A1000）

### 17.2 サービス起動

- Neo4j
- vLLM server
- FastAPI backend
- Streamlit frontend

---

## 18. 非機能要件

### 18.1 パフォーマンス

- デモでは 1,000 ノード未満を目安
- クエリ応答 3〜10 秒程度以内を目標
- 3D 表示は滑らかさを優先し、ノード数が増えたら集約表示を検討

### 18.2 可用性

- デモ用途なので単一ノードで可
- 本番想定では API と DB 分離

### 18.3 セキュリティ

- LLM に破壊系 Cypher を出させない
- Neo4j 読み取り専用ユーザー
- 入力検証
- 表示データはダミー限定

### 18.4 保守性

- オントロジー定義を YAML / Python クラスで一元管理
- Prompt を分離
- シナリオデータを差し替え可能にする

---

## 19. デモ実施シナリオ

### 19.1 デモの流れ（3〜5分）

### 1. 背景説明

- 脆弱性一覧だけでは優先順位が分からない
- 情報漏洩までの経路が重要

### 2. シナリオ読み込み

- Web Server
- CVE
- Service Account
- S3 Bucket
- Customer Data

### 3. 質問入力

```text
顧客データに到達する最も危険な経路は？
```

### 4. グラフ表示

- Three.js で全体グラフ表示
- Attack Path を赤く強調

### 5. 説明

- Internet → Web Server → CVE → Credential → IAM → S3 → Customer Data

### 6. 価値訴求

- 脆弱性一覧でなく攻撃経路で判断できる
- 対策優先順位が明確になる

### 19.2 見せ場

- 経路ハイライト
- ノードクリックで詳細表示
- LLM による自然言語質問
- 説明文の自動生成

---

## 20. 将来拡張

### 20.1 近い拡張

- CVSS / EPSS を使ったスコアリング
- IAM 権限の詳細分析
- 経路ごとの対策提案
- 複数経路の比較
- Graphiti の時系列イベント投入
- ペンテスト結果の証跡連携

### 20.2 中長期拡張

- クラウド構成自動取り込み
- CI/CD セキュリティイベントの取り込み
- 攻撃シミュレーション
- セキュリティ知識グラフ製品化
- 経営向けリスクダッシュボード
- 因果/シミュレーション連携
- Enterprise OS の意思決定基盤との統合

---

## 21. 成功条件

このデモが成功したと言える条件は以下。

1. **「危険な脆弱性」ではなく「危険な経路」という考え方が伝わる**
2. **自然言語で質問し、Attack Path が返る体験ができる**
3. **Three.js による可視化で、直感的に分かる**
4. **将来のプロダクト化の方向性が見える**
5. **Algomatic のセキュリティ/AI Agent/Graph の強みと接続できる**

---

## 22. まとめ

Security Attack Graph 3D は、  
**資産・脆弱性・権限・シークレット・データをグラフで統合し、**  
**「情報漏洩に至る経路」を可視化するセキュリティデモ**である。

このデモの価値は、単に Neo4j や Qwen や Three.js を使うことではなく、

- **脆弱性一覧を経路の文脈に変換すること**
- **セキュリティ判断を説明可能にすること**
- **Graph + LLM + Visualization の製品可能性を示すこと**

にある。

---
