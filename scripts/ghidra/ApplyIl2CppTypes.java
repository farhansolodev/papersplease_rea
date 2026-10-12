// Loads the struct layouts from Il2CppDumper's il2cpp.h into the current
// Ghidra program and applies typed method signatures from script.json, so the
// decompiler shows field names instead of raw offsets.
//
// Headless use (run "types" first, then "signatures"):
//   -postScript ApplyIl2CppTypes.java types <il2cpp.h>
//   -postScript ApplyIl2CppTypes.java signatures <script.json>
//   -postScript ApplyIl2CppTypes.java show <struct name>     (read-only check)
//@category IL2CPP

import java.io.FileReader;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.HashSet;
import java.util.Set;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;

import ghidra.app.cmd.function.ApplyFunctionSignatureCmd;
import ghidra.app.cmd.function.FunctionRenameOption;
import ghidra.app.script.GhidraScript;
import ghidra.app.services.DataTypeManagerService;
import ghidra.app.util.cparser.C.CParser;
import ghidra.app.util.cparser.C.CParserUtils;
import ghidra.program.model.address.Address;
import ghidra.program.model.data.DataType;
import ghidra.program.model.data.DataTypeComponent;
import ghidra.program.model.data.DataTypeManager;
import ghidra.program.model.data.FunctionDefinitionDataType;
import ghidra.program.model.data.Structure;
import ghidra.program.model.symbol.SourceType;

public class ApplyIl2CppTypes extends GhidraScript {

	// il2cpp.h assumes these exist; Ghidra's C parser does not define them.
	private static final String PRELUDE =
		"typedef unsigned __int8 uint8_t;\n" +
		"typedef unsigned __int16 uint16_t;\n" +
		"typedef unsigned __int32 uint32_t;\n" +
		"typedef unsigned __int64 uint64_t;\n" +
		"typedef __int8 int8_t;\n" +
		"typedef __int16 int16_t;\n" +
		"typedef __int32 int32_t;\n" +
		"typedef __int64 int64_t;\n" +
		"typedef __int64 intptr_t;\n" +
		"typedef unsigned __int64 uintptr_t;\n" +
		"typedef unsigned __int64 size_t;\n";

	@Override
	protected void run() throws Exception {
		String[] args = getScriptArgs();
		if (args.length != 2) {
			throw new IllegalArgumentException(
				"usage: ApplyIl2CppTypes.java types <il2cpp.h> | signatures <script.json> | show <struct>");
		}
		switch (args[0]) {
			case "types":
				importTypes(args[1]);
				break;
			case "signatures":
				applySignatures(args[1]);
				break;
			case "show":
				show(args[1]);
				break;
			default:
				throw new IllegalArgumentException("unknown mode: " + args[0]);
		}
	}

	private void importTypes(String headerPath) throws Exception {
		String header = new String(Files.readAllBytes(Paths.get(headerPath)), StandardCharsets.UTF_8);
		// The header uses C++ inheritance ("struct A : B {"), which the C parser
		// rejects. A base struct is laid out first, so it becomes a first member.
		header = header.replaceAll(": (\\w+) \\{", "{\n\t$1 super;");

		DataTypeManager dtm = currentProgram.getDataTypeManager();
		int before = dtm.getDataTypeCount(true);
		CParser parser = new CParser(dtm, true, null);
		parser.parse(PRELUDE + header);
		String messages = parser.getParseMessages();
		if (messages != null && !messages.isBlank()) {
			println("parser messages (first 2000 chars): " +
				messages.substring(0, Math.min(2000, messages.length())));
		}
		println("types: parse succeeded=" + parser.didParseSucceed() + ", data types " + before +
			" -> " + dtm.getDataTypeCount(true));
	}

	private void applySignatures(String jsonPath) throws Exception {
		JsonObject root;
		try (FileReader reader = new FileReader(jsonPath)) {
			root = JsonParser.parseReader(reader).getAsJsonObject();
		}
		JsonArray methods = root.getAsJsonArray("ScriptMethod");

		Set<Address> done = new HashSet<>();
		int applied = 0, parseFailed = 0, applyFailed = 0, printed = 0;
		for (JsonElement element : methods) {
			monitor.checkCancelled();
			JsonObject method = element.getAsJsonObject();
			Address address = currentProgram.getImageBase().add(method.get("Address").getAsLong());
			// Shared generic bodies have several signatures; the first one wins.
			if (!done.add(address)) {
				continue;
			}
			String signature = method.get("Signature").getAsString();
			if (signature.endsWith(";")) {
				signature = signature.substring(0, signature.length() - 1);
			}
			FunctionDefinitionDataType definition;
			try {
				definition = CParserUtils.parseSignature((DataTypeManagerService) null,
					currentProgram, signature, false);
			}
			catch (Exception e) {
				definition = null;
			}
			if (definition == null) {
				parseFailed++;
				if (printed++ < 10) {
					println("could not parse: " + signature);
				}
				continue;
			}
			ApplyFunctionSignatureCmd command = new ApplyFunctionSignatureCmd(address, definition,
				SourceType.USER_DEFINED, false, FunctionRenameOption.NO_CHANGE);
			if (command.applyTo(currentProgram, monitor)) {
				applied++;
			}
			else {
				applyFailed++;
			}
		}
		println("signatures: " + done.size() + " functions, " + applied + " applied, " +
			parseFailed + " not parsed, " + applyFailed + " not applied");
	}

	private void show(String structName) {
		DataType type = null;
		java.util.Iterator<DataType> all = currentProgram.getDataTypeManager().getAllDataTypes();
		while (all.hasNext()) {
			DataType candidate = all.next();
			if (candidate.getName().equals(structName)) {
				type = candidate;
				break;
			}
		}
		if (!(type instanceof Structure)) {
			println("no struct named " + structName);
			return;
		}
		println(structName + " size 0x" + Integer.toHexString(type.getLength()));
		printFields((Structure) type, 0, "");
	}

	private void printFields(Structure structure, int base, String prefix) {
		for (DataTypeComponent component : structure.getDefinedComponents()) {
			int offset = base + component.getOffset();
			String name = prefix + component.getFieldName();
			DataType fieldType = component.getDataType();
			if (fieldType instanceof Structure) {
				printFields((Structure) fieldType, offset, name + ".");
			}
			else {
				println(String.format("  0x%02X  %s  %s", offset, fieldType.getName(), name));
			}
		}
	}
}
