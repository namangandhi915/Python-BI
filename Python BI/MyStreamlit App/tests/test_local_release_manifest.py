from verify_local_release import verify

def main():
    ok,errors=verify()
    assert ok,errors
    print('PASS: Local academic release manifest verified')
if __name__=='__main__':main()
