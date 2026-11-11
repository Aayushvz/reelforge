"""Cinema look: Cycles (GPU, denoised) for faces, Eevee for wider shots, real skin scattering, natural skin
tones under mood light, a film-style camera (camera_rig.py). Quality tiers: preview | standard | cinema.

Nothing here edits the built assets: materials are adjusted in the render session only."""
import bpy

from bl_common import EEVEE

NAME = "cinema"
USE_RIG = True
PER_SHOT = True
# Moods colour the room, not the face: the key keeps most of its own colour so skin stays skin.
MOOD_TINT = {"Key": 0.30, "Rim": 0.65, "Glow": 1.0}
# Low-key: a dimmer key and little fill, so the shadow side models the face; the rim keeps the edge.
LIGHT_SCALE = {"Key": 0.55, "Rim": 0.9, "Glow": 0.8, "Fill": 0.35}
BODY_CHEAT = 0.28  # two characters open up toward each other (about 16 degrees), like stage blocking
LISTEN_YAW = 0.22
FACE_KINDS = ("closeup", "ecu")

# quality -> (cycles samples for faces, cycles samples for wider shots, eevee samples, noise threshold)
TIERS = {"preview": (24, 24, 24, 0.05), "standard": (48, 48, 32, 0.02), "cinema": (128, 96, 64, 0.01)}


def _gpu(sc):
    """Pick OptiX, then CUDA, else CPU. Returns the device kind in use."""
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
    except KeyError:
        sc.cycles.device = "CPU"
        return "CPU"
    for kind in ("OPTIX", "CUDA"):
        try:
            prefs.compute_device_type = kind
        except TypeError:
            continue
        (getattr(prefs, "refresh_devices", None) or prefs.get_devices)()
        if any(d.type == kind for d in prefs.devices):
            for d in prefs.devices:
                d.use = d.type == kind
            sc.cycles.device = "GPU"
            return kind
    sc.cycles.device = "CPU"
    return "CPU"


def is_skin(mat):
    n = mat.name.lower()
    return ("skin" in n or n == "body") and not any(k in n for k in ("eye", "nail", "lash", "teeth", "tongue"))


def _skin(characters, glow):
    """Light has to travel through skin or it reads as plastic: random-walk subsurface on every skin material."""
    done = set()
    for c in characters:
        for o in c["objects"]:
            if o.type != "MESH":
                continue
            for m in o.data.materials:
                if not m or m.name in done or not m.use_nodes or not is_skin(m):
                    continue
                done.add(m.name)
                for b in (n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"):
                    b.subsurface_method = "RANDOM_WALK_SKIN"
                    w = b.inputs["Subsurface Weight"]
                    if not w.is_linked:  # one calibrated amount: authored values range from 0 to 0.67 (waxy)
                        w.default_value = min(0.4, 0.2 * glow)
                    b.inputs["Subsurface Radius"].default_value = (1.0, 0.35, 0.2)
                    b.inputs["Subsurface Scale"].default_value = 0.011
                    if "Subsurface IOR" in b.inputs:
                        b.inputs["Subsurface IOR"].default_value = 1.4


def apply_scene(sc, plan, characters):
    q = plan.get("quality", "standard")
    lp = plan.get("look_params", {})
    sc.render.resolution_x, sc.render.resolution_y = plan["resolution"]
    sc.render.resolution_percentage = 50 if q == "preview" else 100
    sc.render.fps = plan["fps"]
    sc.frame_start, sc.frame_end = 1, plan["n_frames"]
    im = sc.render.image_settings
    im.file_format = "PNG"
    im.color_depth = "16" if q == "cinema" else "8"
    sc.render.dither_intensity = 1.0  # dark gradients band in 8 bits without it
    sc.render.use_motion_blur = True
    sc.render.motion_blur_shutter = 0.5
    sc.eevee.taa_render_samples = TIERS[q][2]
    if hasattr(sc.eevee, "shadow_pool_size"):  # rooms with 20+ practicals overflow the default pool
        sc.eevee.shadow_pool_size = "1024"
    cy = sc.cycles
    kind = _gpu(sc)
    cy.use_adaptive_sampling = True
    cy.adaptive_threshold = TIERS[q][3]
    cy.adaptive_min_samples = 16
    cy.use_denoising = True
    cy.denoiser = "OPENIMAGEDENOISE"
    cy.denoising_input_passes = "RGB_ALBEDO_NORMAL"
    cy.denoising_prefilter = "ACCURATE"
    if hasattr(cy, "denoising_use_gpu"):
        cy.denoising_use_gpu = kind != "CPU"
    cy.max_bounces, cy.diffuse_bounces, cy.glossy_bounces = 8, 3, 4
    cy.transmission_bounces, cy.volume_bounces, cy.transparent_max_bounces = 6, 1, 8
    cy.sample_clamp_indirect, cy.sample_clamp_direct = 8.0, 0.0
    cy.caustics_reflective = cy.caustics_refractive = False
    cy.filter_width = 1.2
    cy.use_persistent_data = False  # shots switch engines; keep memory predictable on 8 GB
    _skin(characters, float(lp.get("skin_glow", 1.0)))
    fill = bpy.data.objects.get("Fill")
    if fill:
        fill.data.energy *= LIGHT_SCALE["Fill"]
    haze = float(lp.get("haze", 1.0))
    nt = sc.world.node_tree if sc.world and sc.world.use_nodes else None
    out = next((n for n in nt.nodes if n.type == "OUTPUT_WORLD"), None) if nt else None
    _HAZE.clear()
    if out and out.inputs["Volume"].is_linked:
        link = out.inputs["Volume"].links[0]
        dens = link.from_node.inputs.get("Density")
        if dens:  # Eevee shots keep a thinner haze
            dens.default_value *= 0.5 * haze
        _HAZE.update(tree=nt, src=link.from_socket, dst=out.inputs["Volume"])
    print(f"cinema look: quality={q} cycles device={kind}")


_HAZE = {}  # the world's haze volume link, unplugged for Cycles shots


def shot_settings(sc, plan, shot):
    q = plan.get("quality", "standard")
    face = shot["kind"] in FACE_KINDS
    cycles = q == "cinema" or (q == "standard" and face)
    sc.render.engine = "CYCLES" if cycles else EEVEE
    if _HAZE:  # a world-wide volume costs Cycles minutes per frame and greys the picture out
        linked = _HAZE["dst"].is_linked
        if cycles and linked:
            _HAZE["tree"].links.remove(_HAZE["dst"].links[0])
        elif not cycles and not linked:
            _HAZE["tree"].links.new(_HAZE["src"], _HAZE["dst"])
    if cycles:
        sc.cycles.samples = TIERS[q][0 if face else 1]
    return sc.render.engine
