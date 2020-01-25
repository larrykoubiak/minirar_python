from bitreader import BitReader

MAX_QUICK_DECODE_BITS = 10
MAX_UNPACK_FILTERS = 8192
MAX3_UNPACK_FILTERS = 8192
MAX3_UNPACK_CHANNELS = 1024
MAX_FILTER_BLOCK_SIZE = 0x400000
UNPACK_MAX_WRITE = 0x400000

NC    = 306
DC    = 64
LDC   = 16
RC    = 44
HUFF_TABLE_SIZE = NC + DC + RC + LDC
BC    = 20

NC30  = 299
DC30  = 60
LDC30 = 17
RC30  = 28
BC30  = 20
HUFF_TABLE_SIZE30 = NC30 + DC30 + RC30 + LDC30

LARGEST_TABLE_SIZE = 306

LDecode = (0,1,2,3,4,5,6,7,8,10,12,14,16,20,24,28,32,40,48,56,64,80,96,112,128,160,192,224)
LBits = (0,0,0,0,0,0,0,0,1,1,1,1,2,2,2,2,3,3,3,3,4,4,4,4,5,5,5,5)
DBitLengthCounts = (4,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,14,0,12)
SDDecode = (0,4,8,16,32,64,128,192)
SDBits = (2,2,3,4,5,6,6,6)

class DecodeTable:
    def __init__(self):
        self.MaxNum = 0
        self.DecodeLen = [0] * 16
        self.DecodePos = [0] * 16
        self.QuickBits = 0
        self.QuickLen = [0] * (1 << MAX_QUICK_DECODE_BITS)
        self.QuickNum = [0] * (1 << MAX_QUICK_DECODE_BITS)
        self.DecodeNum = [0] * LARGEST_TABLE_SIZE


class Unpack29:
    def __init__(self, data):
        self.__DDecode = [0] * 64 ## DC
        self.__DBits = [0] * 64
        self.__Bits = 0
        self.__initarrays()
        self.__bitreader : BitReader = None
        self.__unpackblocktables = {
            "LD": DecodeTable(),
            "DD": DecodeTable(),
            "LDD": DecodeTable(),
            "RD": DecodeTable(),
            "BD": DecodeTable()
        }
        if data is not None:
            self.__bitreader = BitReader(data)
            self.__readTables30()

    def __initarrays(self):
        if self.__DDecode[1] == 0:
            Dist = 0
            BitLength = 0
            Slot = 0
            for I in range(len(DBitLengthCounts)):
                for J in range(DBitLengthCounts[I]):
                    self.__DDecode[Slot] = Dist
                    self.__DBits[Slot] = BitLength
                    Slot += 1
                    Dist += (1 << BitLength)
                BitLength += 1

    def __readTables30(self):
        BitLength = bytearray(BC)
        Table = bytearray(HUFF_TABLE_SIZE30)
        UnpOldTable = bytearray(HUFF_TABLE_SIZE30)
        BitField = self.__bitreader.Read16()
        if BitField & 0x8000:
            pass # BLOCK_PPM
        if (BitField & 0x4000) == 0: ##reset old table
            UnpOldTable = bytearray(HUFF_TABLE_SIZE30)
        PrevLowDist = 0
        LowDistRepCount = 0
        self.__bitreader.AddBits(2)
        I = 0
        while I < BC:
            Length = self.__bitreader.Read16() >> 12
            self.__bitreader.AddBits(4)
            if Length == 15:
                ZeroCount = self.__bitreader.Read16() >> 12
                self.__bitreader.AddBits(4)
                if ZeroCount== 0:
                    BitLength[I] = 15
                else:
                    ZeroCount += 2
                    while ZeroCount > 0 and I <len(BitLength):
                        BitLength[I] = 0
                        I += 1
                        ZeroCount -= 1
                    I -= 1
            else:
                BitLength[I] = Length
            I += 1
        self.__makedecodetables(BitLength,self.__unpackblocktables["BD"], BC30)
        ##TO DO : finish the readtable function

    def __makedecodetables(self, lengthtable, decodetable : DecodeTable, size):
        decodetable.MaxNum = size
        lengthcount = [0] * 16
        for i in range(size):
            lengthcount[lengthtable[i] & 0xf] += 1
        lengthcount[0] = 0
        decodetable.DecodeNum = [0] * len(decodetable.DecodeNum)
        decodetable.DecodePos[0] = 0
        decodetable.DecodeLen[0] = 0
        upperlimit = 0
        for i in range(1,16):
            upperlimit += lengthcount[i]
            leftaligned = upperlimit << (16-i)
            upperlimit *= 2
            decodetable.DecodeLen[i] = leftaligned
            decodetable.DecodePos[i] = decodetable.DecodePos[i-1]+lengthcount[i-1]
        copydecodepos = [0] * len(decodetable.DecodePos)
        copydecodepos[:] = decodetable.DecodePos
        for i in range(size):
            curbitlength = lengthtable[i] & 0xf
            if curbitlength !=0:
                LastPos = copydecodepos[curbitlength]
                decodetable.DecodeNum[LastPos] = i
                copydecodepos[curbitlength] += 1
        if size in (NC, NC30):
            decodetable.QuickBits = MAX_QUICK_DECODE_BITS
        else:
            decodetable.QuickBits = MAX_QUICK_DECODE_BITS - 3
        quickdatasize = 1 << decodetable.QuickBits
        curbitlength = 1
        for code in range(quickdatasize):
            bitfield = code << (16-decodetable.QuickBits)
            while curbitlength < len(decodetable.DecodeLen) and \
                  bitfield>=decodetable.DecodeLen[curbitlength]:
                curbitlength += 1
            decodetable.QuickLen[code] = curbitlength
            dist = bitfield - decodetable.DecodeLen[curbitlength - 1]
            dist >>= (16 - curbitlength)
            pos = decodetable.DecodePos[curbitlength] + dist
            if curbitlength < len(decodetable.DecodePos) and pos < size:
                decodetable.QuickNum[code] = decodetable.DecodeNum[pos]
            else:
                decodetable.QuickNum[code] = 0

    @property
    def DDecode(self):
        return self.__DDecode

    @property
    def DBits(self):
        return self.__DBits

if __name__ == '__main__':
    test = bytearray((0x11,0xD9,0x5C,0x1C,0xC8,0x8F,0xCD,0x1D,0x59))
    pack = Unpack29(test)
    print(pack.DDecode)