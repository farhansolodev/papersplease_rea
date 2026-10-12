// Runs the game's own machine code for String.GetHashCode and the hash mixing
// in haxe.ds.StringMap.lookup in Ghidra's emulator, as ground truth for
// scripts/reference/haxemap.py.
//
// It builds a fake string (class record with slot 2 pointing at the real
// GetHashCode) and a fake StringMap, calls the real StringMap.lookup, and
// stops at two breakpoints: right after GetHashCode returns (raw .NET hash in
// EAX) and right after the mixing (Haxe hash in R14D). Lookup never runs past
// the second breakpoint.
//
// Headless use:
//   analyzeHeadless <project dir> <project name> -process GameAssembly.dll
//     -noanalysis -readOnly -scriptPath scripts\ghidra
//     -postScript EmulateStringHash.java <string>...
// With no strings given, a built-in list is used.
//@category IL2CPP

import ghidra.app.emulator.EmulatorHelper;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;

public class EmulateStringHash extends GhidraScript {

	private static final long LOOKUP = 0x1807f6230L;        // haxe.ds.StringMap.lookup(this, key)
	private static final long GET_HASH_CODE = 0x180738ba0L; // System.String.GetHashCode(this)
	private static final long AFTER_GET_HASH = 0x1807f629cL; // first instruction after the call
	private static final long AFTER_MIX = 0x1807f62ffL;      // final Haxe hash is in R14D here

	// Scratch addresses outside the program's own memory.
	private static final long STRING = 0x20000000L;
	private static final long CLASS = 0x20010000L;
	private static final long MAP = 0x20020000L;
	private static final long STACK = 0x2ff00000L;
	private static final long RETURN_TO = 0x2ffff000L;

	// Il2CppClass method table: starts at 0x138, 16 bytes per slot.
	private static final long SLOT_2 = 0x138 + 2 * 16;

	private static final String[] DEFAULTS = {
		"", "a", "ab", "abc", "Passport/Name", "VaccineCert/VaccineDates",
		"VaccineCert/VaccineDrugs", "Traveler/Nationality", "M0:0", "aeiou",
		"Über ß", "Rules/RuleArstotzkaOnly"
	};

	private EmulatorHelper emulator;

	@Override
	protected void run() throws Exception {
		String[] args = getScriptArgs();
		String[] inputs = args.length > 0 ? args : DEFAULTS;

		emulator = new EmulatorHelper(currentProgram);
		try {
			emulator.setBreakpoint(toAddr(AFTER_GET_HASH));
			emulator.setBreakpoint(toAddr(AFTER_MIX));
			emulator.setBreakpoint(toAddr(RETURN_TO));
			for (String text : inputs) {
				writeString(text);
				emulator.writeMemoryValue(toAddr(CLASS + SLOT_2), 8, GET_HASH_CODE);
				emulator.writeMemoryValue(toAddr(CLASS + SLOT_2 + 8), 8, 0);
				for (long offset = 0; offset < 0x48; offset += 8) {
					emulator.writeMemoryValue(toAddr(MAP + offset), 8, 0);
				}
				emulator.writeMemoryValue(toAddr(MAP + 0x28), 4, 4); // nBuckets

				emulator.writeRegister(emulator.getStackPointerRegister(), STACK);
				emulator.writeMemoryValue(toAddr(STACK), 8, RETURN_TO);
				emulator.writeRegister("RCX", MAP);
				emulator.writeRegister("RDX", STRING);
				emulator.writeRegister(emulator.getPCRegister(), LOOKUP);

				run(AFTER_GET_HASH);
				int raw = emulator.readRegister("EAX").intValue();
				run(AFTER_MIX);
				int mixed = emulator.readRegister("R14D").intValue();
				println(String.format("%-28s raw %08x haxe %08x", quote(text), raw, mixed));
			}
		}
		finally {
			emulator.dispose();
		}
	}

	private void writeString(String text) throws Exception {
		emulator.writeMemoryValue(toAddr(STRING), 8, CLASS);
		emulator.writeMemoryValue(toAddr(STRING + 8), 8, 0);
		emulator.writeMemoryValue(toAddr(STRING + 0x10), 4, text.length());
		long at = STRING + 0x14;
		for (int i = 0; i < text.length(); i++, at += 2) {
			emulator.writeMemoryValue(toAddr(at), 2, text.charAt(i));
		}
		emulator.writeMemoryValue(toAddr(at), 4, 0); // the terminating NUL (and padding)
	}

	private void run(long expected) throws Exception {
		emulator.run(monitor);
		Address stopped = emulator.getExecutionAddress();
		if (stopped.getOffset() != expected) {
			throw new IllegalStateException(
				"emulation stopped at " + stopped + ": " + emulator.getLastError());
		}
	}

	private static String quote(String text) {
		StringBuilder out = new StringBuilder("\"");
		for (char c : text.toCharArray()) {
			out.append(c < 128 ? String.valueOf(c) : String.format("\\u%04x", (int) c));
		}
		return out.append('"').toString();
	}
}
