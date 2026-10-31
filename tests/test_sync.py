import copy
import datetime as dt
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from common import ROOT,TZ,read,write
from model import hit,both_theory,features,forecast
from update_data import validate,run,settle,verify_ledger
from confirm_publication import confirm

class SyncTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.rows=validate(read(ROOT/'data.json')['draws'])

    def test_both_distinct_tails_not_any(self):
        self.assertFalse(hit([1,6],[1,11,21,31,5]))
        self.assertTrue(hit([1,6],[1,16,22,33,39]))
        self.assertFalse(hit([1,6],[2,3,4,5,7]))
        with self.assertRaises(ValueError):hit([1,1],[1,2,3,4,5])
        self.assertLess(both_theory([0,1]),both_theory([1,2]))
        self.assertTrue(.16<both_theory([1,2])<.18)

    def test_validation_and_preservation(self):
        r=copy.deepcopy(self.rows[:5]);self.assertEqual(len(validate(r+[r[0]])),5)
        bad=copy.deepcopy(r[0]);bad['numbers']=[1,1,2,3,4]
        with self.assertRaises(ValueError):validate([bad])
        bad['date']='2099-01-01'
        with self.assertRaises(ValueError):validate([bad])
        with self.assertRaises(ValueError):validate([r[0],r[2]])
        conflict=copy.deepcopy(r[0]);conflict['numbers']=[1,2,3,4,5]
        if conflict['numbers']==r[0]['numbers']:conflict['numbers']=[2,3,4,5,6]
        with self.assertRaises(ValueError):validate(r+[conflict])

    def test_no_future_leakage(self):
        rows=copy.deepcopy(self.rows[:70]);x,y=features(rows);a=forecast(x,y,60)
        # Isolated test fixture only, never written to official history.
        for r in rows[60:]:r['numbers']=[1,2,3,4,5]
        xx,yy=features(rows);np.testing.assert_array_equal(x[:61],xx[:61]);self.assertEqual(a,forecast(xx,yy,60))

    def test_full_loop_and_no_overwrite(self):
        rows=self.rows[:65]
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);write(root/'data.json',dict(draws=rows[:60],fetchedAt='2026-01-01T00:00:00+08:00'))
            day=dt.date.fromisoformat(rows[60]['date']);clock=dt.datetime.combine(day,dt.time(18),TZ)
            with patch('update_data.fetch_official',return_value=rows[:60]):self.assertTrue(run(root,clock=clock))
            ledger=read(root/'archive/predictions.json');original=copy.deepcopy(ledger)
            with patch('update_data.fetch_official',return_value=rows[:60]),patch('update_data.analyze',side_effect=AssertionError('must not retrain unchanged data')):
                self.assertTrue(run(root,clock=clock+dt.timedelta(minutes=30)))
            self.assertEqual(original,read(root/'archive/predictions.json'))
            self.assertTrue(confirm(root,clock=clock+dt.timedelta(minutes=35),run_url='unit-test',commit='unit-test'))
            self.assertFalse(confirm(root,clock=clock+dt.timedelta(minutes=36)))
            after=clock.replace(hour=21)
            with patch('update_data.fetch_official',return_value=rows[:61]):self.assertTrue(run(root,clock=after))
            data=read(root/'data.json');self.assertEqual(data['ai']['liveSummary']['settled'],1)
            self.assertEqual(data['ai']['prediction']['afterPeriod'],rows[60]['period'])
            self.assertEqual(read(root/'archive/predictions.json')[0],original[0])
            result=read(root/'archive/settlements.json')[0]
            self.assertEqual(result['hit'],hit(original[0]['tails'],rows[60]['numbers']))
            prior=(root/'data.json').read_bytes();success=read(root/'status.json')['lastSuccessAt']
            with patch('update_data.fetch_official',side_effect=RuntimeError('unit-test source failure')):self.assertFalse(run(root,clock=after))
            self.assertEqual((root/'data.json').read_bytes(),prior)
            self.assertEqual(read(root/'status.json')['lastSuccessAt'],success)

    def test_late_publication_excluded_and_ledger_tamper_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);rows=self.rows[:61];day=dt.date.fromisoformat(rows[60]['date']);clock=dt.datetime.combine(day,dt.time(18),TZ)
            write(root/'data.json',dict(draws=rows[:60],fetchedAt=clock.isoformat()))
            with patch('update_data.fetch_official',return_value=rows[:60]):self.assertTrue(run(root,clock=clock))
            confirm(root,clock=clock.replace(hour=21))
            results=settle(read(root/'archive/predictions.json'),read(root/'archive/publications.json'),rows,[])
            self.assertFalse(results[0]['eligible'])
            ledger=read(root/'archive/predictions.json');ledger[0]['tails']=[0,1]
            with self.assertRaises(ValueError):verify_ledger(ledger)

if __name__=='__main__':unittest.main()
