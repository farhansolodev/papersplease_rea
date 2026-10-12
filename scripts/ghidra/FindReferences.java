// Prints which functions refer to the given addresses (code or data).
//
// Headless use:
//   analyzeHeadless <project dir> <project name> -process GameAssembly.dll
//     -noanalysis -readOnly -scriptPath scripts\ghidra
//     -postScript FindReferences.java 0xADDRESS...
//@category IL2CPP

import java.util.Map;
import java.util.TreeMap;

import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.symbol.Reference;

public class FindReferences extends GhidraScript {

	@Override
	protected void run() throws Exception {
		for (String arg : getScriptArgs()) {
			Address target = toAddr(arg);
			// function entry -> number of references from inside it
			Map<String, Integer> callers = new TreeMap<>();
			int outside = 0;
			for (Reference reference : getReferencesTo(target)) {
				Function function = getFunctionContaining(reference.getFromAddress());
				if (function == null) {
					outside++;
					continue;
				}
				callers.merge(function.getEntryPoint() + "  " + function.getName(), 1, Integer::sum);
			}
			println("references to " + arg + ": " + callers.size() + " functions, " + outside +
				" from outside any function");
			for (Map.Entry<String, Integer> caller : callers.entrySet()) {
				println("  " + caller.getKey() + "  x" + caller.getValue());
			}
		}
	}
}
