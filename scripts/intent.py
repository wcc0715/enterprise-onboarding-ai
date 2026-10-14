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
