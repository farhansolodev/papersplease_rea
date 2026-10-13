// Finds instructions that WRITE to a class's static values.
//
// IL2CPP code reaches a class's static values by loading the class record
// (X_TypeInfo), then the pointer at +0xb8, then the value at its offset. This
// script looks at every reference to the class record and prints the memory
// writes in the instructions that follow (a short window), so a write to a
// given static value can be spotted by its offset.
//
// Headless use:
//   analyzeHeadless <project dir> <project name> -process GameAssembly.dll
//     -noanalysis -readOnly -scriptPath scripts\ghidra
//     -postScript FindStaticWrites.java 0xTYPEINFO_ADDRESS [window]
//@category IL2CPP

import java.util.Map;
import java.util.TreeMap;

import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.symbol.Reference;

public class FindStaticWrites extends GhidraScript {

	@Override
	protected void run() throws Exception {
		String[] args = getScriptArgs();
		Address target = toAddr(args[0]);
		int window = args.length > 1 ? Integer.parseInt(args[1]) : 14;
		int references = 0;
		Map<String, String> found = new TreeMap<>();
		for (Reference reference : getReferencesTo(target)) {
			Function function = getFunctionContaining(reference.getFromAddress());
			if (function == null) {
				continue;
			}
			references++;
			Instruction instruction = getInstructionAt(reference.getFromAddress());
			for (int i = 0; i < window && instruction != null; i++) {
				instruction = instruction.getNext();
				if (instruction == null) {
					break;
				}
				String text = instruction.toString();
				// A write has the memory operand first: "MOV byte ptr [RAX + 0x1],..."
				if (text.startsWith("MOV") && text.matches("MOV\\w* \\w+ ptr \\[[^\\]]*\\],.*")) {
					found.put(instruction.getAddress() + "  " + function.getName(), text);
				}
				if (text.startsWith("RET") || text.startsWith("JMP")) {
					break;
				}
			}
		}
		println("references to " + args[0] + " inside functions: " + references +
			"; memory writes within " + window + " instructions after one: " + found.size());
		for (Map.Entry<String, String> entry : found.entrySet()) {
			println("  " + entry.getKey() + "  " + entry.getValue());
		}
	}
}
