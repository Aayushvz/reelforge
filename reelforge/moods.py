"""Light + screen colors per mood. Linear RGB. Energies in watts (Blender area/point lights)."""
MOOD_PRESETS: dict[str, dict] = {
    "calm":    {"key": [1.0, 0.62, 0.35], "key_w": 180, "rim": [0.25, 0.45, 1.0], "rim_w": 220,
                "glow": [1.0, 0.55, 0.2], "glow_w": 60, "screen": [0.35, 0.6, 1.0]},
    "success": {"key": [0.75, 1.0, 0.6], "key_w": 170, "rim": [0.2, 1.0, 0.45], "rim_w": 260,
                "glow": [0.3, 1.0, 0.4], "glow_w": 120, "screen": [0.3, 1.0, 0.5]},
    "panic":   {"key": [1.0, 0.35, 0.25], "key_w": 200, "rim": [1.0, 0.1, 0.08], "rim_w": 300,
                "glow": [1.0, 0.15, 0.1], "glow_w": 150, "screen": [1.0, 0.2, 0.15]},
    "awkward": {"key": [0.85, 0.8, 0.75], "key_w": 120, "rim": [0.5, 0.55, 0.6], "rim_w": 120,
                "glow": [0.6, 0.6, 0.6], "glow_w": 30, "screen": [0.7, 0.75, 0.8]},
    "reveal":  {"key": [1.0, 0.8, 0.4], "key_w": 260, "rim": [1.0, 0.7, 0.3], "rim_w": 260,
                "glow": [1.0, 0.75, 0.3], "glow_w": 200, "screen": [1.0, 0.85, 0.4]},
    "sad":     {"key": [0.55, 0.65, 1.0], "key_w": 110, "rim": [0.2, 0.3, 0.9], "rim_w": 160,
                "glow": [0.3, 0.4, 1.0], "glow_w": 40, "screen": [0.4, 0.5, 0.9]},
}
