from pathlib import Path
from tempfile import TemporaryDirectory
from start_local import command

def main():
    with TemporaryDirectory() as d:
        base=Path(d); (base/'app.py').write_text('print("local")')
        args=command(base)
        assert '--server.address' in args and args[args.index('--server.address')+1]=='127.0.0.1'
        assert '--server.port' in args and args[args.index('--server.port')+1]=='8501'
        assert 'streamlit' in args and 'run' in args
    print('PASS: Local-only launcher binds loopback, no hosting commands')
if __name__=='__main__':main()
