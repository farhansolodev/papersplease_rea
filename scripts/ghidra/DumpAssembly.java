// Prints the machine instructions of the given functions, with any numeric
// constant they read from the program's data shown as a double. For settling
// details the decompiler drops.
//
// Headless use:
//   analyzeHeadless <project dir> <project name> -process GameAssembly.dll
//     -noanalysis -readOnly -scriptPath scripts\ghidra
//     -postScript DumpAssembly.java 0xFUNCTION_ADDRESS...
//@category IL2CPP

import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.mem.Memory;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.Symbol;

public class DumpAssembly extends GhidraScript {

	@Override
	protected void run() throws Exception {
		Memory memory = currentProgram.getMemory();
		for (String arg : getScriptArgs()) {
			Function function = getFunctionAt(toAddr(arg));
			if (function == null) {
				println("no function at " + arg);
				continue;
			}
			println("assembly of " + function.getName() + ":");
			for (Instruction instruction : currentProgram.getListing()
					.getInstructions(function.getBody(), true)) {
				StringBuilder line = new StringBuilder("  " + instruction.getAddress() + "  " + instruction);
				for (Reference reference : instruction.getReferencesFrom()) {
					Address target = reference.getToAddress();
					Symbol symbol = getSymbolAt(target);
					if (symbol != null) {
						line.append("   ; ").append(symbol.getName());
					}
					if (reference.getReferenceType().isRead() && memory.contains(target)) {
						try {
							double value = Double.longBitsToDouble(memory.getLong(target));
							line.append("   ; as double: ").append(value);
						}
						catch (Exception e) {
							// not readable as 8 bytes; nothing to add
						}
					}
				}
				println(line.toString());
			}
		}
	}
}
