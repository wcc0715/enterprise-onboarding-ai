"""辨識描述對象與明確假別；不推定申請資格。"""
import retrieval

def family_illness(question):
    q=retrieval.normalize(question)
    relatives=['家人','親人','孩子','小孩','父親','母親','爸爸','媽媽','配偶','太太','先生']
    return any(t in q and '不是'+t not in q for t in relatives) and any(t in q for t in ['生病','發燒','不舒服','住院','就醫'])

def specified_leave(question):
    q=retrieval.normalize(question)
    found=[t for t in ['特休','年假','事假','病假'] if t in q and '不請'+t not in q and '不是'+t not in q]
    if len(found)==1:return '特休' if found[0]=='年假' else found[0]
    return None


def carrying_out(question):
    q=retrieval.normalize(question)
    return any(t in q for t in ['帶出去','帶出公司','拿出去','帶走','帶回家','攜出','帶到外面'])


def personal_record_request(question):
    """辨識要求實際個人紀錄；不攔截一般制度或更正流程提問。"""
    q=retrieval.normalize(question)
    fields=['薪水','薪資','薪酬','工資','出勤紀錄','打卡紀錄','個資','個人資料','身分證','住址','帳戶資料','權限紀錄','獎金金額']
    subjects=['我的','我這個月','我本月','我薪水','我薪資','本人','同事','部屬','所有員工','員工的','大家的','其他人的','他的','她的']
    explicit=['查','列出','顯示','讀取','匯出','下載']
    requests=explicit+['告訴我','給我','提供','看一下','多少','金額']
    if not (any(t in q for t in fields) and any(t in q for t in subjects) and any(t in q for t in requests)):
        return None
    if any(t in q for t in ['變更','更正','少發','算錯','補發','發放','發薪']) and not any(t in q for t in explicit+['多少','金額']):
        return None
    others=any(t in q for t in ['同事','部屬','所有員工','員工的','大家的','其他人的','他的','她的'])
    return 'others' if others else 'self'


def restricted_action_request(question):
    """辨識要求小助理實際設定／核准，不驗證或接受對話職務宣稱。"""
    q=retrieval.normalize(question)
    if '權限' in q and any(t in q for t in ['幫我開','幫我設定','幫我提升','直接開','立即開','現在開','授予我','給我最高','給我管理員']):
        return 'access_change'
    if any(t in q for t in ['設備','筆電','電腦']) and any(t in q for t in ['批准','核准','認定','宣布']) and any(t in q for t in ['我是主管','我是總經理','全部','所有','都不是','不用it','直接攜出']):
        return 'equipment_classification'
    return None


def data_incident(question):
    q=retrieval.normalize(question)
    events=['寄錯','誤寄','誤傳','傳錯','發錯','寄到錯的人','傳到錯的人','外洩','洩漏','資料外流']
    data=['資料','文件','附件','檔案','客戶','個資','機密','公司信件']
    return any(t in q for t in events) and any(t in q for t in data)


def equipment_liability(question):
    q=retrieval.normalize(question)
    if '責任' in q and any(t in q for t in ['誰','單位','判定']):
        return False  # 責任認定單位尚未提供，不能把 IT 技術確認當作責任裁定。
    return any(t in q for t in ['電腦','筆電','螢幕','設備']) and any(t in q for t in ['賠','責任','摔壞','弄壞','人為損壞','正常耗損'])
