// Runs the game's own machine code for app.Rand in Ghidra's emulator and
// prints the results, as ground truth for scripts/reference/rand.py.
//
// It builds a fake Rand object and a fake class record whose method table
// points slot 25 at the real nextInt, calls the real constructor with a seed,
// then calls the real nextInt repeatedly.
//
// Headless use:
//   analyzeHeadless <project dir> <project name> -process GameAssembly.dll
//     -noanalysis -readOnly -scriptPath scripts\ghidra
//     -postScript EmulateRand.java <count> <seed>...
//@category IL2CPP

import ghidra.app.emulator.EmulatorHelper;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;

public class EmulateRand extends GhidraScript {

	private static final long CONSTRUCTOR = 0x18091c340L; // app.Rand.__hx_ctor(this, seed)
	private static final long NEXT_INT = 0x18091cdc0L;    // app.Rand.nextInt(this)

	// Scratch addresses outside the program's own memory.
	private static final long OBJECT = 0x20000000L;
	private static final long CLASS = 0x20010000L;
	private static final long STACK = 0x2ff00000L;
	private static final long RETURN_TO = 0x2ffff000L;

	// Il2CppClass method table: starts at 0x138, 16 bytes per slot.
	private static final long SLOT_25 = 0x138 + 25 * 16;

	private EmulatorHelper emulator;

	@Override
	protected void run() throws Exception {
		String[] args = getScriptArgs();
		int count = Integer.parseInt(args[0]);

		emulator = new EmulatorHelper(currentProgram);
		try {
			emulator.setBreakpoint(toAddr(RETURN_TO));
			for (int i = 1; i < args.length; i++) {
				int seed = Integer.parseInt(args[i]);

				emulator.writeMemoryValue(toAddr(OBJECT), 8, CLASS);
				emulator.writeMemoryValue(toAddr(OBJECT + 8), 8, 0);
				emulator.writeMemoryValue(toAddr(OBJECT + 0x10), 8, 0);
				emulator.writeMemoryValue(toAddr(OBJECT + 0x18), 8, 0);
				emulator.writeMemoryValue(toAddr(CLASS + SLOT_25), 8, NEXT_INT);
				emulator.writeMemoryValue(toAddr(CLASS + SLOT_25 + 8), 8, 0);

				call(CONSTRUCTOR, OBJECT, seed & 0xffffffffL);
				StringBuilder line = new StringBuilder("seed " + seed + " state");
				for (int offset = 0x10; offset <= 0x1c; offset += 4) {
					line.append(String.format(" %08x", readInt(OBJECT + offset)));
				}
				line.append(" |");
				for (int n = 0; n < count; n++) {
					call(NEXT_INT, OBJECT, 0);
					line.append(' ').append(emulator.readRegister("EAX").intValue());
				}
				println(line.toString());
			}
		}
		finally {
			emulator.dispose();
		}
	}

	private void call(long function, long firstArgument, long secondArgument) throws Exception {
		emulator.writeRegister(emulator.getStackPointerRegister(), STACK);
		emulator.writeMemoryValue(toAddr(STACK), 8, RETURN_TO);
		emulator.writeRegister("RCX", firstArgument);
		emulator.writeRegister("RDX", secondArgument);
		emulator.writeRegister(emulator.getPCRegister(), function);
		emulator.run(monitor);
		Address stopped = emulator.getExecutionAddress();
		if (stopped.getOffset() != RETURN_TO) {
			throw new IllegalStateException(
				"emulation stopped at " + stopped + ": " + emulator.getLastError());
		}
	}

	private int readInt(long address) {
		byte[] bytes = emulator.readMemory(toAddr(address), 4);
		return (bytes[0] & 0xff) | (bytes[1] & 0xff) << 8 | (bytes[2] & 0xff) << 16 |
			(bytes[3] & 0xff) << 24;
	}
}
