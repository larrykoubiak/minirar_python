import argparse
from structs import RAR_FORMAT, HEADER_TYPE
from structs import BaseBlock, MainHeader, FileHeader


def read_signature(f):
    rarsig = bytearray([0x52, 0x61, 0x72, 0x21, 0x1a, 0x07])
    sig = f.read(7)
    if sig[0:6]==rarsig:
        if sig[6]==0:
            return RAR_FORMAT.RARFMT15
        elif sig[6]==1:
            return RAR_FORMAT.RARFMT50
        elif sig[6]==2:
            return RAR_FORMAT.RARFMT_FUTURE
        else:
            return RAR_FORMAT.RARFMT_NONE


def read_file(filename):
    f = open(filename, "rb")
    fmt = read_signature(f)
    log = open(filename[:-4]+".log","w")
    if fmt != RAR_FORMAT.RARFMT_NONE:
        bb = BaseBlock(f)
        while bb.HeaderType != HEADER_TYPE.HEAD3_ENDARC:
            if bb.HeaderType == HEADER_TYPE.HEAD3_MAIN:
                mh = MainHeader(bb, f)
                print(mh)
            elif bb.HeaderType == HEADER_TYPE.HEAD3_FILE:
                fh = FileHeader(bb, f)
                print(fh)
                for r in fh.GetTableValues():
                    log.write(r + "\n")
            else:
                pass
            bb = BaseBlock(f)
    f.close()
    log.close()

def main():
    parser = argparse.ArgumentParser(description='Unrar file')
    parser.add_argument('filename', nargs='+')
    args = parser.parse_args()
    filename = args.filename[0]
    read_file(filename)

if __name__ == '__main__':
    main()