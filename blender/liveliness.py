"""A shading pass that makes the imported, realistic characters (Matt, Freya, Mina) read as alive, not as wax.

Shading only: no geometry, texture resolution or shape key is touched (CLAUDE.md: never reduce character quality).
Each material is classified by name, so the same pass works for the Character Creator rig (Matt: Std_Skin_*,
Std_Cornea_*, ...) and the two hand-built ones (Freya: Body, Eyes, Glass; Mina: body, eyes):
- skin: subsurface at a real-world scale (about 1 cm, red-heavy), softer specular, a little more colour (AgX mutes it)
- corneas: clear and glossy (a transparent shader plus a sharp reflection), so the eyes catch the light; before, an
  alpha-faded rough cornea also faded its own reflection, which is what made the eyes look dead
- eyeballs, teeth, tongue: wetter
- hair: its own colour kept (no sheen, highlights capped), a little richer
Idempotent: a material carries "enlivened" once done.

Run on a built file: blender -b <char.blend> -P blender/liveliness.py -- [--save]
"""
import sys

try:
    import bpy
except ImportError:  # read as data outside Blender
    bpy = None

SKIN = ("std_skin_", "skin", "body")  # Matt, generic, Freya ("Body") / Mina ("body")
NOT_SKIN = ("bodysuit", "nails")
CORNEA = ("cornea", "glass")
WET = ("teeth", "tongue", "mouth")
HAIR = ("hair", "scalp", "cap", "eyebrow", "eyelash")
SKIN_SSS = (0.6, 0.012, (1.0, 0.35, 0.2))  # weight, scale (m), radius
SKIN_SATURATION = 1.12


def kind(name: str) -> str:
    n = name.lower()
    if any(k in n for k in CORNEA):
        return "cornea"
    if "occlusion" in n or "tearline" in n:
        return "other"
    if n in ("eyes", "eye") or n.startswith("std_eye_"):  # not "eyebrows" / "eyelashes"
        return "eye"
    if any(k in n for k in WET):
        return "wet"
    if any(k in n for k in HAIR):
        return "hair"
    if any(n.startswith(k) or n == k for k in SKIN) and not any(k in n for k in NOT_SKIN):
        return "skin"
    return "other"


def _bsdf(m):
    return next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)


def _saturate(nt, b, amount):
    """Put a hue/saturation node between the base colour texture and the shader."""
    inp = b.inputs["Base Color"]
    if not inp.is_linked:
        return
    link = inp.links[0]
    hs = nt.nodes.new("ShaderNodeHueSaturation")
    hs.inputs["Saturation"].default_value = amount
    nt.links.new(link.from_socket, hs.inputs["Color"])
    nt.links.new(hs.outputs["Color"], inp)


def skin(m):
    nt, b = m.node_tree, _bsdf(m)
    w, s, r = SKIN_SSS
    if not b.inputs["Subsurface Weight"].is_linked:
        b.inputs["Subsurface Weight"].default_value = w
    b.inputs["Subsurface Scale"].default_value = s
    b.inputs["Subsurface Radius"].default_value = r
    if not b.inputs["Specular IOR Level"].is_linked:
        b.inputs["Specular IOR Level"].default_value = 0.38  # was up to 1.0: greasy, plastic highlights
    if not b.inputs["Roughness"].is_linked:
        b.inputs["Roughness"].default_value = 0.46
    _saturate(nt, b, SKIN_SATURATION)


def cornea(m):
    """Clear, glossy cornea: transparent + sharp glossy, so reflections stay full strength."""
    nt = m.node_tree
    out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    gl = nt.nodes.new("ShaderNodeBsdfGlossy")
    gl.inputs["Roughness"].default_value = 0.05
    gl.inputs["Color"].default_value = (0.62, 0.62, 0.62, 1.0)  # a soft catchlight, not a white rim at the lids
    fr = nt.nodes.new("ShaderNodeFresnel")
    fr.inputs["IOR"].default_value = 1.376  # the cornea's own
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(fr.outputs["Fac"], mix.inputs["Fac"])
    nt.links.new(tr.outputs["BSDF"], mix.inputs[1])
    nt.links.new(gl.outputs["BSDF"], mix.inputs[2])
    nt.links.new(mix.outputs["Shader"], out.inputs["Surface"])
    if hasattr(m, "surface_render_method"):
        m.surface_render_method = "BLENDED"
    if hasattr(m, "use_transparent_shadow"):
        m.use_transparent_shadow = True


def eye(m):
    b = _bsdf(m)
    if not b.inputs["Roughness"].is_linked:
        b.inputs["Roughness"].default_value = 0.18
    if not b.inputs["Specular IOR Level"].is_linked:
        b.inputs["Specular IOR Level"].default_value = 0.6
    _saturate(m.node_tree, b, 1.1)  # a touch more iris colour


def wet(m):
    b = _bsdf(m)
    if not b.inputs["Roughness"].is_linked:
        b.inputs["Roughness"].default_value = 0.32
    if not b.inputs["Specular IOR Level"].is_linked:
        b.inputs["Specular IOR Level"].default_value = 0.5


def hair(m):
    """Keep hair's own colour: sheen and strong highlights read as grey on alpha cards, so only cap them."""
    b = _bsdf(m)
    if not b.inputs["Roughness"].is_linked:
        b.inputs["Roughness"].default_value = max(0.55, min(b.inputs["Roughness"].default_value, 0.65))
    if not b.inputs["Sheen Weight"].is_linked:
        b.inputs["Sheen Weight"].default_value = 0.0
    if not b.inputs["Specular IOR Level"].is_linked:
        b.inputs["Specular IOR Level"].default_value = min(b.inputs["Specular IOR Level"].default_value, 0.35)
    _saturate(m.node_tree, b, 1.1)


PASSES = {"skin": skin, "cornea": cornea, "eye": eye, "wet": wet, "hair": hair}


def enliven(materials) -> dict:
    """Apply the pass to these materials once each; returns {kind: count}."""
    done = {}
    for m in materials:
        if not m or not m.use_nodes or m.get("enlivened") or _bsdf(m) is None:
            continue
        k = kind(m.name)
        if k in PASSES:
            PASSES[k](m)
            m["enlivened"] = k
            done[k] = done.get(k, 0) + 1
    return done


if __name__ == "__main__" and bpy is not None:
    mats = {m for o in bpy.data.objects if o.type == "MESH" for m in o.data.materials if m}
    print("ENLIVENED", enliven(mats))
    if "--save" in sys.argv:
        bpy.context.preferences.filepaths.save_version = 0
        bpy.ops.wm.save_mainfile(compress=True)
        print("SAVED", bpy.data.filepath)
