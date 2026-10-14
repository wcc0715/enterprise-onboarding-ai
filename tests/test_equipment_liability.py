import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import chatbot
from fixture_project import fixture_answer
class EquipmentLiabilityTests(unittest.TestCase):
    def test_damage_and_compensation_variants(self):
        for q in ['我把筆電摔壞了，是不是直接全額賠？','螢幕被我弄壞了，要賠多少','公司電腦正常耗損誰負責']:
            with self.subTest(q=q):
                r=fixture_answer(q,'draft')
                self.assertEqual(r['status'],'EQUIPMENT_LIABILITY')
                self.assertIn('不能直接認定你必須全額賠償',r['display_answer'])
                self.assertIn('依法釐清責任',r['display_answer'])
                self.assertEqual(r['sources'][0]['source_id'],'IT-005')
    def test_personal_damaged_property_not_company_policy(self):
        self.assertNotEqual(fixture_answer('我摔壞了自己的花瓶','draft')['status'],'EQUIPMENT_LIABILITY')
    def test_active_isolation(self):
        self.assertEqual(fixture_answer('筆電摔壞要全額賠嗎','active')['status'],'NO_ACTIVE_REGULATIONS')
if __name__=='__main__':unittest.main()
