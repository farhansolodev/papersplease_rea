// Lists, in instruction order, every string literal a function refers to.
// Useful when the decompiler drops a string argument from a call.
//
// Headless use:
//   analyzeHeadless <project dir> <project name> -process GameAssembly.dll
//     -noanalysis -readOnly -scriptPath scripts\ghidra
//     -postScript ListStringUses.java 0xFUNCTION_ADDRESS...
//@category IL2CPP

import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.Symbol;

public class ListStringUses extends GhidraScript {

	@Override
	protected void run() throws Exception {
		for (String arg : getScriptArgs()) {
			Function function = getFunctionAt(toAddr(arg));
			if (function == null) {
				println("no function at " + arg);
				continue;
			}
			println("string uses in " + function.getName() + ":");
			for (Instruction instruction : currentProgram.getListing()
					.getInstructions(function.getBody(), true)) {
				for (Reference reference : instruction.getReferencesFrom()) {
					Symbol symbol = getSymbolAt(reference.getToAddress());
					if (symbol != null && symbol.getName().startsWith("StringLiteral_")) {
						println("  " + instruction.getAddress() + "  " + symbol.getName());
					}
				}
			}
		}
	}
}
