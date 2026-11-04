// Decompiles functions whose name starts with a given prefix (or that sit at a
// given 0x address) and writes them into one text file.
//
// Headless use:
//   analyzeHeadless <project dir> <project name> -process GameAssembly.dll
//     -noanalysis -readOnly -scriptPath scripts\ghidra
//     -postScript DecompileFunctions.java <output file> <prefix or 0xADDRESS>...
//
// The time limit per function is 120 s; the environment variable
// PP_DECOMPILE_TIMEOUT (seconds) raises it, and with it the decompiler's
// output limit, for the few functions too big for the default (the Booth
// constructor, 2026-11-04).
//
// A selector of the form @<file> reads selectors from that file, one per line
// (blank lines and lines starting with # are skipped). Use it for long lists
// of addresses: see game_function_lists.py.
//@category IL2CPP

import java.io.PrintWriter;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.List;

import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileOptions;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.Function;

public class DecompileFunctions extends GhidraScript {

	private static final int DEFAULT_TIMEOUT_SECONDS = 120;

	@Override
	protected void run() throws Exception {
		String[] args = getScriptArgs();
		if (args.length < 2) {
			throw new IllegalArgumentException(
				"usage: DecompileFunctions.java <output file> <prefix, 0xADDRESS or @file>...");
		}

		List<String> selectors = new ArrayList<>();
		for (int i = 1; i < args.length; i++) {
			if (!args[i].startsWith("@")) {
				selectors.add(args[i]);
				continue;
			}
			for (String line : Files.readAllLines(Paths.get(args[i].substring(1)),
				StandardCharsets.UTF_8)) {
				line = line.trim();
				if (!line.isEmpty() && !line.startsWith("#")) {
					selectors.add(line);
				}
			}
		}

		List<Function> selected = new ArrayList<>();
		for (String selector : selectors) {
			if (selector.startsWith("0x")) {
				Function function = getFunctionAt(toAddr(selector));
				if (function != null) {
					selected.add(function);
				}
				else {
					println("no function at " + selector);
				}
				continue;
			}
			for (Function function : currentProgram.getFunctionManager().getFunctions(true)) {
				if (function.getName().startsWith(selector)) {
					selected.add(function);
				}
			}
		}

		int timeout = DEFAULT_TIMEOUT_SECONDS;
		String env = System.getenv("PP_DECOMPILE_TIMEOUT");
		DecompInterface decompiler = new DecompInterface();
		if (env != null && !env.isEmpty()) {
			timeout = Integer.parseInt(env);
			DecompileOptions options = new DecompileOptions();
			options.setMaxPayloadMBytes(512);
			options.setMaxInstructions(200000);
			decompiler.setOptions(options);
		}
		decompiler.openProgram(currentProgram);
		int written = 0, failed = 0;
		try (PrintWriter out = new PrintWriter(args[0], StandardCharsets.UTF_8)) {
			for (Function function : selected) {
				monitor.checkCancelled();
				DecompileResults results =
					decompiler.decompileFunction(function, timeout, monitor);
				out.println("// ===== " + function.getName() + " @ " + function.getEntryPoint());
				if (results.decompileCompleted()) {
					out.println(results.getDecompiledFunction().getC());
					written++;
				}
				else {
					out.println("// decompile failed: " + results.getErrorMessage());
					failed++;
				}
			}
		}
		finally {
			decompiler.dispose();
		}
		println("selected " + selected.size() + ", decompiled " + written + ", failed " + failed +
			" -> " + args[0]);
	}
}
