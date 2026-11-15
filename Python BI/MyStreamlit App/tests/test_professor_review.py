import json
import zipfile
from io import BytesIO
from professor_review import review_packet, review_summary, checklist_csv, review_html

def main():
    doc=review_summary(); assert doc['operating_mode']=='PRIVATE_LOCAL_ONLY'
    assert doc['academic_approval']=='NOT_YET_REQUESTED'
    assert doc['public_hosting']=='NOT_AUTHORIZED'
    assert len(doc['phase_status'])==8
    assert 'Professor comments' in checklist_csv()
    data=review_packet()
    with zipfile.ZipFile(BytesIO(data)) as zf:
        assert sorted(zf.namelist())==sorted(['PROJECT_STATUS.json','PROFESSOR_REVIEW.html','VERIFICATION_CHECKLIST.csv','README.txt'])
        data=json.loads(zf.read('PROJECT_STATUS.json'));assert data['public_hosting']=='NOT_AUTHORIZED'
        assert b'Customer Name' not in zf.read('PROFESSOR_REVIEW.html')
    assert '<html' in review_html()
    print('PASS: Eight-phase, privacy-minimised professor handover materials')
if __name__=='__main__':main()
