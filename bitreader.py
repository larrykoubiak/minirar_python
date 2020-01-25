from binascii import hexlify
class BitReader:
    def __init__(self, data = None):
        length = 0 if data is None else len(data) + 4 
        self.__data = bytearray(length)
        self.__addr = 0
        self.__bit = 0
        if data is not None:
            self.__data[0:len(data)] = data

    def AddBits(self, bits):
        bits += self.__bit
        self.__addr += (bits >> 3)
        self.__bit = bits & 7

    def Read16(self):
        bitfield = self.__data[self.__addr] << 16
        bitfield |= self.__data[self.__addr + 1] << 8
        bitfield |= self.__data[self.__addr + 2]
        bitfield >>= (8 - self.__bit)
        return bitfield & 0xffff

    def Read32(self):
        bitfield = self.__data[self.__addr] << 24
        bitfield |= self.__data[self.__addr + 1] << 16
        bitfield |= self.__data[self.__addr + 2] << 8
        bitfield |= self.__data[self.__addr + 3]
        bitfield <<= self.__bit
        bitfield |= self.__data[self.__addr + 4] >> (8 - self.__bit)
        return bitfield & 0xffffffff

if __name__ == '__main__':
    test = bytearray((0x11, 0xD9, 0x5C, 0x1C))
    br = BitReader(test)
    test1 = br.Read16()
    br.AddBits(2)
    test2 = br.Read16()
    test3 = test2 >> 12
    print(hexlify(test))
    print("{0:#0{1}x}".format(test1, 10))
    print("{0:#0{1}x}".format(test2, 10))
    print("{0:#0{1}x}".format(test3, 10))