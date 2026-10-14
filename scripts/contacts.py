"""只讀使用者授權的虛構通訊錄；不驗證身分、不提供真實個資。"""
import json
import retrieval

def lookup(question,root,mode):
    path=root/'metadata/simulated_contact_directory.json'
    if mode!='draft' or not path.exists():
        text='目前沒有提供可確認的真實姓名或聯絡資訊，也沒有串接公司聯絡名冊。模擬通訊錄僅供草案測試，不能當作真實聯絡方式。'
        return dict(status='CONTACT_NOT_PROVIDED',answer=text,display_answer=text,sources=[])
    d=json.loads(path.read_text(encoding='utf-8'))
    if d['dataset_type']!='SIMULATED' or not d['is_simulated'] or any(not c['is_simulated'] or not c['email'].endswith('@example.invalid') for c in d['contacts']):
        raise ValueError('模擬通訊錄標示或測試郵件格式不符')
    q=retrieval.normalize(question)
    selected=[c for c in d['contacts'] if c['name'] in q or any(t in q for t in c['aliases'])]
    if any(t in q for t in ['我的主管','直屬主管']) or not selected:
        text='可以幫你查模擬通訊錄。你想找哪個部門或哪一位主管？目前沒有你的所屬部門或主管配對資料，不能替你認定誰是你的主管。'
        return dict(status='CONTACT_CLARIFY',answer=text,display_answer=text,sources=[])
    text='以下是 PoC 模擬聯絡資料，全部為虛構，郵件與分機不能當作真實聯絡方式：\n\n'
    text+='\n\n'.join(f'{c["role"]}：{c["name"]}\n模擬郵件：{c["email"]}\n模擬分機：{c["extension"]}' for c in selected)
    if any(t in q for t in ['手機','電話']):text+='\n\n目前只建立模擬分機與郵件，沒有手機或外線電話。'
    text+=f'\n資料來源：模擬通訊錄 v{d["version"]}（metadata/simulated_contact_directory.json）'
    return dict(status='SIMULATED_CONTACTS',answer=text,display_answer=text,sources=[],contacts=selected,contact_directory_version=d['version'],is_simulated=True)
