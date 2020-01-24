from binascii import hexlify
from enum import Enum, IntFlag, Flag
from struct import unpack
from datetime import datetime, timedelta
from unpack import Unpack29

class RAR_FORMAT(Enum):
    RARFMT_NONE =   0
    RARFMT14 =      1
    RARFMT15 =      2
    RARFMT50 =      3
    RARFMT_FUTURE = 4


class HEADER_TYPE(Enum):
    HEAD_MARK =         0x00
    HEAD_MAIN =         0x01
    HEAD_FILE =         0x02
    HEAD_SERVICE =      0x03
    HEAD_CRYPT =        0x04
    HEAD_ENDARC =       0x05
    HEAD_UNKNOWN =      0xFF
    HEAD3_MARK =        0x72
    HEAD3_MAIN =        0x73
    HEAD3_FILE =        0x74
    HEAD3_CMT =         0x75
    HEAD3_AV =          0x76
    HEAD3_OLDSERVICE =  0x77
    HEAD3_PROTECT =     0x78
    HEAD3_SIGN =        0x79
    HEAD3_SERVICE =     0x7A
    HEAD3_ENDARC =      0x7B


class HOST_SYSTEM(Enum):
    MSDOS =     0
    OS2 =       1
    WIN32 =     2
    UNIX =      3
    MACOS =     4
    BEOS =      5


class MAINHEADER_FLAGS(IntFlag):
    VOLUME =        0x0001
    COMMENT =       0x0002
    LOCK =          0x0004
    SOLID =         0x0008
    NEWNUMBERING =  0x0010
    AV =            0x0020
    PROTECT =       0x0040
    PASSWORD =      0x0080
    FIRSTVOLUME =   0x0100


class FILEHEADER_FLAGS(IntFlag):
    SPLIT_BEFORE =  0x0001
    SPLIT_AFTER =   0x0002
    PASSWORD =      0x0004
    COMMENT =       0x0008
    SOLID =         0x0010
    LARGE =         0x0100
    UNICODE =       0x0200
    SALT =          0x0400
    VERSION =       0x0800
    EXTTIME =       0x1000


class FILEHEADER_MASKS(IntFlag):
    WINDOWMASK =    0x00e0
    WINDOW64 =      0x0000
    WINDOW128 =     0x0020
    WINDOW256 =     0x0040
    WINDOW512 =     0x0060
    WINDOW1024 =    0x0080
    WINDOW2048 =    0x00A0
    WINDOW4096 =    0x00C0
    DIRECTORY =     0x00E0


class BaseBlock:
    def __init__(self, f = None):
        self.__headcrc = 0
        self.__headertype = None
        self.__flags = 0
        self.__headsize = 0
        if f is not None:
            self.__readbytes(f)

    def __readbytes(self, f):
        bytes = f.read(7)
        crc, type, flags, size =  unpack('<HBHH', bytes)
        self.__headcrc = crc
        self.__headertype = HEADER_TYPE(type)
        self.__flags = flags
        self.__headsize = size

    @property
    def HeadCRC(self):
        return self.__headcrc

    @property
    def HeaderType(self):
        return self.__headertype

    @property
    def Flags(self):
        return self.__flags

    @property
    def HeadSize(self):
        return self.__headsize

    def __str__(self):
        return "CRC: %s Type: %s Flags: %s Size:%s" % (
            "{0:#0{1}x}".format(self.__headcrc, 6),
            self.__headertype.name,
            "{0:#0{1}x}".format(self.__flags, 6),
            "{0:#0{1}x}".format(self.__headsize, 6)
            )

    def __repr__(self):
        return "CRC: %s Type: %s Flags: %s Size:%s" % (
            "{0:#0{1}x}".format(self.__headcrc, 6),
            self.__headertype.name,
            "{0:#0{1}x}".format(self.__flags, 6),
            "{0:#0{1}x}".format(self.__headsize, 6)
            )


class MainHeader:
    def __init__(self, bb = None, f = None):
        self.__baseblock = None
        self.__highposav = 0
        self.__posav = 0
        if bb is not None:
            self.__baseblock = bb
        if f is not None:
            self.__readbytes(f)

    def __readbytes(self, f):
        bytes = f.read(6)
        self.__highposav, self.__posav = unpack("<HI", bytes)

    @property
    def HeadCRC(self):
        return self.__baseblock.HeadCRC

    @property
    def HeaderType(self):
        return self.__baseblock.HeaderType

    @property
    def Flags(self):
        return MAINHEADER_FLAGS(self.__baseblock.Flags)

    @property
    def HeadSize(self):
        return self.__baseblock.HeadSize

    @property
    def HighPosAV(self):
        return self.__highposav

    @property
    def PosAV(self):
        return self.__posav

    def __str__(self):
        formatstring = " HighPosAV: %s PosAv: %s MainFlags: %s"
        return "MainHeader " + str(self.__baseblock) + formatstring % (
            "{0:#0{1}x}".format(self.__highposav, 6),
            "{0:#0{1}x}".format(self.__posav, 10),
            self.Flags.name
        )


class FileHeader:
    def __init__(self, bb = None, f = None):
        self.__baseblock = None
        self.__datasize = 0
        self.__lowunpsize = 0
        self.__host = 0
        self.__filecrc = 0
        self.__filetime = 0
        self.__unpver = 0
        self.__method = 0
        self.__fileattr = 0
        self.__winsize = 0
        self.__filename = ""
        self.__filedata = None
        self.__dates = None
        if bb is not None:
            self.__baseblock = bb
        if f is not None:
            self.__readbytes(f)

    def __readbytes(self, f):
        bytes = f.read(25)
        ds, lus, hs, fc, ft, uv, m, ns, fa = unpack("<IIBIIBBHI", bytes)
        fn = f.read(ns).decode("utf-8")
        d = (self.__baseblock.Flags & FILEHEADER_MASKS.WINDOWMASK) == FILEHEADER_MASKS.DIRECTORY
        self.__datasize = ds
        self.__lowunpsize = lus
        self.__hos = hs
        self.__filecrc = fc
        self.__filetime = ft
        self.__unpver = uv
        self.__method = m
        self.__fileattr = fa
        self.__winsize = 0 if d else 0x10000 << ((self.__baseblock.Flags & FILEHEADER_MASKS.WINDOWMASK) >> 5)
        self.__filename = fn
        self.__readexttime(f)
        unpacker = Unpack29(f.read(ds))

    def __readexttime(self, f):
        tbl = [None] * 4
        tbl[0] = self.__gettime(self.__filetime)
        if self.Flags & FILEHEADER_FLAGS.EXTTIME:
            flags = f.read(2)
            for i in range(4):
                ms = 0
                rmode = int.from_bytes(flags, 'little') >> ((3-i) * 4)
                if (rmode & 8) == 0:
                    continue
                if i != 0:
                    dostime = f.read(4)
                    dostimeint = int.from_bytes(dostime, 'little')
                    tbl[i] = self.__gettime(dostimeint)
                if rmode & 4:
                    tbl[i] += timedelta(seconds=1)
                count = rmode & 3
                for j in range(count):
                    cb = int.from_bytes(f.read(1), 'little')
                    ms |= ((cb) << ((j+3-count)*8))
                tbl[i] += timedelta(milliseconds=ms)
        self.__dates = tbl

    def __gettime(self, t):
        s = (t & 0x1f) * 2
        m = (t >> 5) & 0x3f
        h = (t >> 11) & 0x1f
        d = (t >> 16) & 0x1f
        mm = (t >> 21) & 0xf
        y = (t >> 25) + 1980
        return datetime(y,mm,d, h,m,s)


    @property
    def HeadCRC(self):
        return self.__baseblock.HeadCRC

    @property
    def HeaderType(self):
        return self.__baseblock.HeaderType

    @property
    def Flags(self):
        return FILEHEADER_FLAGS(self.__baseblock.Flags)

    @property
    def HeadSize(self):
        return self.__baseblock.HeadSize

    @property
    def DataSize(self):
        return self.__datasize

    @property
    def LowUnpSize(self):
        return self.__lowunpsize

    @property
    def HostOS(self):
        return HOST_SYSTEM(self.__host)

    @property
    def FileCRC(self):
        return self.__filecrc

    @property
    def FileTime(self):
        return self.__filetime

    @property
    def UnpVer(self):
        return self.__unpver

    @property
    def Method(self):
        return self.__method

    @property
    def FileAttribute(self):
        return self.__fileattr

    @property
    def WinSize(self):
        return self.__winsize

    @property
    def Filename(self):
        return self.__filename

    @property
    def ModifiedDate(self):
        return self.__dates[0]


    def __str__(self):
        formatstring = "\nFlags: %s\n Packed: %s Unpacked: %s HostOS: %s\n"
        formatstring += " CRC: %s\n Time: %s\n Ver: %s\n Method: %s\n"
        formatstring += " FileAttr: %s\n WinSize: %s\n Filename: \"%s\"\n"
        return "File " + str(self.__baseblock) + formatstring % (
            self.Flags.name,
            "{0:#0{1}x}".format(self.DataSize, 10),
            "{0:#0{1}x}".format(self.LowUnpSize, 6),
            self.HostOS.name,
            "{0:#0{1}x}".format(self.FileCRC, 10),
            self.ModifiedDate.strftime("%d/%m/%Y %H:%M:%S"),
            "{0:#0{1}x}".format(self.UnpVer, 4),
            "{0:#0{1}x}".format(self.Method, 4),
            "{0:#0{1}x}".format(self.FileAttribute, 10),
            "{0:#0{1}x}".format(self.WinSize, 10),
            self.Filename
        )


if __name__ == '__main__':
    flags = FILEHEADER_FLAGS(0xFF)
    print(flags)