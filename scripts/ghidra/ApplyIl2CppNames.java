// Applies the names recovered by Il2CppDumper (script.json) to the current
// Ghidra program: method names, type/method metadata pointers and string
// literals. Struct layouts from il2cpp.h are not applied.
//
// Headless use:
//   analyzeHeadless <project dir> <project name> -process GameAssembly.dll
//     -noanalysis -scriptPath scripts\ghidra
//     -postScript ApplyIl2CppNames.java <path to script.json>
//@category IL2CPP

import java.io.FileReader;
import java.util.HashMap;
import java.util.Map;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;

import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.CodeUnit;
import ghidra.program.model.listing.Function;
import ghidra.program.model.symbol.SourceType;

public class ApplyIl2CppNames extends GhidraScript {

	private static final int MAX_ALIASES_IN_COMMENT = 8;

	@Override
	protected void run() throws Exception {
		String[] args = getScriptArgs();
		if (args.length < 1) {
			throw new IllegalArgumentException("usage: ApplyIl2CppNames.java <script.json>");
		}

		JsonObject root;
		try (FileReader reader = new FileReader(args[0])) {
			root = JsonParser.parseReader(reader).getAsJsonObject();
		}

		applyMethods(root.getAsJsonArray("ScriptMethod"));
		applyLabels(root.getAsJsonArray("ScriptMetadata"), "Name", "Signature");
		applyLabels(root.getAsJsonArray("ScriptMetadataMethod"), "Name", null);
		applyStrings(root.getAsJsonArray("ScriptString"));
	}

	private Address rva(JsonObject entry) {
		return currentProgram.getImageBase().add(entry.get("Address").getAsLong());
	}

	// Ghidra symbol names may not contain whitespace.
	private static String clean(String name) {
		return name.replaceAll("\\s+", "_");
	}

	private void applyMethods(JsonArray methods) throws Exception {
		// Generic methods share one body, so several names can map to one address.
		Map<Address, StringBuilder> aliases = new HashMap<>();
		Map<Address, Integer> aliasCounts = new HashMap<>();
		int named = 0, created = 0, failed = 0;

		for (JsonElement element : methods) {
			monitor.checkCancelled();
			JsonObject method = element.getAsJsonObject();
			Address address = rva(method);
			String name = method.get("Name").getAsString();

			int seen = aliasCounts.merge(address, 1, Integer::sum);
			if (seen > 1) {
				if (seen <= MAX_ALIASES_IN_COMMENT) {
					aliases.get(address).append("\nalso: ").append(name);
				}
				continue;
			}

			Function function = getFunctionAt(address);
			if (function == null) {
				disassemble(address);
				function = createFunction(address, null);
				if (function != null) {
					created++;
				}
			}
			if (function == null) {
				failed++;
				aliases.put(address, new StringBuilder());
				continue;
			}

			function.setName(clean(name), SourceType.USER_DEFINED);
			named++;
			aliases.put(address,
				new StringBuilder(name).append('\n').append(method.get("Signature").getAsString()));
		}

		for (Map.Entry<Address, StringBuilder> entry : aliases.entrySet()) {
			if (entry.getValue().length() == 0) {
				continue;
			}
			int extra = aliasCounts.get(entry.getKey()) - MAX_ALIASES_IN_COMMENT;
			if (extra > 0) {
				entry.getValue().append("\n(+").append(extra).append(" more names)");
			}
			setPlateComment(entry.getKey(), entry.getValue().toString());
		}

		println("methods: " + methods.size() + " entries, " + named + " functions named, " +
			created + " functions created, " + failed + " addresses with no function");
	}

	private void applyLabels(JsonArray entries, String nameKey, String commentKey)
			throws Exception {
		int labelled = 0;
		for (JsonElement element : entries) {
			monitor.checkCancelled();
			JsonObject entry = element.getAsJsonObject();
			Address address = rva(entry);
			createLabel(address, clean(entry.get(nameKey).getAsString()), true,
				SourceType.USER_DEFINED);
			if (commentKey != null && entry.has(commentKey) && !entry.get(commentKey).isJsonNull()) {
				setEOLComment(address, entry.get(commentKey).getAsString());
			}
			labelled++;
		}
		println("labels: " + labelled + " applied");
	}

	private void applyStrings(JsonArray strings) throws Exception {
		int index = 0;
		for (JsonElement element : strings) {
			monitor.checkCancelled();
			JsonObject entry = element.getAsJsonObject();
			Address address = rva(entry);
			createLabel(address, "StringLiteral_" + index, true, SourceType.USER_DEFINED);
			currentProgram.getListing().setComment(address, CodeUnit.EOL_COMMENT,
				entry.get("Value").getAsString());
			index++;
		}
		println("string literals: " + index + " labelled");
	}
}
