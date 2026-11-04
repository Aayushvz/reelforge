"""Character roster for the stylized-sculpt cast (data only). Colours are linear RGB.

Head-space units: the head is ~2.2 units tall (chin -1.05 .. crown 1.15), face toward -Y.
Every number here is a dial; build_character.py turns them into a mesh + face rig.
All seven are original characters; the style references only set the look, never a likeness."""

BASE = {
    "head_scale": 0.138,        # metres per head unit
    "face_length": 1.12,        # z stretch of the skull
    "head_width": 0.70,
    "jaw_width": 0.80,          # 0 = pointy chin, 1 = no taper
    "jaw_corner": 0.10,         # outward bump at the jaw angle
    "chin": 0.17,               # chin projection
    "cheekbone": 0.10,
    "nose_length": 1.0,
    "nose_tip": 0.15,
    "nose_width": 1.0,
    "brow_ridge": 0.11,         # how far the brow shelf juts out
    "socket": 0.15,             # eye-socket depth
    "planes": 0.03,             # crease depth of the cheek/jaw plane breaks
    "mouth_width": 0.28,        # half-width on the unit sphere
    "smile_rest": 0.12,         # smile baked into the neutral mouth
    "hollow": 0.07,             # cheek hollow under the cheekbone
    "fold": 0.03,               # nasolabial fold depth
    "lip_full": 1.0,
    "eye_spacing": 0.30,
    "eye_size": 0.17,
    "eye_wide": 1.18,           # almond stretch of eye + lids
    "eye_tall": 0.92,
    "lid_rest": -0.42,          # upper-lid rotation at rest (rad); closer to 0 = sleepier
    "lashes": False,
    "neck_length": 0.075,       # metres of visible neck
    "neck_radius": 0.04,
    "torso_w": 0.205,
    "skin": (0.50, 0.25, 0.15),
    "lip": (0.40, 0.13, 0.10),
    "iris": (0.06, 0.025, 0.01),
    "brow_color": (0.012, 0.009, 0.008),
    "brow_thick": 1.0,
    "brow_angle": 0.08,
    "stubble": 0.0,
    "beard": 0.0,
    "freckles": 0.0,
    "blush": 0.0,
    "hair": "curls",            # curls | swoop | messy | long | bob | ponytail
    "curl_scale": 1.0,
    "hair_color": (0.012, 0.010, 0.010),
    "top_type": "shirt",        # shirt | tee | hoodie | turtle | zip
    "top": (0.018, 0.018, 0.02),
    "accent": (0.8, 0.8, 0.8),  # drawstrings, zipper, scrunchie
    "metal": "silver",
    "earring": None,            # None | hoop_left | hoops | studs
    "chain": None,              # None | thin | chunky
    "watch": False,
    "glasses": None,            # None | round | rect
    "frame_color": (0.01, 0.01, 0.012),
    "outer": None,              # blazer | cardigan | varsity | puffer | puffer_vest | trench | techwear | track | flannel | vest
    "outer_color": (0.1, 0.1, 0.1),
    "outer_accent": (0.8, 0.8, 0.8),
    "print": None,              # chest print colour (graphic tee)
    "print_shape": None,        # None | butterfly
    "hat": None,                # None | beanie | cap | beret
    "hat_color": (0.1, 0.1, 0.1),
    "hair_volume": 0.15,        # how far hair stands off the skull (hats sit on top of it)
}

# Wardrobe: each outfit overrides the dials above. Outfit 0 is the character's base look.
O = {
    "boxy_shirt": {"top_type": "shirt"},
    "oversized_hoodie": {"top_type": "hoodie", "torso_w": 0.225},
    "knit_vest": {"top_type": "tee", "top": (0.8, 0.78, 0.72), "outer": "vest", "outer_color": (0.25, 0.14, 0.06)},
    "track_jacket": {"top_type": "tee", "top": (0.8, 0.8, 0.8), "outer": "track", "outer_color": (0.02, 0.04, 0.15),
                     "accent": (0.9, 0.9, 0.9)},
    "puffer_vest": {"top_type": "hoodie", "outer": "puffer_vest", "outer_color": (0.015, 0.015, 0.018)},
    "techwear": {"top_type": "tee", "top": (0.02, 0.02, 0.02), "outer": "techwear", "outer_color": (0.03, 0.035, 0.03),
                 "outer_accent": (0.4, 0.42, 0.1)},
    "varsity": {"top_type": "tee", "top": (0.85, 0.85, 0.82), "outer": "varsity", "outer_color": (0.02, 0.05, 0.2),
                "outer_accent": (0.8, 0.75, 0.6), "accent": (0.9, 0.9, 0.9)},
    "cardigan": {"top_type": "tee", "outer": "cardigan", "outer_color": (0.22, 0.13, 0.06), "accent": (0.6, 0.5, 0.35)},
    "graphic_beanie": {"top_type": "tee", "top": (0.02, 0.06, 0.1), "print": (0.9, 0.5, 0.1), "hat": "beanie",
                       "hat_color": (0.4, 0.05, 0.03)},
    "flannel_hoodie": {"top_type": "hoodie", "top": (0.2, 0.2, 0.21), "outer": "flannel",
                       "outer_color": (0.4, 0.03, 0.03), "outer_accent": (0.03, 0.02, 0.02)},
    "blazer": {"top_type": "tee", "top": (0.015, 0.015, 0.017), "outer": "blazer", "outer_color": (0.2, 0.19, 0.18)},
    "baby_tee": {"top_type": "tee", "top": (0.7, 0.35, 0.45), "torso_w": 0.16},
    "butterfly_top": {"top_type": "tee", "top": (0.45, 0.35, 0.7), "print": (0.45, 0.35, 0.7),
                      "print_shape": "butterfly", "accent": (0.1, 0.5, 0.9)},
    "puffer_jacket": {"top_type": "zip", "outer": "puffer", "outer_color": (0.85, 0.82, 0.75)},
    "trench_turtle": {"top_type": "turtle", "outer": "trench", "outer_color": (0.45, 0.3, 0.15)},
    "cargo_set": {"top_type": "zip", "top": (0.12, 0.13, 0.06), "accent": (0.3, 0.3, 0.25)},
    "sweater_beret": {"top_type": "turtle", "top": (0.75, 0.68, 0.55), "torso_w": 0.19, "hat": "beret",
                      "hat_color": (0.35, 0.03, 0.04)},
}

FEM = {"jaw_width": 0.64, "jaw_corner": 0.02, "chin": 0.09, "cheekbone": 0.12, "nose_length": 0.85,
       "nose_tip": 0.11, "lip_full": 1.3, "mouth_width": 0.26, "hollow": 0.025, "fold": 0.01, "eye_size": 0.18, "lashes": True,
       "brow_thick": 0.8, "brow_angle": 0.02, "neck_radius": 0.031, "torso_w": 0.17, "lip": (0.36, 0.08, 0.08)}

CAST = {
    # M1 chill creative, deadpan: tight black curls, thin chain, earring, boxy black shirt
    "kai": {**BASE, "hair_volume": 0.35, "smile_rest": 0.04, "stubble": 0.7, "eye_size": 0.175, "brow_thick": 1.25, "brow_angle": 0.05,
            "earring": "hoop_left", "chain": "thin",
        "outfits": [{}, O["oversized_hoodie"] | {"top": (0.12, 0.13, 0.08)}, O["knit_vest"]]},
    # M2 loud and funny: big curls, full beard, glasses, grey sweatsuit, chunky chain
    "rey": {**BASE, "hair_volume": 0.45, "smile_rest": 0.3, "face_length": 1.0, "head_width": 0.78, "jaw_width": 0.86, "cheekbone": 0.06, "nose_tip": 0.19,
            "lid_rest": -0.5, "brow_thick": 1.3, "brow_angle": -0.02, "skin": (0.36, 0.17, 0.09), "stubble": 0.6,
            "beard": 1.0, "curl_scale": 1.3, "hair_color": (0.02, 0.012, 0.008), "glasses": "rect",
            "top_type": "hoodie", "top": (0.2, 0.2, 0.21), "accent": (0.9, 0.9, 0.9), "chain": "chunky",
            "metal": "gold",
        "face_length": 0.95, "head_width": 0.84, "jaw_width": 0.92, "nose_length": 0.9, "nose_tip": 0.24, "eye_size": 0.16, 
        "nose_width": 1.45, "brow_ridge": 0.12, "outfits": [{}, O["track_jacket"], O["puffer_vest"]]},
    # M3 confident coder, smirk: fade with swoop top, stubble, watch, camel tee
    "dev": {**BASE, "hair_volume": 0.25, "smile_rest": 0.2, "face_length": 1.1, "jaw_width": 0.84, "jaw_corner": 0.13, "chin": 0.2, "stubble": 0.5,
            "brow_angle": 0.1, "skin": (0.42, 0.21, 0.11), "hair": "swoop", "hair_color": (0.02, 0.012, 0.008),
            "top_type": "tee", "top": (0.36, 0.2, 0.09), "watch": True,
        "face_length": 1.2, "head_width": 0.67, "jaw_width": 0.9, "jaw_corner": 0.16, "chin": 0.24, 
        "nose_width": 0.9, "brow_ridge": 0.15, "socket": 0.18, "outfits": [{}, O["techwear"], O["varsity"]]},
    # M4 anxious overthinker: messy hair, round glasses, beige tee, lanky
    "mo": {**BASE, "hair_volume": 0.3, "face_length": 1.16, "head_width": 0.68, "jaw_width": 0.66, "chin": 0.08, "nose_length": 1.1,
           "nose_tip": 0.18, "lid_rest": -0.6, "brow_angle": -0.15, "skin": (0.62, 0.38, 0.27),
           "hair": "messy", "hair_color": (0.07, 0.035, 0.015), "brow_color": (0.05, 0.025, 0.012),
           "glasses": "round", "frame_color": (0.12, 0.06, 0.02), "neck_length": 0.09,
           "top_type": "tee", "top": (0.38, 0.32, 0.22),
        "face_length": 1.24, "head_width": 0.63, "jaw_width": 0.58, "nose_length": 1.25, "nose_tip": 0.22, "eye_size": 0.19, "lid_rest": -0.66, 
        "brow_ridge": 0.07, "socket": 0.12, "outfits": [O["cardigan"], O["graphic_beanie"], O["flannel_hoodie"]]},
    # F1 witty lead, sarcastic: long dark hair, gold hoops, cream cropped knit
    "aria": {**BASE, **FEM, "face_length": 1.08, "lid_rest": -0.38, "skin": (0.46, 0.25, 0.14),
             "hair": "long", "hair_color": (0.01, 0.008, 0.008), "earring": "hoops", "metal": "gold",
             "top_type": "tee", "top": (0.6, 0.52, 0.4),
        "face_length": 1.06, "jaw_width": 0.54, "cheekbone": 0.15, "chin": 0.11, 
        "nose_width": 0.85, "brow_ridge": 0.08, "outfits": [{}, O["blazer"], O["baby_tee"]]},
    # F2 bubbly, dramatic: high ponytail, freckles, blush, sporty pink zip-up
    "zoe": {**BASE, **FEM, "smile_rest": 0.2, "face_length": 1.02, "head_width": 0.72, "eye_size": 0.19, "lid_rest": -0.58,
            "skin": (0.66, 0.42, 0.3), "freckles": 0.9, "blush": 0.9, "hair": "ponytail",
            "hair_color": (0.16, 0.045, 0.015), "brow_color": (0.1, 0.035, 0.015), "iris": (0.03, 0.05, 0.02),
            "top_type": "zip", "top": (0.6, 0.15, 0.25), "accent": (0.95, 0.95, 0.95),
        "face_length": 0.96, "head_width": 0.76, "jaw_width": 0.6, "chin": 0.05, "eye_size": 0.2, "nose_length": 0.7, "nose_tip": 0.1, 
        "nose_width": 0.9, "brow_ridge": 0.05, "socket": 0.1, "outfits": [{}, O["butterfly_top"], O["puffer_jacket"]]},
    # F3 calm, stylish, dry humour: sleek bob, gold jewellery, black turtleneck
    "noor": {**BASE, **FEM, "face_length": 1.1, "jaw_width": 0.68, "cheekbone": 0.15, "nose_length": 0.9,
             "lip_full": 1.2, "eye_size": 0.17, "lid_rest": -0.45, "skin": (0.3, 0.15, 0.08), "hair": "bob",
             "hair_color": (0.008, 0.006, 0.006), "brow_thick": 0.9, "earring": "studs", "chain": "thin",
             "metal": "gold", "top_type": "turtle", "top": (0.015, 0.015, 0.017),
        "face_length": 1.15, "head_width": 0.65, "cheekbone": 0.18, "jaw_width": 0.66, 
        "brow_ridge": 0.09, "outfits": [O["trench_turtle"], O["cargo_set"], O["sweater_beret"]]},
}
