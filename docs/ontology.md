# オントロジー

定義の正本は `backend/models/ontology.py`（Enum）。ここは説明用。

## ノード種別

| 種別 | 説明 | 主な属性（スコアで使うもの） | 3D 表現 |
|---|---|---|---|
| `Asset` | サーバ、アプリ、クラウド資産 | `criticality` 1〜5 | 青 / sphere |
| `Identity` | ユーザー、サービスアカウント、IAM ロール | `privilege` 1〜5 | 紫 / cube |
| `Permission` | 権限 | `privilege`（表示のみ） | 黄 / cylinder |
| `Vulnerability` | 脆弱性、設定不備 | `severity` 0〜10, `exploitability` 0〜1 | 赤 / octahedron |
| `Secret` | 認証情報、鍵、トークン | — | オレンジ / tetrahedron |
| `Data` | 守るべきデータ | `confidentiality_impact` 1〜5 | 緑 / 発光 sphere |
| `NetworkZone` | ネットワーク境界 | — | 灰 / torus |
| `AttackTechnique` | 攻撃手法（MITRE ATT&CK） | `mitre_id` | ピンク / cone |

## エッジ種別

| エッジ | 説明 | 攻撃経路として辿る |
|---|---|---|
| `EXPOSED_TO` | 資産が外部公開されている | ✓ |
| `HOSTS` | 資産が別の資産を保持 | ✓ |
| `HAS_VULNERABILITY` | 資産が脆弱性を持つ | ✓ |
| `CAN_EXPLOIT` | 脆弱性が資産侵害につながる | ✓ |
| `CAN_ACCESS` | Identity が Asset / Data にアクセス可能 | ✓ |
| `HAS_PERMISSION` | Identity が権限を持つ | — （状態。「必要な権限」の回答に使う） |
| `USES_SECRET` | 資産や Identity が Secret を使用 | ✓ |
| `LEADS_TO` | ある侵害が次の侵害に進展 | ✓ |
| `CAN_REACH` | ネットワーク的に到達可能 | ✓ |
| `PROTECTS` | 資産がデータを保護 | — |
| `STORES` | 資産がデータを格納 | ✓ |

エッジ属性 `weight`（既定 1.0）はそのステップの成功しやすさ。経路スコアに積で掛かる。

## リスクスコア

```
score = ( Σ(severity × exploitability)      # Vulnerability
        + max(privilege)                     # Identity
        + max(confidentiality_impact)        # Data
        + max(criticality) )                 # Asset
        × Π(edge weight)
        − 1.0 × (#edges)
```

設計書 §9.2 は全項目 Σ だが、影響度を Σ にすると迂回経路ほど高スコアになるため max にしている（Issue #4）。

## シナリオデータ

`data/seed/*.yaml`。ノード ID はシナリオ間で一意にする（`a_`, `b_`, `c_` 接頭辞）。

```yaml
scenario:
  id: demo_company_a
  name: "Scenario A: Web侵入→S3到達"
  default_source: Internet        # 質問で起点が分からないときの既定
  default_target: Customer Data   # 同・終点
nodes:
  - {id: a_cve, type: Vulnerability, label: CVE-XXXX, severity: 9.1, exploitability: 0.9}
edges:
  - {source: a_web, target: a_cve, type: HAS_VULNERABILITY}
```
