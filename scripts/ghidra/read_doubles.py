"""Print the 8-byte number stored at each given address of a Windows DLL.

Usage: python -I read_doubles.py <dll> 0xADDRESS [0xADDRESS ...]

Addresses are the ones Ghidra shows (image base included). Used to read
numeric constants the decompiler shows only as DAT_... names.
"""
import struct
import sys

data = open(sys.argv[1], "rb").read()
pe = struct.unpack_from("<I", data, 0x3C)[0]
sections = struct.unpack_from("<H", data, pe + 6)[0]
optional_size = struct.unpack_from("<H", data, pe + 20)[0]
image_base = struct.unpack_from("<Q", data, pe + 24 + 24)[0]
table = pe + 24 + optional_size
for text in sys.argv[2:]:
    rva = int(text, 16) - image_base
    for i in range(sections):
        name, vsize, vaddr, rsize, raw = struct.unpack_from("<8sIIII", data, table + 40 * i)
        if vaddr <= rva < vaddr + max(vsize, rsize):
            offset = raw + rva - vaddr
            print("%s [%s] double=%r int32=%d" % (text, name.rstrip(b"\0").decode(),
                                                  struct.unpack_from("<d", data, offset)[0],
                                                  struct.unpack_from("<i", data, offset)[0]))
            break
    else:
        print(text, "not in any section")
