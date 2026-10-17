"""Dump the Unity scene, materials, shaders and project settings of the
game (docs/screen-output.md, "The Unity files").

Usage: .venv\\Scripts\\python -I scene_dump.py <PapersPlease_Data dir> <out dir>
(<PapersPlease_Data dir> = game\\PapersPlease_Data, the project's copy;
<out dir> = extracted\\unity. Needs UnityPy, installed in the project's
.venv, and Windows' own D3DCompiler_47.dll to disassemble the shaders.)

Writes:
  <out>/objects/<file>_<id>_<type>.json   every object except scripts,
                                          sounds, pictures and the art file
  <out>/shaders/<name>_<pass>_<vp|fp>.asm  each compiled DirectX 11 program,
                                          disassembled
  <out>/summary.txt                       what docs/screen-output.md uses
and prints the summary.

The game is an IL2CPP build, so the files carry no field lists for the
game's own scripts (MonoBehaviour). Their bytes are decoded here by hand
from the field order in dumps/il2cppdumper/dump.cs (PixelPerfectCamera,
HostUnity). Unity's own classes are read with UnityPy's built-in field
lists for 2020.3.34.
"""
import ctypes
import json
import os
import struct
import sys

import UnityPy

data_dir, out = sys.argv[1], sys.argv[2]
FILES = ["level0", "globalgamemanagers", "globalgamemanagers.assets", "sharedassets0.assets"]
SKIP = {"MonoScript", "AudioClip", "TextAsset", "Texture2D"}

BLEND = ["Zero", "One", "DstColor", "SrcColor", "OneMinusDstColor", "SrcAlpha",
         "OneMinusSrcColor", "DstAlpha", "OneMinusDstAlpha", "SrcAlphaSaturate",
         "OneMinusSrcAlpha"]
BLENDOP = {0: "Add", 1: "Subtract", 2: "ReverseSubtract", 3: "Min", 4: "Max"}
COMPARE = ["Disabled", "Never", "Less", "Equal", "LessEqual", "Greater",
           "NotEqual", "GreaterEqual", "Always"]
CULL = ["Off", "Front", "Back"]
CLEAR = {1: "Skybox", 2: "SolidColor", 3: "Depth", 4: "Nothing"}
COLORSPACE = {0: "Gamma", 1: "Linear"}
FULLSCREEN = {0: "ExclusiveFullScreen", 1: "FullScreenWindow", 2: "MaximizedWindow", 3: "Windowed"}

summary = []


def say(line=""):
    summary.append(line)


os.makedirs(os.path.join(out, "objects"), exist_ok=True)
os.makedirs(os.path.join(out, "shaders"), exist_ok=True)

envs = {name: UnityPy.load(os.path.join(data_dir, name)) for name in FILES}
sf = {name: next(iter(env.files.values())) for name, env in envs.items()}


def ext_name(file_name, file_id):
    """The file a PPtr with this file id points into."""
    if file_id == 0:
        return file_name
    return os.path.basename(sf[file_name].externals[file_id - 1].path)


def obj(file_name, path_id):
    return sf[file_name].objects[path_id]


def ptr(file_name, p):
    """'file:id' for a PPtr given as a dict or as (file id, path id)."""
    fid, pid = (p["m_FileID"], p["m_PathID"]) if isinstance(p, dict) else p
    if pid == 0:
        return "none"
    return "%s:%d" % (ext_name(file_name, fid), pid)


# ---- every object as JSON -------------------------------------------------
trees = {}
for name in FILES:
    for o in sf[name].objects.values():
        if o.type.name in SKIP or o.type.name == "Shader":
            continue
        try:
            tree = o.read_typetree()
        except Exception as e:  # MonoBehaviour: no field list in an IL2CPP build
            tree = {"error": repr(e), "raw": o.get_raw_data().hex()}
        trees[(name, o.path_id)] = tree
        with open(os.path.join(out, "objects", "%s_%d_%s.json" % (name, o.path_id, o.type.name)),
                  "w", encoding="utf-8") as fh:
            json.dump(tree, fh, indent=1, default=str)

# ---- project settings -------------------------------------------------------
say("== Project settings (globalgamemanagers)")
for o in sf["globalgamemanagers"].objects.values():
    t = trees.get(("globalgamemanagers", o.path_id))
    if o.type.name == "PlayerSettings":
        say("unity version            %s" % sf["level0"].unity_version)
        say("colour space             %s (%d)" % (COLORSPACE.get(t["m_ActiveColorSpace"]), t["m_ActiveColorSpace"]))
        say("default window           %d x %d" % (t["defaultScreenWidth"], t["defaultScreenHeight"]))
        say("resizable window         %s" % t["resizableWindow"])
        say("full-screen mode         %s (%d)" % (FULLSCREEN.get(t["fullscreenMode"]), t["fullscreenMode"]))
        say("allow full-screen switch %s" % t["allowFullscreenSwitch"])
        say("run / visible in background %s / %s" % (t["runInBackground"], t["visibleInBackground"]))
        say("default is native resolution %s" % t.get("defaultIsNativeResolution"))
        say("aspect ratios allowed    %s" % t.get("m_SupportedAspectRatios"))
    if o.type.name == "QualitySettings":
        cur = t["m_CurrentQuality"]
        q = t["m_QualitySettings"][cur]
        say("quality level            %d of %d: %s" % (cur, len(t["m_QualitySettings"]), q["name"]))
        say("  vSyncCount %s, antiAliasing %s, anisotropicTextures %s, masterTextureLimit %s"
            % (q["vSyncCount"], q["antiAliasing"], q["anisotropicTextures"], q.get("globalTextureMipmapLimit", q.get("masterTextureLimit"))))
        say("  every level: " + ", ".join("%s (vSync %s, AA %s)" % (l["name"], l["vSyncCount"], l["antiAliasing"])
                                          for l in t["m_QualitySettings"]))
    if o.type.name == "GraphicsSettings":
        say("transparency sort mode   %s" % t["m_TransparencySortMode"])

# ---- the scene --------------------------------------------------------------
say()
say("== The scene (level0)")
scripts = {}
for o in sf["level0"].objects.values():
    if o.type.name != "GameObject":
        continue
    t = trees[("level0", o.path_id)]
    say("GameObject %d '%s'  active %s  layer %d" % (o.path_id, t["m_Name"], t["m_IsActive"], t["m_Layer"]))
    for c in t["m_Component"]:
        cid = c["component"]["m_PathID"]
        co = obj("level0", cid)
        ct = trees[("level0", cid)]
        line = "   %d %s" % (cid, co.type.name)
        if co.type.name == "Transform":
            p, r, s = ct["m_LocalPosition"], ct["m_LocalRotation"], ct["m_LocalScale"]
            line += "  position (%g, %g, %g)  rotation (%g, %g, %g, %g)  scale (%g, %g, %g)  parent %s" % (
                p["x"], p["y"], p["z"], r["x"], r["y"], r["z"], r["w"], s["x"], s["y"], s["z"],
                ptr("level0", ct["m_Father"]))
        elif co.type.name == "Camera":
            b = ct["m_BackGroundColor"]
            line += ("  enabled %s  clear %s  background (%g, %g, %g, %g)  orthographic %s size %g"
                     "  near %g far %g  depth %g  HDR %s  MSAA %s  target %s" % (
                         ct["m_Enabled"], CLEAR.get(ct["m_ClearFlags"]), b["r"], b["g"], b["b"], b["a"],
                         ct["orthographic"], ct["orthographic size"], ct["near clip plane"],
                         ct["far clip plane"], ct["m_Depth"], ct["m_HDR"], ct["m_AllowMSAA"],
                         ptr("level0", ct["m_TargetTexture"])))
        elif co.type.name == "MeshRenderer":
            line += "  enabled %s  materials %s  sorting layer %d order %d" % (
                ct["m_Enabled"], [ptr("level0", m) for m in ct["m_Materials"]],
                ct["m_SortingLayerID"], ct["m_SortingOrder"])
        elif co.type.name == "MeshFilter":
            line += "  mesh %s" % ptr("level0", ct["m_Mesh"])
        elif co.type.name == "MonoBehaviour":
            raw = co.get_raw_data()
            _gofid, _gopid, enabled, sfid, spid = struct.unpack_from("<iq?3xiq", raw, 0)
            script = ext_name("level0", sfid)
            sname = obj(script, spid).read().m_ClassName if script in sf else "?"
            scripts[cid] = (sname, raw)
            line += "  enabled %s  script %s:%d = %s  (%d bytes)" % (enabled, script, spid, sname, len(raw))
        say(line)


def mono_fields(raw):
    """Offset of the first own field: m_GameObject, m_Enabled, m_Script, m_Name."""
    n = struct.unpack_from("<i", raw, 32 - 4)[0]
    return 32 + ((n + 3) & ~3)


for cid, (sname, raw) in scripts.items():
    pos = mono_fields(raw)
    if sname == "PixelPerfectCamera":
        ppu, rx, ry = struct.unpack_from("<iii", raw, pos)
        flags = struct.unpack_from("<5i", raw, pos + 12)  # five bools, each padded to 4 bytes
        names = ["upscaleRT", "pixelSnapping", "cropFrameX", "cropFrameY", "stretchFill"]
        say()
        say("PixelPerfectCamera (%d): assetsPPU %d, reference %d x %d, %s" % (
            cid, ppu, rx, ry, ", ".join("%s %s" % (n, bool(v)) for n, v in zip(names, flags))))
        assert pos + 32 == len(raw), "PixelPerfectCamera: %d bytes left over" % (len(raw) - pos - 32)
    if sname == "HostUnity":
        say()
        say("HostUnity (%d):" % cid)

        def pp(p):
            fid, pid = struct.unpack_from("<iq", raw, p)
            return ptr("level0", (fid, pid)), p + 12

        for f in ["screenQuad", "screenShader", "screenPausedShader", "quadShader", "artAsset", "audioMixer"]:
            v, pos = pp(pos)
            say("   %-20s %s" % (f, v))
        n = struct.unpack_from("<i", raw, pos)[0]
        pos += 4
        paths = []
        for _ in range(n):
            ln = struct.unpack_from("<i", raw, pos)[0]
            paths.append(raw[pos + 4:pos + 4 + ln].decode("utf-8"))
            pos += 4 + ((ln + 3) & ~3)
        say("   %-20s %d strings, first %s" % ("audioPaths", n, paths[:2]))
        n = struct.unpack_from("<i", raw, pos)[0]
        pos += 4 + 12 * n
        say("   %-20s %d references" % ("audioClips", n))
        for f in ["pixelPerfectCamera", "phantomCursor"]:
            v, pos = pp(pos)
            say("   %-20s %s" % (f, v))
        assert pos == len(raw), "HostUnity: %d bytes left over" % (len(raw) - pos)

# The mesh both renderers use (Unity's built-in quad, by its name).
mf = next(t for (f, i), t in trees.items() if f == "level0" and "m_Mesh" in t)
mesh_file = ext_name("level0", mf["m_Mesh"]["m_FileID"])
mesh_path = os.path.join(data_dir, "Resources", mesh_file)
if os.path.exists(mesh_path):
    menv = UnityPy.load(mesh_path)
    m = next(iter(menv.files.values())).objects[mf["m_Mesh"]["m_PathID"]].read()
    verts = m.export().splitlines() if hasattr(m, "export") else []
    vs = [l for l in verts if l.startswith("v ")]
    say()
    say("mesh %s:%d '%s': %d corners %s" % (mesh_file, mf["m_Mesh"]["m_PathID"], m.m_Name, len(vs), vs))

# ---- materials ----------------------------------------------------------------
say()
say("== Materials")
for name in FILES:
    for o in sf[name].objects.values():
        if o.type.name != "Material":
            continue
        t = trees[(name, o.path_id)]
        sh = obj(ext_name(name, t["m_Shader"]["m_FileID"]), t["m_Shader"]["m_PathID"]) \
            if ext_name(name, t["m_Shader"]["m_FileID"]) in sf else None
        shname = sh.read().m_ParsedForm.m_Name if sh is not None else ptr(name, t["m_Shader"])
        tex = {k: ptr(name, v["m_Texture"]) for k, v in t["m_SavedProperties"]["m_TexEnvs"]}
        say("%s:%d '%s'  shader %s  render queue %d  keywords '%s'  textures %s" % (
            name, o.path_id, t["m_Name"], shname, t["m_CustomRenderQueue"], t["m_ShaderKeywords"], tex))
        say("   floats " + ", ".join("%s %g" % (k, v) for k, v in t["m_SavedProperties"]["m_Floats"]))
        say("   colours " + ", ".join("%s (%g, %g, %g, %g)" % (k, v["r"], v["g"], v["b"], v["a"])
                                       for k, v in t["m_SavedProperties"]["m_Colors"]))

# ---- shaders --------------------------------------------------------------------
d3d = ctypes.WinDLL("D3DCompiler_47.dll")
d3d.D3DDisassemble.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_uint, ctypes.c_char_p,
                               ctypes.POINTER(ctypes.c_void_p)]


def disassemble(code):
    blob = ctypes.c_void_p()
    hr = d3d.D3DDisassemble(code, len(code), 0, None, ctypes.byref(blob))
    if hr != 0:
        return "D3DDisassemble failed: 0x%08x" % (hr & 0xFFFFFFFF)
    vt = ctypes.cast(ctypes.cast(blob, ctypes.POINTER(ctypes.c_void_p))[0], ctypes.POINTER(ctypes.c_void_p))
    get_ptr = ctypes.WINFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p)(vt[3])
    get_size = ctypes.WINFUNCTYPE(ctypes.c_size_t, ctypes.c_void_p)(vt[4])
    release = ctypes.WINFUNCTYPE(ctypes.c_ulong, ctypes.c_void_p)(vt[2])
    text = ctypes.string_at(get_ptr(blob), get_size(blob)).decode("utf-8", "replace").rstrip("\0")
    release(blob)
    return text


def fv(v):
    """The material property that sets a state value, or None when the
    value is fixed (Unity names a fixed value '<noninit>')."""
    return ("[%s]" % v.name) if v.name and v.name != "<noninit>" else None


def blend_name(v, names):
    return fv(v) or names[int(v.val)] if int(v.val) < len(names) else str(v.val)


say()
say("== Shaders (sharedassets0.assets)")
from UnityPy.export.ShaderConverter import ShaderProgram  # noqa: E402
from UnityPy.helpers import CompressionHelper  # noqa: E402
from UnityPy.streams import EndianBinaryReader  # noqa: E402

for o in sf["sharedassets0.assets"].objects.values():
    if o.type.name != "Shader":
        continue
    s = o.read()
    pf = s.m_ParsedForm
    say("%d '%s'  properties %s  platforms %s" % (
        o.path_id, pf.m_Name, [p.m_Name for p in pf.m_PropInfo.m_Props], list(s.platforms)))
    programs = []
    for i in range(len(s.platforms)):
        def first(a):
            return a[i][0] if isinstance(a[i], list) else a[i]
        raw = bytes(s.compressedBlob)[first(s.offsets):first(s.offsets) + first(s.compressedLengths)]
        dec = CompressionHelper.decompress_lz4(raw, first(s.decompressedLengths))
        programs.append(ShaderProgram(EndianBinaryReader(dec, endian="<"), o.assets_file.version))
    for si, sub in enumerate(pf.m_SubShaders):
        say("   subshader %d  LOD %d  tags %s" % (si, sub.m_LOD, sub.m_Tags.tags))
        for pi, ps in enumerate(sub.m_Passes):
            st = ps.m_State
            b = st.rtBlend0
            say("   pass %d  tags %s  LOD %d" % (pi, st.m_Tags.tags, st.m_LOD))
            say("      Blend %s %s, alpha %s %s  op %s / %s  colour mask %s  separate per target %s" % (
                blend_name(b.srcBlend, BLEND), blend_name(b.destBlend, BLEND),
                blend_name(b.srcBlendAlpha, BLEND), blend_name(b.destBlendAlpha, BLEND),
                fv(b.blendOp) or BLENDOP.get(int(b.blendOp.val)), fv(b.blendOpAlpha) or BLENDOP.get(int(b.blendOpAlpha.val)),
                fv(b.colMask) or int(b.colMask.val), st.rtSeparateBlend))
            say("      ZTest %s  ZWrite %s  Cull %s  AlphaToMask %s  offset %g, %g  stencil ref %g read %g write %g" % (
                fv(st.zTest) or COMPARE[int(st.zTest.val)], fv(st.zWrite) or ("On" if st.zWrite.val else "Off"),
                fv(st.culling) or CULL[int(st.culling.val)], st.alphaToMask.val,
                st.offsetFactor.val, st.offsetUnits.val, st.stencilRef.val, st.stencilReadMask.val,
                st.stencilWriteMask.val))
            for kind, prog in (("vp", ps.progVertex), ("fp", ps.progFragment)):
                for spi, sp in enumerate(prog.m_SubPrograms):
                    chans = [(c.source, c.target) for c in sp.m_Channels.m_Channels]
                    code = None
                    for plat, progs in zip(s.platforms, programs):
                        code = bytes(progs.m_SubPrograms[sp.m_BlobIndex].m_ProgramCode)
                        start = code.find(b"DXBC")
                        if start < 0:
                            continue
                        asm = disassemble(code[start:])
                        fn = "%s_p%d_%s%d.asm" % (pf.m_Name.replace("/", "_"), pi, kind, spi)
                        with open(os.path.join(out, "shaders", fn), "w", encoding="utf-8") as fh:
                            fh.write(asm)
                        say("      %s %d: type %d, tier %d, channels (source, target) %s -> shaders/%s (%d lines)" % (
                            kind, spi, sp.m_GpuProgramType, sp.m_ShaderHardwareTier, chans, fn,
                            asm.count("\n")))

text = "\n".join(summary) + "\n"
with open(os.path.join(out, "summary.txt"), "w", encoding="utf-8") as fh:
    fh.write(text)
print(text)
