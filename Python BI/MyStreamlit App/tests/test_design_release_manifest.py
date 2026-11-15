from verify_design_release import check

def main():
    ok,errors=check()
    assert ok,errors
    print('PASS: Packaged file hashes and release identity')

if __name__=='__main__':main()
