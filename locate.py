import sys
import os
import glob
import struct

code = '';
addrdb = {};
base = 0x00100000;

def findNearestSTMFD(code, pos):
	pos = (pos // 4) * 4;
	term = pos - 0x1000;
	if term < 0:
		term = 0;
	while (pos >= term) :
		if (code[pos + 2: pos + 4] == '\x2d\xe9'):
			return pos;
		pos -= 4;
	return 0;
	
def findFunction(code, sig):
	global base;
	
	t = code.find(sig);
	if (t == -1):
		return 0;
	return base + findNearestSTMFD(code, t);

def save(k, v):
	global addrdb, base;
	if (not addrdb.has_key(k)):
		addrdb[k] = '0';
	if (v != 0):
		addrdb[k] = hex(v);

def findAll(code, sig):
	r = [];
	off = 0;
	while True:
		t = code.find(sig, off);
		if (t == -1):
			return r;
		off = t + 1;
		r.append(t);

def parseHexStr(s):
	t = '';
	for i in s.split(' '):
		if (len(i) > 0): 
			t += chr(int('0x' + i, 0));
	return t;

def locateHid():
	global code, base;
	
	save('hidObj', 0);
	t = code.find('hid:USER');
	if (t == -1):
		print('strHidUser not found');
		return;
	strHidUser =  t + base;
	print('strHidUser: %08x' % strHidUser);
	
	t = code.find(struct.pack('I', strHidUser));
	if (t == -1):
		print('refHidUser not found');
		return;
	refHidUser =  t + base;
	print('refHidUser: %08x' % refHidUser);
	
	r = findAll(code, struct.pack('I', refHidUser - 8));
	hidObj = 0;
	for i in r:
		(t,) = struct.unpack('I', code[i + 4: i + 8]);	
		if ((t & 0x80000000) == 0):
			hidObj = t;

	print('hidObj: %08x' % hidObj);
	
	save('hidObj', hidObj);

def locateFS() :
	global code, base;
	save('fsUserHandle', 0);
	save('fsOpenFile', findFunction(code, parseHexStr('c2 01 02 08')));
	save('fsOpenArchive', findFunction(code, parseHexStr('c2 00 0c 08')));
	save('fsWriteFile', findFunction(code, parseHexStr('02 01 03 08')));
	t = code.find(parseHexStr('f9 67 a0 08'));
	if (t == 0):
		return;
	(fsUserHandle,) = struct.unpack('I', code[t - 4: t]);
	save('fsUserHandle', fsUserHandle);





with open(sys.argv[1], 'rb') as f:
	code = f.read();


save('mountRom', findFunction(code, parseHexStr('0C 00 9D E5 00 10 90 E5  28 10 91 E5 31 FF 2F E1  ')));
save('mountRom', findFunction(code, '\x31\xFF\x2F\xE1\x04\x00\xA0\xE1\x0F\x10\xA0\xE1\xA4\x2F\xB0\xE1'));
save('mountArchive', findFunction(code, '\x10\x00\x97\xE5\xD8\x20\xCD\xE1\x00\x00\x8D'));
save('regArchive', findFunction(code, '\xB4\x44\x20\xC8\x59\x46\x60\xD8'));
save('mountArchive', findFunction(code, '\x28\xD0\x4D\xE2\x00\x40\xA0\xE1\xA8\x60\x9F\xE5\x01\xC0\xA0\xE3'));
save('getServiceHandle', findFunction(code, parseHexStr(' F8 67 A0 D8')));
save('userFsTryOpen', findFunction(code, parseHexStr('0D 10 A0 E1 00 C0 90 E5  04 00 A0 E1 3C FF 2F E1')));
save('userFsTryOpen', findFunction(code, parseHexStr('10 10 8D E2 00 C0 90 E5  05 00 A0 E1 3C FF 2F E1')));
save('cfgReadBlock', findFunction(code, parseHexStr('10 80 BD E8 82 00 01 00')));

locateHid();
locateFS();
print(repr(addrdb));

for i in addrdb:
	if (addrdb[i] == '0'):
		print('***WARNING*** Failed locating symbol %s , some patches may not work.' % i); 

print('Enter an empty folder to disable the layeredFS feature.');
filePath = raw_input('Enter the folder of the layeredFS file:');
print(""" 0: Japanese
 1: English
 6: Simp.Chinese
11: Trad.Chinese
Enter an empty code to disable Language Emulation.
""");
langCode = raw_input('Enter the language code for Language Emulation:');
if (len(langCode) == 0) :
	langCode = -1;
else:
	langCode = int(langCode);
regCode = 0;
if (langCode == 0):
	regCode = 0;
if (langCode == 1):
	regCode = 1;
if (langCode == 6):
	regCode = 4;
if (langCode == 11):
	regCode = 6;
		
header = 'u32 fsMountArchive = ' + addrdb['mountArchive'] + ';\n';
header += 'u32 fsRegArchive = ' + addrdb['regArchive'] + ';\n';
header += 'u32 userFsTryOpenFile = ' + addrdb['userFsTryOpen'] + ';\n';
header += 'u32 cfgReadBlock = ' + addrdb['cfgReadBlock'] + ';\n';
header += 'u32 langCode = ' + str(langCode) + ';\n';
header += 'u32 regCode = ' + str(regCode) + ';\n';
header += '#define LAYEREDFS_PREFIX "ram:/' + filePath + '/"\n'

if (len(filePath) > 0) :
	header += '#define ENABLE_LAYEREDFS 1 \n';
if (langCode != -1) :
	header += '#define ENABLE_LANGEMU 1 \n';
	
print(header);

with open('plugin\\source\\autogen.h', 'w') as f:
	f.write(header);