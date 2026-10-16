// Runs the game's own Layout constructor (and Layout's static constructor)
// in Ghidra's emulator for the DESKTOP platform, and prints the finished
// Layout object as raw memory, for scripts/reference/layout_dump.py to decode.
//
// The constructor is too big for the decompiler, and its booth rectangles are
// computed from one another, so running it is easier and safer than reading
// thousands of instructions by hand.
//
// How it works:
// - every class slot (symbol "..._TypeInfo") the code uses is pointed at a fake
//   class record: its static block holds 64 fake enum values (object +0x10 =
//   index), its method table points at stub addresses, so a call through an
//   object lands in a stub that records it and returns 0;
// - every string slot ("StringLiteral_N") is pointed at a fake string object
//   whose text is "#N", so keys can be recognised afterwards;
// - calls into a few engine helpers are replaced by stubs: object allocation,
//   boxing, the Rect, PointData and DockPoint constructors, StringMap.set,
//   casts, write barriers, class initialisation, floor and ceil, and the
//   string building of the constructor's log line; app.Num.lerpScale runs
//   as the game's own code;
// - any other direct call is reported and returns 0.
// Every stub call is printed, so the run can be checked.
//
// Headless use:
//   analyzeHeadless <project dir> <project name> -process GameAssembly.dll
//     -noanalysis -readOnly -scriptPath scripts\ghidra
//     -postScript EmulateLayout.java
//@category IL2CPP

import java.util.*;

import ghidra.app.emulator.EmulatorHelper;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.Symbol;
import ghidra.program.model.symbol.SymbolIterator;

public class EmulateLayout extends GhidraScript {

	private static final long CTOR = 0x180496810L;    // Layout.__hx_ctor__Layout(this, platform)
	private static final long CCTOR = 0x1804a1280L;   // Layout..cctor()
	private static final long INIT_FLAG = 0x180c9b3c3L; // "metadata set up" byte of the ctor

	private static final long ALLOC = 0x180127190L;     // thunk_FUN_1800f3b80: new object
	private static final long BOX = 0x1800b4a80L;       // il2cpp_value_box
	private static final long RECT_CTOR = 0x1807720c0L;
	private static final long POINT_CTOR = 0x180856890L;
	private static final long DOCK_CTOR = 0x1807a8510L;

	private static final long CLASSES = 0x40000000L;   // fake classes, 0x800 apart
	private static final long STATICS = 0x48000000L;   // their static blocks, 0x400 apart
	private static final long STUBS = 0x50000000L;     // method table targets: class i slot n
	private static final long HEAP = 0x60000000L;
	private static final long STACK = 0x7f000000L;
	private static final long RETURN_TO = 0x7ffff000L;
	private static final long STRING_CLASS = 0x3ff00000L;

	private static final int SLOTS = 120;

	private EmulatorHelper emu;
	private long heap = HEAP;
	private final Map<Long, String> classNames = new HashMap<>();   // fake class -> name
	private final Map<Long, Integer> classIndex = new HashMap<>();
	private final Map<Long, String> stringNames = new HashMap<>();  // fake string -> literal
	// Game functions run as they are (pure arithmetic).
	private final Set<String> nativeNames = new HashSet<>(Arrays.asList(
		"app.Num$$lerpScale", "FUN_180034970"));
	private final List<long[]> objects = new ArrayList<>();          // address, size
	private Function ctor;
	private Function cctor;

	@Override
	protected void run() throws Exception {
		ctor = getFunctionAt(toAddr(CTOR));
		cctor = getFunctionAt(toAddr(CCTOR));
		emu = new EmulatorHelper(currentProgram);
		try {
			setUpSlots();
			emu.writeMemoryValue(toAddr(INIT_FLAG), 1, 1);
			// Layout's static values first.
			call(CCTOR, 0, 0, cctor);
			// The platform: kind = PlatformKind.DESKTOP (static 0), width/height 0.
			long kindClass = classFor("app.plat.PlatformKind_TypeInfo");
			long desktop = readLong(readLong(kindClass + 0xb8));
			long platform = alloc(classFor("app.plat.Platform_TypeInfo"), 0x40);
			emu.writeMemoryValue(toAddr(platform + 0x10), 8, desktop);
			long layout = alloc(classFor("Layout_TypeInfo"), 0x2c0);
			println("LAYOUT_OBJECT " + hex(layout));
			call(CTOR, layout, platform, ctor);
			dumpObjects();
		}
		finally {
			emu.dispose();
		}
	}

	// ---- set-up

	private void setUpSlots() throws Exception {
		int i = 0;
		int strings = 0;
		SymbolIterator it = currentProgram.getSymbolTable().getAllSymbols(false);
		while (it.hasNext()) {
			Symbol s = it.next();
			String name = s.getName();
			long slot = s.getAddress().getOffset();
			if (name.endsWith("_TypeInfo")) {
				long cls = CLASSES + (long) i * 0x800;
				long stat = STATICS + (long) i * 0x400;
				classNames.put(cls, name);
				classIndex.put(cls, i);
				emu.writeMemoryValue(toAddr(slot), 8, cls);
				emu.writeMemoryValue(toAddr(cls + 0xb8), 8, stat);
				emu.writeMemoryValue(toAddr(cls + 0xe0), 4, 1);
				i++;
			}
			else if (name.startsWith("StringLiteral_")) {
				long str = alloc(STRING_CLASS, 0x40);
				String text = "#" + name.substring("StringLiteral_".length());
				emu.writeMemoryValue(toAddr(str + 0x10), 4, text.length());
				for (int c = 0; c < text.length(); c++) {
					emu.writeMemoryValue(toAddr(str + 0x14 + 2 * c), 2, text.charAt(c));
				}
				stringNames.put(str, name);
				emu.writeMemoryValue(toAddr(slot), 8, str);
				strings++;
			}
		}
		println("fake classes " + i + ", strings " + strings);
	}

	// Fills a class's method table and static enum values the first time it is used.
	private final Set<Long> filled = new HashSet<>();

	private void fill(long cls) throws Exception {
		if (cls < CLASSES || cls >= STATICS || filled.contains(cls)) {
			return;
		}
		filled.add(cls);
		int index = classIndex.get(cls);
		for (int n = 0; n < SLOTS; n++) {
			emu.writeMemoryValue(toAddr(cls + 0x138 + 16L * n), 8, STUBS + index * 0x1000L + 16L * n);
		}
		long stat = readLong(cls + 0xb8);
		for (int k = 0; k < 64; k++) {
			if (readLong(stat + 8L * k) != 0) {
				continue; // written by a static constructor
			}
			long e = alloc(cls, 0x20);
			emu.writeMemoryValue(toAddr(e + 0x10), 4, k);
			emu.writeMemoryValue(toAddr(stat + 8L * k), 8, e);
		}
	}

	private long classFor(String name) throws Exception {
		for (Map.Entry<Long, String> e : classNames.entrySet()) {
			if (e.getValue().equals(name)) {
				fill(e.getKey());
				return e.getKey();
			}
		}
		throw new IllegalStateException("no class " + name);
	}

	private long alloc(long cls, int size) throws Exception {
		long at = heap;
		heap += (size + 0xf) & ~0xfL;
		heap += 0x10;
		for (int off = 0; off < size; off += 8) {
			emu.writeMemoryValue(toAddr(at + off), 8, 0);
		}
		emu.writeMemoryValue(toAddr(at), 8, cls);
		objects.add(new long[] { at, size });
		return at;
	}

	// ---- running

	private void call(long entry, long rcx, long rdx, Function body) throws Exception {
		emu.writeRegister(emu.getStackPointerRegister(), STACK);
		emu.writeMemoryValue(toAddr(STACK), 8, RETURN_TO);
		emu.writeRegister("RCX", rcx);
		emu.writeRegister("RDX", rdx);
		emu.writeRegister(emu.getPCRegister(), entry);
		long steps = 0;
		while (true) {
			long pc = emu.getExecutionAddress().getOffset();
			if (pc == RETURN_TO) {
				println("returned after " + steps + " steps");
				return;
			}
			if (pc >= STUBS && pc < HEAP) {
				virtualCall(pc);
				ret();
				continue;
			}
			if (!body.getBody().contains(toAddr(pc))) {
				Function f = getFunctionAt(toAddr(pc));
				String name = f == null ? "?" : f.getName();
				if (!nativeNames.contains(name) && !inNative(pc)) {
					directCall(pc, name);
					ret();
					continue;
				}
			}
			// Make sure classes read through slots are filled before use.
			preFill(pc);
			if (!emu.step(monitor)) {
				throw new IllegalStateException("step failed at " + hex(pc) + ": " + emu.getLastError());
			}
			steps++;
			if (steps > 2_000_000) {
				throw new IllegalStateException("too many steps");
			}
		}
	}

	// True when pc is inside one of the functions allowed to run as they are.
	private boolean inNative(long pc) {
		Function f = getFunctionContaining(toAddr(pc));
		if (f == null || f.getEntryPoint().getOffset() == pc) {
			return false;
		}
		return nativeNames.contains(f.getName());
	}

	// Before an instruction that loads a class slot, fill that class.
	private void preFill(long pc) throws Exception {
		Instruction ins = getInstructionAt(toAddr(pc));
		if (ins == null) {
			return;
		}
		for (Reference r : ins.getReferencesFrom()) {
			Symbol s = getSymbolAt(r.getToAddress());
			if (s != null && s.getName().endsWith("_TypeInfo")) {
				fill(readLong(r.getToAddress().getOffset()));
			}
		}
	}

	private void ret() throws Exception {
		long sp = emu.readRegister(emu.getStackPointerRegister()).longValue();
		long back = readLong(sp);
		emu.writeRegister(emu.getStackPointerRegister(), sp + 8);
		emu.writeRegister(emu.getPCRegister(), back);
	}

	private void directCall(long pc, String name) throws Exception {
		long rcx = reg("RCX");
		long rdx = reg("RDX");
		long r8 = reg("R8");
		long r9 = reg("R9");
		long sp = reg("RSP");
		if (pc == ALLOC) {
			fill(rcx);
			long obj = alloc(rcx, 0x100);
			setRax(obj);
			println("alloc " + cname(rcx) + " -> " + hex(obj));
		}
		else if (pc == BOX) {
			fill(rcx);
			long box = alloc(rcx, 0x20);
			emu.writeMemoryValue(toAddr(box + 0x10), 8, readLong(rdx));
			setRax(box);
		}
		else if (pc == RECT_CTOR) {
			long[] a = { rdx, r8, r9, readLong(sp + 0x28) };
			StringBuilder line = new StringBuilder("Rect " + hex(rcx) + " =");
			for (int k = 0; k < 4; k++) {
				double v = unbox(a[k]);
				emu.writeMemoryValue(toAddr(rcx + 0x10 + 8L * k), 8, Double.doubleToRawLongBits(v));
				line.append(" ").append(v);
			}
			println(line.toString());
		}
		else if (pc == POINT_CTOR) {
			double x = xmm("XMM1");
			double y = xmm("XMM2");
			emu.writeMemoryValue(toAddr(rcx + 0x10), 8, Double.doubleToRawLongBits(x));
			emu.writeMemoryValue(toAddr(rcx + 0x18), 8, Double.doubleToRawLongBits(y));
			println("Point " + hex(rcx) + " = " + x + " " + y);
		}
		else if (pc == DOCK_CTOR) {
			long clip = readLong(sp + 0x28);
			emu.writeMemoryValue(toAddr(rcx + 0x10), 8, rdx);
			emu.writeMemoryValue(toAddr(rcx + 0x18), 8, r8);
			emu.writeMemoryValue(toAddr(rcx + 0x28), 8, r9);
			emu.writeMemoryValue(toAddr(rcx + 0x20), 8, clip);
			println("DockPoint " + hex(rcx) + " entry " + hex(rdx) + " home " + hex(r8)
				+ " clamp " + hex(r9) + " clip " + hex(clip));
		}
		else if (name.equals("floor") || name.equals("ceil")) {
			double v = xmm("XMM0");
			double r = name.equals("floor") ? Math.floor(v) : Math.ceil(v);
			emu.writeRegister("XMM0", java.math.BigInteger.valueOf(Double.doubleToRawLongBits(r))
				.and(new java.math.BigInteger("ffffffffffffffff", 16)));
		}
		else if (name.equals("FUN_1800029d0") || name.equals("FUN_180002f80")
			|| name.equals("thunk_FUN_1800f0a30")) {
			setRax(rcx); // casts: assume they succeed
		}
		else if (name.startsWith("thunk_FUN_180125b00") || name.startsWith("thunk_FUN_1800eeee0")
			|| name.equals("il2cpp_runtime_class_init")) {
			setRax(0);
		}
		else if (name.equals("Std$$string") || name.equals("haxe.lang.Runtime$$concat")
			|| name.equals("haxe.lang.Runtime$$toString")) {
			setRax(emptyString()); // only used for the log line
		}
		else if (name.equals("FUN_180126c60")) { // new array (type, length)
			long arr = alloc(rcx, 0x20 + 8 * (int) Math.max(rdx, 0) + 8);
			emu.writeMemoryValue(toAddr(arr + 0x18), 8, rdx);
			setRax(arr);
		}
		else if (name.startsWith("System.Runtime.CompilerServices.RuntimeHelpers$$InitializeArray")
			|| name.startsWith("Trace") || name.contains("customPrint") || name.contains("haxe.Log")) {
			setRax(0);
		}
		else if (name.equals("FUN_1801271d0") || pc == 0) {
			throw new IllegalStateException("null reference / bad call at " + hex(pc)
				+ " return address " + hex(readLong(sp)));
		}
		else {
			println("CALL " + name + " @" + hex(pc) + " rcx " + hex(rcx) + " rdx " + hex(rdx)
				+ " r8 " + hex(r8) + " -> 0");
			setRax(0);
		}
	}

	private void virtualCall(long pc) throws Exception {
		long off = pc - STUBS;
		int index = (int) (off / 0x1000);
		int slot = (int) ((off % 0x1000) / 16);
		String cls = "?";
		for (Map.Entry<Long, Integer> e : classIndex.entrySet()) {
			if (e.getValue() == index) {
				cls = classNames.get(e.getKey());
			}
		}
		long rcx = reg("RCX");
		long rdx = reg("RDX");
		long r8 = reg("R8");
		println("VCALL " + cls + " slot " + slot + " this " + hex(rcx) + " rdx " + describe(rdx)
			+ " r8 " + describe(r8) + " xmm1 " + xmm("XMM1") + " -> 0");
		setRax(0);
	}

	private long empty = 0;

	private long emptyString() throws Exception {
		if (empty == 0) {
			empty = alloc(STRING_CLASS, 0x20);
		}
		return empty;
	}

	// ---- output

	private void dumpObjects() throws Exception {
		for (long[] o : objects) {
			long at = o[0];
			long cls = readLong(at);
			if (cls == STRING_CLASS) {
				continue;
			}
			StringBuilder line = new StringBuilder("OBJ " + hex(at) + " " + cname(cls));
			for (int off = 0x10; off < o[1]; off += 8) {
				line.append(" ").append(String.format("%x", readLong(at + off)));
			}
			println(line.toString());
		}
	}

	private String describe(long v) {
		String s = stringNames.get(v);
		return s != null ? s : hex(v);
	}

	private String cname(long cls) {
		if (cls == STRING_CLASS) {
			return "String";
		}
		String n = classNames.get(cls);
		return n == null ? hex(cls) : n;
	}

	private double unbox(long box) throws Exception {
		if (box == 0) {
			return 0.0;
		}
		String type = cname(readLong(box));
		long raw = readLong(box + 0x10);
		if (type.equals("int_TypeInfo")) {
			return (int) raw;
		}
		if (type.equals("double_TypeInfo")) {
			return Double.longBitsToDouble(raw);
		}
		println("unbox of " + type + " " + hex(box));
		return Double.longBitsToDouble(raw);
	}

	private long readLong(long at) throws Exception {
		byte[] b = emu.readMemory(toAddr(at), 8);
		long v = 0;
		for (int k = 7; k >= 0; k--) {
			v = (v << 8) | (b[k] & 0xff);
		}
		return v;
	}

	private long reg(String name) {
		return emu.readRegister(name).longValue();
	}

	private double xmm(String name) {
		long bits = emu.readRegister(name).longValue(); // low 64 bits
		return Double.longBitsToDouble(bits);
	}

	private void setRax(long v) {
		emu.writeRegister("RAX", v);
	}

	private static String hex(long v) {
		return "0x" + Long.toHexString(v);
	}
}
