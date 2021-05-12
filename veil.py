#!/usr/bin/env python3

import argparse
import textwrap
from construct import *
import struct

supported_types = [ "bmp", "wav", "au" ]

"""
Encode au file
"""
def encode_au(xor_array, output):
	r_size = len(xor_array)

	format = Struct(
		"signature" / Const(b".snd"),
		"data_offset" / Const(b"\x00\x00\x00\x18"),
		"data_size" / BytesInteger(4, swapped=False),
		"encoding" / Const(b"\x00\x00\x00\x01"),
		"sample_rate"/ Const(b"\x00\x00\xac\x44"),
		"channels" / Const(b"\x00\x00\x00\x02"),
		"data" / Array(r_size, Byte)
	)

	x = format.build(dict(data_size=r_size, data=xor_array))
	f = open(output, 'w+b')
	f.write(x)
	f.close()

"""
Encodes wav file
"""
def encode_wav(xor_array, output):
	r_size = len(xor_array)
	f_size = 44 + r_size
	
	format = Struct(
		"signature" / Const(b"RIFF"),
		"file_size" / BytesInteger(4, swapped=True),
		"type_header" / Const(b"WAVE"),
		"fmt" / Const(b"fmt\x20"),
		"format_data_len" / Const(b"\x10\x00\x00\x00"),
		"format_type" / Const(b"\x01\x00"),
		"channel_num" / Const(b"\x02\x00"),
		"sample_rate" / Const(b"\x44\xac\x00\x00"),
		"calc1" / Const(b"\x10\xb1\x02\x00"),
		"calc2" / Const(b"\x04\x00"),
		"bits_per_sample"/ Const(b"\x10\x00"),
		"chunk_header" / Const(b"data"),
		"data_size" / BytesInteger(4, swapped=True),
		"data" / Array(r_size, Byte)
	)

	x = format.build(dict(file_size=f_size, data_size=r_size, data=xor_array))
	f = open(output, 'w+b')
	f.write(x)
	f.close()

"""
Encodes bmp file
"""
def encode_bmp(xor_array, output):
	r_size = len(xor_array)
	h = r_size / 12
	ih = int(h)
	f_size = r_size + 54

	format = Struct(
		"signature" / Const(b"BM"),
		"file_size" / BytesInteger(4, swapped=True),
		Padding(4),
		"data_offset" / Const(b"\x36\x00\x00\x00"),
		"header_len" / Const(b"\x28\x00\x00\x00"),
		"width" / BytesInteger(4, swapped=True), 
		"height" / BytesInteger(4, swapped=True), 
		"color_planes" / Const(b"\x01\x00"),
		"pixel_bits" / Const(b"\x18\x00"),
		Padding(4),
		"raw_size" / BytesInteger(4, swapped=True),
		"print_res_1" / Const(b"\x13\x0b\x00\x00"),
		"print_res_2" / Const(b"\x13\x0b\x00\x00"),
		Padding(8),
		"pixels" / Array(r_size, Byte)
	)

	x = format.build(dict(file_size=f_size, height=ih, width=4, raw_size=r_size, pixels=xor_array))
	f = open(output, 'w+b')
	f.write(x)
	f.close()


"""
Uses xor to encode the message with the key.
"""
def message_xor_key(message, key, ftype):
	size = len(message)
	if ftype == "bmp": #mod by 12 to make sure there is no picture corruption
		xor_array = [32]*size if size % 12  == 0 else [32]*(size + (12 - (size % 12)))
	if ftype == "wav" or ftype == "au": #mod by 4 to make sure there is no channel corruption
		xor_array = [32]*size if size % 4  == 0 else [32]*(size + (4 - (size % 4)))

	#In case of zero length key	
	if key == "":
		for letter in range(0, len(message)):
			if ord(message[letter]) > 255:
				print("Message contains the character '" + message[letter] + "' at location " + str(letter) + " outside the range of ASCII printable characters. Please remove the character and re-encode.")
				quit()

			xor_array[letter] = ord(message[letter])
		return xor_array
	

	for letter in range(0, len(xor_array)):
		if ord(message[letter%len(message)]) > 255:
			print("Message contains the character '" + message[letter] + "' at location " + str(letter) + " outside the range of ASCII printable characters. Please remove the character and re-encode.")
			quit()
		if ord(key[letter%len(key)]) > 255:
			print("Key contains the character '" + key[letter] + "' at location " + str(letter) + " outside the range of ASCII printable characters. Please remove the character and re-encode.")
			quit()

		if letter < len(message):
			xor_array[letter] = ord(message[letter]) ^ ord(key[letter%len(key)])
		else:
			xor_array[letter] = xor_array[letter] ^ ord(key[letter%len(key)])
	
	return xor_array

"""
Performs error checking, creates encoded message, then calls appropriate encode function based on file type.
"""
def encode(message, key, ftype, output):
	if type(message) != str:
		print("Message not given. Please see usage.")
		quit()
	if type(key) != str:
		print("Key not given. Please see usage.")
		quit()
	if type(ftype) != str:
		print("File type not specified. Please see usage.")
		quit()
	if ftype not in supported_types:
		print("File type is either not recognized or not supported. Please see usage.")
		quit()
	if type(output) != str:
		print("Output file not specified. Please see usage.")
		quit()
	
	xor_array = message_xor_key(message, key, ftype)
	if ftype == "bmp":
		encode_bmp(xor_array, output)
	if ftype == "wav":
		encode_wav(xor_array, output)
	if ftype == "au":
		encode_au(xor_array, output)

"""
Performs error checking, calculates data offset based on provided file type, the decodes file with given key.
"""
def decode(key, ftype, ifile):
	if type(key) != str:
		print("Key not given. Please see usage.")
		quit()
	if type(ifile) != str:
		print("Input file not specified. Please see usage.")
		quit()
	if type(ftype) != str:
		print("File type not specified. Please see usage.")
		quit()
	if ftype not in supported_types:
		print("File type is either not recognized or not supported. Please see usage.")
		quit()

	offset = 0
	if ftype == "bmp":
		offset = 54 
	if ftype == "wav":
		offset = 44
	if ftype == "au":
		offset = 24

	try:
		f = open(ifile, 'rb')
	except FileNotFoundError:
		print("File to decode not found. Exiting.")
		quit()
	
	byte_array = f.read()
	message_bytes = byte_array[offset:len(byte_array)] 
	message = []

	if key == "":
		for b in range(0, len(message_bytes)):
			message.append(chr(message_bytes[b]))
	else:
		for b in range(0, len(message_bytes)):
			message.append(chr(message_bytes[b] ^ ord(key[b%len(key)])))
	
	unstripped = "".join(message) 
	print(unstripped.strip()) #strip spaces placed as padding
	
	f.close()

"""
MAIN - Parses arguments and calls encode or decode. 
"""
parser = argparse.ArgumentParser(prog= 'steg', formatter_class=argparse.RawDescriptionHelpFormatter, epilog=textwrap.dedent('''This program creates and interprets steganographic images.\nTo create an encoded image, run this program with the -e flag, and supply the message, key, type, and output parameters.\nExample: python3 veil.py -e -m "Ride at dawn" -k "Hello world!" -t bmp -o harmless.bmp\n\nTo decode a created steganographic file, run this program with the -d flag, and supply the key, type, and file parameters.\nExample: python3 veil.py -d -k "Hello world!" -t bmp -f harmless.bmp\n\nCurrent file type options are: bmp, wav, au'''))

parser.add_argument('-e', '--encode', action='store_true')	
parser.add_argument('-d', '--decode', action='store_true')
parser.add_argument('-m', '--message', action='store', type=str)
parser.add_argument('-k', '--key', action='store', type=str)
parser.add_argument('-t', '--type', action='store', type=str)
parser.add_argument('-f', '--file', action='store', type=str)
parser.add_argument('-o', '--output', action='store', type=str)

args = parser.parse_args()

if args.encode == True:
	encode(args.message, args.key, args.type, args.output)
elif args.decode == True:
	decode(args.key, args.type, args.file)
else:
	print("Unclear request. Please see usage.")
	quit()
