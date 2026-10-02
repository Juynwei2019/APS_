import copy
import unittest
from scheduler import schedule, validate


class SchedulerTests(unittest.TestCase):
    def setUp(self):
        self.data = {'resources': [{'id':'A','windows':[{'start':'2026-10-02T08:00','end':'2026-10-02T12:00'},{'start':'2026-10-03T08:00','end':'2026-10-03T12:00'}]}, {'id':'B','windows':[{'start':'2026-10-02T08:00','end':'2026-10-02T17:00'}]}], 'products':[{'id':'P','route':[{'name':'切割','resource':'A','minutes_per_unit':60},{'name':'組裝','resource':'B','minutes_per_unit':60}]}], 'orders':[{'id':'O1','product':'P','quantity':2,'priority':1,'due':'2026-10-02T11:00'},{'id':'O2','product':'P','quantity':2,'priority':2,'due':'2026-10-03T17:00'}]}

    def run_schedule(self, data=None, end='2026-10-04T00:00', rule='priority'):
        return schedule(data or self.data, '2026-10-02T08:00',end,rule)

    def test_capacity_precedence_and_due(self):
        result=self.run_schedule()
        self.assertEqual([o['status'] for o in result['orders']], ['late','on_time'])
        ops=result['operations']
        self.assertEqual(ops[0]['end'], '2026-10-02T10:00')
        self.assertEqual(ops[1]['start'], ops[0]['end'])
        self.assertEqual(ops[2]['start'], ops[0]['end'])
        self.assertEqual(ops[3]['start'],ops[1]['end'])
        for resource in ('A','B'):
            items=sorted([o for o in ops if o['resource']==resource],key=lambda o:o['start'])
            for left,right in zip(items,items[1:]):
                self.assertLessEqual(left['end'],right['start'])

    def test_insufficient_capacity_blocks_successor(self):
        result=self.run_schedule(end='2026-10-02T09:00')
        self.assertTrue(all(o['status']=='unscheduled' for o in result['operations']))
        self.assertEqual(result['operations'][1]['reason'],'前置工序未排入')

    def test_calendar_gap_not_spanned(self):
        self.data['orders'][0]['quantity']=5
        result=self.run_schedule()
        self.assertEqual(result['operations'][0]['status'],'unscheduled')

    def test_next_day_and_holiday(self):
        self.data['orders'][0]['quantity']=3
        self.data['products'][0]['route']=self.data['products'][0]['route'][:1]
        result=self.run_schedule()
        self.assertEqual(result['operations'][1]['start'],'2026-10-03T08:00')
        self.data['resources'][0]['windows']=self.data['resources'][0]['windows'][:1]
        self.assertEqual(self.run_schedule()['operations'][1]['status'],'unscheduled')

    def test_due_rule_and_repeatability(self):
        self.data['orders'][1]['due']='2026-10-02T09:00'
        self.assertEqual(self.run_schedule(rule='due')['orders'][0]['order'],'O2')
        original=copy.deepcopy(self.data)
        self.assertEqual(self.run_schedule(),self.run_schedule())
        self.assertEqual(self.data,original)

    def test_validation(self):
        cases=[]
        d=copy.deepcopy(self.data);d['orders'][0]['quantity']=0;cases.append(d)
        d=copy.deepcopy(self.data);d['orders'][0]['product']='missing';cases.append(d)
        d=copy.deepcopy(self.data);d['resources'][0]['windows']*=2;cases.append(d)
        d=copy.deepcopy(self.data);d['products'][0]['route'][0]['minutes_per_unit']=1.5;cases.append(d)
        d=copy.deepcopy(self.data);d['orders'][1]['id']='O1';cases.append(d)
        for d in cases:
            with self.subTest(data=d), self.assertRaises(ValueError): validate(d)
        with self.assertRaises(ValueError): self.run_schedule(end='2026-10-02T08:00')

if __name__ == '__main__':
    unittest.main()
