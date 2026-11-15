from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
import zipfile
import openpyxl
from local_file_guard import validate_upload, safe_stored_path

class Upload:
    def __init__(self,name,raw):self.name=name;self._raw=raw;self.size=len(raw)
    def getvalue(self):return self._raw

def rejects(call):
    try: call()
    except (ValueError,FileNotFoundError): return
    raise AssertionError('Unsafe input was accepted')

def main():
    x=validate_upload(Upload('good.csv',b'A,B\n1,2\n'));assert x['size_bytes']==8
    rejects(lambda:validate_upload(Upload('../evil.csv',b'a,b\n1,2')))
    rejects(lambda:validate_upload(Upload('bad.csv',b'PK\x03\x04PAYLOAD')))
    rejects(lambda:validate_upload(Upload('bad.csv',b'X\x00Y')))
    rejects(lambda:validate_upload(Upload('bad.exe',b'Hello')))
    rejects(lambda:validate_upload(Upload('bad.xlsx',b'not a workbook')))
    rejects(lambda:validate_upload(Upload('big.csv',b'1'*2048),max_mib=0))
    book=openpyxl.Workbook(); book.active['A1']='Test'; stream=BytesIO();book.save(stream)
    result=validate_upload(Upload('good.xlsx',stream.getvalue()))
    assert result['extension']=='.xlsx'
    with TemporaryDirectory() as temp:
        folder=Path(temp)
        f=safe_stored_path(folder,'0123456789abcdef0123456789abcdef.csv')
        f.write_text('a\n1\n')
        assert safe_stored_path(folder,f.name,must_exist=True)==f
        rejects(lambda:safe_stored_path(folder,'../data.csv'))
        rejects(lambda:safe_stored_path(folder,'..bad.csv'))
        rejects(lambda:safe_stored_path(folder,'file.exe'))
        rejects(lambda:safe_stored_path(folder,'missing.csv',must_exist=True))
    print('PASS: Local CSV/XLSX validation, size rules, safe Dataset Library paths')
if __name__=='__main__':main()
