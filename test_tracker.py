import tempfile, unittest
from datetime import datetime,timedelta,timezone
from pathlib import Path
from plugins.study_tracker import StudyTracker
class TrackerTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(); self.now=datetime(2026,11,3,12,tzinfo=timezone(timedelta(hours=-8))); self.t=StudyTracker(lambda:Path(self.tmp.name),lambda pid:{'title':'Paper '+pid},lambda:self.now)
 def tearDown(self): self.tmp.cleanup()
 def beat(self,sid='a'*32,pid='paper',active=True): return self.t.heartbeat({'session_id':sid,'paper_id':pid,'active':active})
 def test_checkin_unique(self):
  self.assertTrue(self.t.checkin()['new']); self.assertFalse(self.t.checkin()['new']); self.assertEqual(self.t.summary()['total_checkins'],1)
 def test_streak_and_gap(self):
  self.now-=timedelta(days=2); self.t.checkin(); self.now+=timedelta(days=1); self.t.checkin(); self.now+=timedelta(days=1); self.assertEqual(self.t.summary()['current_streak'],2); self.t.checkin(); self.assertEqual(self.t.summary()['current_streak'],3); self.now+=timedelta(days=2); self.assertEqual(self.t.summary()['current_streak'],0); self.assertEqual(self.t.summary()['longest_streak'],3)
 def test_completions_month_and_undo(self):
  self.t.complete('p',True); self.t.complete('p',True); self.assertEqual(self.t.summary()['month_completed'],1); self.assertEqual(self.t.summary()['month_read'],1); self.now=self.now.replace(month=12); self.t.complete('p',True); self.assertEqual(self.t.summary()['month_completed'],0); self.assertEqual(self.t.summary('2026-11')['month_completed'],1); self.t.complete('p',False); self.assertEqual(self.t.summary('2026-11')['month_completed'],0)
 def test_no_import_backfill(self): self.assertEqual(self.t.summary()['month_read'],0)
 def test_activity_threshold_and_hidden(self):
  self.beat(); self.now+=timedelta(seconds=15); self.beat(); self.assertEqual(self.t.summary()['month_read'],0); self.now+=timedelta(seconds=15); self.beat(); s=self.t.summary(); self.assertEqual(s['month_read'],1); self.assertTrue(s['checked_today']); self.now+=timedelta(seconds=15); self.beat(active=False); self.now+=timedelta(minutes=5); self.beat(); self.assertEqual(self.t.summary()['month_seconds'],30)
 def test_multiple_tabs_deduplicate(self):
  self.beat(); self.beat('b'*32); self.now+=timedelta(seconds=15); self.beat(); self.beat('b'*32); self.assertEqual(self.t.summary()['month_seconds'],15)
 def test_midnight(self):
  self.now=self.now.replace(day=30,hour=23,minute=59,second=50); self.beat(); self.now+=timedelta(seconds=20); self.beat(); self.assertEqual(self.t.summary('2026-11')['month_seconds'],10); self.assertEqual(self.t.summary()['month_seconds'],10)
 def test_pause_and_goal_validation(self):
  self.t.update_settings({'auto_track':False,'monthly_goal':7}); self.beat(); self.now+=timedelta(seconds=15); self.beat(); self.assertEqual(self.t.summary()['month_seconds'],0); self.assertEqual(self.t.summary()['settings']['monthly_goal'],7)
  for goal in [0,101,True,'4']:
   with self.assertRaises(ValueError):self.t.update_settings({'monthly_goal':goal})
 def test_calendar_leap_and_csv(self):
  self.assertEqual(len(self.t.summary('2024-02')['days']),29); self.t.checkin(); self.assertIn('2026-11-03',self.t.export_csv('2026-11'))
  with self.assertRaises(ValueError): self.t.summary('2027-01')
if __name__=='__main__':unittest.main(verbosity=2)
