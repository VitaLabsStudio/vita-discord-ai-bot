from typing import List, Dict, Any

def tag_permissions(metadata: Dict[str, Any], allowed_roles: List[str], allowed_channels: List[str]) -> Dict[str, Any]:
    """Tag metadata with allowed roles and channels."""
    metadata["allowed_roles"] = allowed_roles
    metadata["allowed_channels"] = allowed_channels
    return metadata

def filter_by_permissions(chunks: List[Dict[str, Any]], user_roles: List[str], channel_id: str) -> List[Dict[str, Any]]:
    """Filter chunks by user roles and channel access."""
    filtered = []
    for chunk in chunks:
        allowed_roles = set(chunk.get("allowed_roles", []))
        allowed_channels = set(chunk.get("allowed_channels", []))
        if (not allowed_roles or set(user_roles) & allowed_roles) and (not allowed_channels or channel_id in allowed_channels):
            filtered.append(chunk)
    return filtered 