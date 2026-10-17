"""Security ontology: the single source of truth for node and edge types."""

from enum import StrEnum


class NodeType(StrEnum):
    ASSET = "Asset"
    IDENTITY = "Identity"
    PERMISSION = "Permission"
    VULNERABILITY = "Vulnerability"
    SECRET = "Secret"
    DATA = "Data"
    NETWORK_ZONE = "NetworkZone"
    ATTACK_TECHNIQUE = "AttackTechnique"


class EdgeType(StrEnum):
    EXPOSED_TO = "EXPOSED_TO"
    HOSTS = "HOSTS"
    HAS_VULNERABILITY = "HAS_VULNERABILITY"
    CAN_EXPLOIT = "CAN_EXPLOIT"
    CAN_ACCESS = "CAN_ACCESS"
    HAS_PERMISSION = "HAS_PERMISSION"
    USES_SECRET = "USES_SECRET"
    LEADS_TO = "LEADS_TO"
    CAN_REACH = "CAN_REACH"
    PROTECTS = "PROTECTS"
    STORES = "STORES"


NODE_DESCRIPTIONS: dict[NodeType, str] = {
    NodeType.ASSET: "サーバ、アプリ、クラウド資産など",
    NodeType.IDENTITY: "ユーザー、サービスアカウント、IAM ロール",
    NodeType.PERMISSION: "権限",
    NodeType.VULNERABILITY: "脆弱性、設定不備",
    NodeType.SECRET: "認証情報、鍵、トークン",
    NodeType.DATA: "守るべきデータ",
    NodeType.NETWORK_ZONE: "ネットワーク境界",
    NodeType.ATTACK_TECHNIQUE: "攻撃手法",
}

EDGE_DESCRIPTIONS: dict[EdgeType, str] = {
    EdgeType.EXPOSED_TO: "資産が外部公開されている",
    EdgeType.HOSTS: "資産が別の資産やコンポーネントを保持",
    EdgeType.HAS_VULNERABILITY: "資産が脆弱性を持つ",
    EdgeType.CAN_EXPLOIT: "脆弱性が資産侵害につながる",
    EdgeType.CAN_ACCESS: "Identity が Asset / Data にアクセス可能",
    EdgeType.HAS_PERMISSION: "Identity が権限を持つ",
    EdgeType.USES_SECRET: "資産や Identity が Secret を使用",
    EdgeType.LEADS_TO: "ある侵害が次の侵害に進展する",
    EdgeType.CAN_REACH: "ネットワーク的に到達可能",
    EdgeType.PROTECTS: "資産がデータを保護/保持",
    EdgeType.STORES: "資産がデータを格納している",
}

# Edges an attacker can traverse when moving toward a target.
# HAS_PERMISSION / PROTECTS describe state rather than attacker movement.
ATTACK_EDGE_TYPES: tuple[EdgeType, ...] = (
    EdgeType.EXPOSED_TO,
    EdgeType.HOSTS,
    EdgeType.HAS_VULNERABILITY,
    EdgeType.CAN_EXPLOIT,
    EdgeType.CAN_ACCESS,
    EdgeType.USES_SECRET,
    EdgeType.LEADS_TO,
    EdgeType.CAN_REACH,
    EdgeType.STORES,
)

MAX_PATH_DEPTH = 10
