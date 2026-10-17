"""Checks of the Unity scene and shader settings (docs/screen-output.md,
"The Unity files") against the dump of scripts/unity/scene_dump.py, and
of host.quad_pixel.

Usage: python -I unity_scene_check.py <reference dir> <dump dir>
(<dump dir> = extracted\\unity, written by scene_dump.py; pure Python)

1. Project settings: gamma colour space, the window settings.
2. The scene: the four objects, the camera, the Pixel Perfect Camera's
   bytes, which object holds which material and mesh.
3. Shader pass states: blending, depth, culling, queue.
4. Shader programs: the instructions of the four fragment programs and
   the screen shaders' turned-over v.
5. host.quad_pixel: the shader's arithmetic is ordinary alpha blending;
   half-opacity examples.
"""
import json
import os
import re
import struct
import sys

sys.path.insert(0, sys.argv[1])
import host as H  # noqa: E402

dump = sys.argv[2]
problems = []


def expect(name, got, want):
    ok = got == want
    print("   %-58s %s%s" % (name, got, "" if ok else "   (wanted %s)" % (want,)))
    if not ok:
        problems.append(name)


def obj(name):
    with open(os.path.join(dump, "objects", name), encoding="utf-8") as fh:
        return json.load(fh)


with open(os.path.join(dump, "summary.txt"), encoding="utf-8") as fh:
    summary = fh.read()


def asm_body(name):
    """The instruction lines of a disassembled program (comments and
    declarations dropped)."""
    with open(os.path.join(dump, "shaders", name), encoding="utf-8") as fh:
        lines = [l.strip() for l in fh]
    return [l for l in lines if l and not l.startswith("//") and not l.startswith("dcl_")
            and l not in ("ps_4_0", "vs_4_0")]


print("1. Project settings")
ps = obj("globalgamemanagers_1_PlayerSettings.json")
expect("colour space (0 gamma, 1 linear)", ps["m_ActiveColorSpace"], 0)
expect("default window", (ps["defaultScreenWidth"], ps["defaultScreenHeight"]), (1140, 640))
expect("resizable window", ps["resizableWindow"], True)
expect("full-screen mode (1 = full-screen window)", ps["fullscreenMode"], 1)

print("2. The scene")
names = {i: obj("level0_%d_GameObject.json" % i) for i in (1, 2, 3, 4)}
expect("objects", [(names[i]["m_Name"], names[i]["m_IsActive"]) for i in (1, 2, 3, 4)],
       [("Phantom Cursor", False), ("Main Camera", True), ("Host", True), ("Quad", False)])
cam = obj("level0_9_Camera.json")
expect("camera clear (2 = solid colour)", cam["m_ClearFlags"], 2)
expect("camera background", [cam["m_BackGroundColor"][k] for k in "rgba"], [0.0, 0.0, 0.0, 0.0])
expect("camera orthographic, near, far", (cam["orthographic"], cam["near clip plane"], cam["far clip plane"]),
       (True, 0.5, 100.0))
expect("camera position", [obj("level0_6_Transform.json")["m_LocalPosition"][k] for k in "xyz"],
       [0.0, 0.0, -2.0])
expect("camera rotation (looks along +z)", [obj("level0_6_Transform.json")["m_LocalRotation"][k] for k in "xyzw"],
       [0.0, 0.0, 0.0, 1.0])
expect("screen quad position", [obj("level0_8_Transform.json")["m_LocalPosition"][k] for k in "xyz"],
       [0.0, 0.0, 0.0])
raw = bytes.fromhex(obj("level0_18_MonoBehaviour.json")["raw"])
expect("PixelPerfectCamera bytes", len(raw), 64)
expect("PixelPerfectCamera ppu, reference", struct.unpack_from("<iii", raw, 32), (100, 570, 320))
expect("upscaleRT, pixelSnapping, cropX, cropY, stretchFill", struct.unpack_from("<5i", raw, 44),
       (0, 1, 0, 0, 1))
expect("phantom cursor material", obj("level0_10_MeshRenderer.json")["m_Materials"][0]["m_PathID"], 2)
expect("screen quad material", obj("level0_11_MeshRenderer.json")["m_Materials"][0]["m_PathID"], 3)
expect("ScreenMat's shader (4 = Unlit/ScreenShader)", obj("sharedassets0.assets_3_Material.json")["m_Shader"]["m_PathID"], 4)
expect("PhantomCursorMat's shader (6)", obj("sharedassets0.assets_2_Material.json")["m_Shader"]["m_PathID"], 6)
expect("render queues from the shaders", [obj("sharedassets0.assets_%d_Material.json" % i)["m_CustomRenderQueue"]
                                          for i in (2, 3)], [-1, -1])
expect("both meshes: built-in Quad, corners at -0.5 / 0.5",
       re.search(r"mesh unity default resources:10210 'Quad': 4 corners \['v 0\.5 -0\.5[^]]*-0\.5 0\.5", summary) is not None,
       True)

print("3. Shader pass states")
blocks = re.split(r"\n(?=\d+ 'Unlit/)", summary.split("== Shaders")[1])
state = {}
for b in blocks:
    m = re.match(r"\s*\d+ '([^']+)'", b)
    if m:
        state[m.group(1)] = b
expect("QuadShader blend", "Blend One OneMinusSrcAlpha, alpha One OneMinusSrcAlpha  op Add / Add  colour mask 15"
       in state["Unlit/QuadShader"], True)
expect("QuadShader depth and culling", "ZTest Always  ZWrite Off  Cull Off" in state["Unlit/QuadShader"], True)
for s in ("Unlit/ScreenShader", "Unlit/ScreenPausedShader"):
    expect(s + " blend off", "Blend One Zero, alpha One Zero" in state[s], True)
    expect(s + " depth", "ZTest LessEqual  ZWrite On  Cull Back" in state[s], True)
expect("PhantomCursorShader blend", "Blend One OneMinusSrcAlpha" in state["Unlit/PhantomCursorShader"], True)
expect("PhantomCursorShader depth", "ZTest LessEqual  ZWrite On  Cull Back" in state["Unlit/PhantomCursorShader"], True)
expect("PhantomCursorShader queue", "('QUEUE', 'Background')" in state["Unlit/PhantomCursorShader"], True)
expect("ScreenShader has no queue tag (default, geometry)", "QUEUE" in state["Unlit/ScreenShader"], False)

print("4. Shader programs")
expect("QuadShader fragment", asm_body("Unlit_QuadShader_p0_fp0.asm"), [
    "sample r0.xyzw, v2.xyxx, t0.xyzw, s0",
    "mul r0.xyzw, r0.xyzw, v1.xyzw",
    "mul o0.xyz, r0.wwww, r0.xyzx",
    "mov o0.w, r0.w",
    "ret"])
expect("QuadShader vertex passes the colour on", "mov o1.xyzw, v1.xyzw" in asm_body("Unlit_QuadShader_p0_vp0.asm"), True)
expect("ScreenShader fragment", asm_body("Unlit_ScreenShader_p0_fp0.asm"),
       ["sample o0.xyzw, v0.xyxx, t0.xyzw, s0", "ret"])
expect("ScreenPausedShader fragment", asm_body("Unlit_ScreenPausedShader_p0_fp0.asm"), [
    "sample r0.xyzw, v0.xyxx, t0.xyzw, s0",
    "dp3 r0.x, r0.xyzx, l(0.299000, 0.587000, 0.114000, 0.000000)",
    "mov o0.w, r0.w",
    "mul o0.xyz, r0.xxxx, l(0.750000, 0.750000, 0.750000, 0.000000)",
    "ret"])
expect("PhantomCursorShader fragment", asm_body("Unlit_PhantomCursorShader_p0_fp0.asm"), [
    "sample r0.xyzw, v0.xyxx, t0.xyzw, s0",
    "mul o0.xyz, r0.wwww, r0.xyzx",
    "mov o0.w, r0.w",
    "ret"])
flip = "mad r0.xy, v1.xyxx, l(1.000000, -1.000000, 0.000000, 0.000000), l(0.000000, 1.000000, 0.000000, 0.000000)"
for s in ("ScreenShader", "ScreenPausedShader", "PhantomCursorShader"):
    expect(s + " reads (u, 1 - v)", flip in asm_body("Unlit_%s_p0_vp0.asm" % s), True)

print("5. host.quad_pixel")
worst = 0
for tr, ta, cr, ca, under in [(t, a, c, k, u) for t in (0, 77, 255) for a in (0, 1, 128, 254, 255)
                              for c in (0.0, 0.5, 1.0) for k in (0.0, 0.25, 0.5, 1.0) for u in (0, 90, 255)]:
    got = H.quad_pixel((tr, tr, tr, ta), (cr, cr, cr, ca), (under,) * 3)[0]
    a = ta / 255.0 * ca
    want = H.to_byte(tr / 255.0 * cr * a + under / 255.0 * (1 - a))
    worst = max(worst, abs(got - want))
expect("same as ordinary alpha blending (largest difference)", worst, 0)
expect("opaque white over anything", H.quad_pixel((255, 255, 255, 255), (1, 1, 1, 1), (10, 20, 30)), (255, 255, 255))
expect("alpha below 1 lets the picture under show", H.quad_pixel((0, 0, 0, 255), (1, 1, 1, 0.5), (200, 200, 200)),
       (100, 100, 100))
expect("half-opacity red seal over pale paper", H.quad_pixel((200, 30, 30, 255), (1, 1, 1, 0.5), (250, 250, 250)),
       (225, 140, 140))
# Over 255 the red would be 227.5 exactly: a tie, whose rounding is the
# graphics card's (to_byte gives 227 through float noise). Not decidable
# from the files.
expect("a tie lands on the float noise (227.5 -> 227)", H.quad_pixel((200, 30, 30, 255), (1, 1, 1, 0.5),
                                                                    (255, 255, 255))[0], 227)
expect("paused grey of pure white", H.paused_pixel((255, 255, 255)), (191, 191, 191))

print()
print("%d problems" % len(problems) if problems else "0 problems")
for p in problems:
    print("   " + p)
