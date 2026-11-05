"""Independent local study statistics plugin. No model calls or network access."""
import calendar, csv, io, json, math, re, sqlite3
from contextlib import contextmanager
from datetime import datetime, date, timedelta
from pathlib import Path
from flask import Blueprint, request, jsonify, send_from_directory, Response

class StudyTracker:
    def __init__(self,data_path,paper_loader,clock=None):
        self.data_path=data_path; self.paper_loader=paper_loader
        self.clock=clock or (lambda:datetime.now().astimezone())
    @contextmanager
    def db(self):
        path=Path(self.data_path())/'study_tracker.sqlite3'; path.parent.mkdir(parents=True,exist_ok=True)
        db=sqlite3.connect(path,timeout=10); db.row_factory=sqlite3.Row
        try:
            db.executescript('''
            CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY,value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS checkins (day TEXT PRIMARY KEY,reason TEXT NOT NULL,at REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS activity (day TEXT NOT NULL,pid TEXT NOT NULL,title TEXT NOT NULL,seconds REAL NOT NULL DEFAULT 0,PRIMARY KEY(day,pid));
            CREATE TABLE IF NOT EXISTS completions (pid TEXT PRIMARY KEY,day TEXT NOT NULL,title TEXT NOT NULL,at REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS sessions (sid TEXT PRIMARY KEY,pid TEXT NOT NULL,last_at REAL NOT NULL,active INTEGER NOT NULL);
            ''')
            db.execute('BEGIN IMMEDIATE'); yield db; db.commit()
        except Exception: db.rollback(); raise
        finally: db.close()
    def settings(self,db):
        values={r['key']:r['value'] for r in db.execute('SELECT * FROM settings')}
        return {'daily_goal':int(values.get('daily_goal','1')),'monthly_goal':int(values.get('monthly_goal','4')),'auto_track':values.get('auto_track','true')=='true'}
    def update_settings(self,v):
        with self.db() as db:
            if 'daily_goal' in v:
                goal=v['daily_goal']
                if isinstance(goal,bool) or not isinstance(goal,int) or not 1<=goal<=100: raise ValueError('Daily goal must be an integer from 1 to 100')
                db.execute('INSERT OR REPLACE INTO settings VALUES (?,?)',('daily_goal',str(goal)))
            if 'monthly_goal' in v:
                goal=v['monthly_goal']
                if isinstance(goal,bool) or not isinstance(goal,int) or not 1<=goal<=100: raise ValueError('月度目标需要是 1 至 100 篇的整数。')
                db.execute('INSERT OR REPLACE INTO settings VALUES (?,?)',('monthly_goal',str(goal)))
            if 'auto_track' in v:
                if not isinstance(v['auto_track'],bool): raise ValueError('自动统计开关无效。')
                db.execute('INSERT OR REPLACE INTO settings VALUES (?,?)',('auto_track','true' if v['auto_track'] else 'false'))
                db.execute('UPDATE sessions SET active=0')
            return self.settings(db)
    def checkin(self):
        now=self.clock(); day=now.date().isoformat()
        with self.db() as db:
            result=db.execute('INSERT OR IGNORE INTO checkins VALUES (?,?,?)',(day,'manual',now.timestamp()))
            return {'day':day,'new':result.rowcount==1,'checked':True}
    def complete(self,pid,completed):
        if not isinstance(completed,bool): raise ValueError('读完状态无效。')
        p=self.paper_loader(pid); now=self.clock(); day=now.date().isoformat()
        with self.db() as db:
            if completed:
                db.execute('INSERT OR IGNORE INTO completions VALUES (?,?,?,?)',(pid,day,p['title'],now.timestamp()))
                db.execute('INSERT OR IGNORE INTO checkins VALUES (?,?,?)',(day,'completed',now.timestamp()))
            else: db.execute('DELETE FROM completions WHERE pid=?',(pid,))
            return {'completed':completed,'id':pid}
    def heartbeat(self,v):
        sid=v.get('session_id',''); pid=v.get('paper_id',''); active=v.get('active')
        if not re.fullmatch('[a-f0-9]{32}',str(sid)) or not isinstance(active,bool): raise ValueError('阅读会话格式无效。')
        p=self.paper_loader(pid); now=self.clock(); ts=now.timestamp(); credited=0
        with self.db() as db:
            enabled=self.settings(db)['auto_track']; active=active and enabled
            last=db.execute('SELECT * FROM sessions WHERE sid=?',(sid,)).fetchone()
            if active and last and last['active'] and last['pid']==pid and 0<ts-last['last_at']<=45:
                marker=db.execute("SELECT value FROM settings WHERE key='last_credit'").fetchone()
                start=max(last['last_at'],float(marker['value']) if marker else last['last_at'])
                # Count at most the actual observed interval; no client-supplied duration.
                if start<ts:
                    seconds=min(ts-start,30.0); start=ts-seconds
                    midnight=now.replace(hour=0,minute=0,second=0,microsecond=0).timestamp()
                    segments=[]
                    if start<midnight: segments.append(((now.date()-timedelta(days=1)).isoformat(),midnight-start))
                    segments.append((now.date().isoformat(),ts-max(start,midnight)))
                    for day,amount in segments:
                        if amount<=0: continue
                        db.execute('INSERT INTO activity VALUES (?,?,?,?) ON CONFLICT(day,pid) DO UPDATE SET seconds=seconds+excluded.seconds,title=excluded.title',(day,pid,p['title'],amount))
                        total=db.execute('SELECT SUM(seconds) FROM activity WHERE day=?',(day,)).fetchone()[0]
                        if total>=30: db.execute('INSERT OR IGNORE INTO checkins VALUES (?,?,?)',(day,'reading',ts))
                        credited+=amount
                    db.execute('INSERT OR REPLACE INTO settings VALUES (?,?)',('last_credit',str(ts)))
            db.execute('INSERT OR REPLACE INTO sessions VALUES (?,?,?,?)',(sid,pid,ts,int(active)))
            db.execute('DELETE FROM sessions WHERE last_at<?',(ts-86400*2,))
        return {'seconds_added':round(credited,2),'auto_track':enabled}
    def summary(self,month=None):
        self.generate_reviews()
        now=self.clock(); today=now.date(); month=month or today.strftime('%Y-%m')
        try:
            if not re.fullmatch(r'\d{4}-\d{2}',month): raise ValueError()
            first=date.fromisoformat(month+'-01')
        except Exception: raise ValueError('月份格式应为 YYYY-MM。')
        if first>today.replace(day=1): raise ValueError('还没有未来月份的学习记录。')
        with self.db() as db:
            settings=self.settings(db); checkins=[dict(r) for r in db.execute('SELECT * FROM checkins ORDER BY day')]
            activity=[dict(r) for r in db.execute('SELECT * FROM activity WHERE day LIKE ? ORDER BY day DESC',(month+'-%',))]
            completed=[dict(r) for r in db.execute('SELECT * FROM completions ORDER BY at DESC')]
        days_set={r['day'] for r in checkins}; cursor=today if today.isoformat() in days_set else today-timedelta(days=1); streak=0
        while cursor.isoformat() in days_set: streak+=1; cursor-=timedelta(days=1)
        longest=0; run=0; previous=None
        for day in sorted(days_set):
            d=date.fromisoformat(day); run=run+1 if previous and d-previous==timedelta(days=1) else 1; longest=max(longest,run); previous=d
        monthly_completions=[r for r in completed if r['day'].startswith(month)]
        per_paper={}
        for a in activity: per_paper[a['pid']]=per_paper.get(a['pid'],0)+a['seconds']
        read_ids={pid for pid,seconds in per_paper.items() if seconds>=30}|{r['pid'] for r in monthly_completions}
        check_by={r['day']:r for r in checkins}; days=[]
        for n in range(1,calendar.monthrange(first.year,first.month)[1]+1):
            day=first.replace(day=n).isoformat(); active=[r for r in activity if r['day']==day]; done=[r for r in monthly_completions if r['day']==day]
            seconds=sum(r['seconds'] for r in active)
            days.append({'day':day,'checked':day in check_by,'reason':check_by.get(day,{}).get('reason'),'seconds':int(seconds),'papers':[{'id':r['pid'],'title':r['title'],'seconds':int(r['seconds'])} for r in active],'completed':[{'id':r['pid'],'title':r['title']} for r in done],'read_count':len({r['pid'] for r in active if r['seconds']>=30}|{r['pid'] for r in done}),'completed_count':len(done),'future':day>today.isoformat()})
        return {'month':month,'today':today.isoformat(),'timezone':now.tzname(),'utc_offset':now.strftime('%z'),'checked_today':today.isoformat() in days_set,'current_streak':streak,'longest_streak':longest,'total_checkins':len(checkins),'month_checkins':sum(d['checked'] for d in days),'month_read':len(read_ids),'month_completed':len(monthly_completions),'month_seconds':int(sum(r['seconds'] for r in activity)),'completed_ids':[r['pid'] for r in completed],'settings':settings,'days':days,'week_start':first.weekday()}
    def generate_reviews(self):
        today=self.clock().date().isoformat();folder=Path(self.data_path())/'daily_reviews';folder.mkdir(exist_ok=True)
        with self.db() as db:
            dates=[r[0] for r in db.execute('SELECT day FROM activity WHERE day<? UNION SELECT day FROM completions WHERE day<? UNION SELECT day FROM checkins WHERE day<? ORDER BY day',(today,today,today))]
            for day in dates:
                target=folder/(day+'.md')
                if target.exists():continue
                activity=[dict(r) for r in db.execute('SELECT * FROM activity WHERE day=? ORDER BY seconds DESC',(day,))]
                done=[dict(r) for r in db.execute('SELECT * FROM completions WHERE day=?',(day,))]
                records={r['pid']:r for r in activity}
                for r in done:records.setdefault(r['pid'],r|{'seconds':0})
                finished={r['pid'] for r in done};read={r['pid'] for r in activity if r['seconds']>=30}|finished
                lines=['# '+day+' ????','', '?????'+self.clock().isoformat(),'','?? '+str(len(read))+' ? ? ???? '+str(len(done))+' ? ? ???? '+str(round(sum(r['seconds'] for r in activity)/60,1))+' ??','', '?????????????????????????????????? AI ???????','']
                for pid,r in records.items():
                    lines+=['## '+r['title'],'','???'+('????' if pid in finished else '???')+' ? ?? '+str(round(r['seconds']/60,1))+' ??','']
                    try:p=self.paper_loader(pid)
                    except Exception:
                        lines+=['???????????????',''];continue
                    if p.get('notes'):lines+=['### ???????????','',p['notes'],'']
                    for h in (p.get('highlights') or [])[-20:]:lines+=['> [p.'+str(h.get('page','?'))+'] '+str(h.get('quote','')).replace('\n',' '),str(h.get('note','')),'']
                    if p.get('chat'):
                        lines+=['### ??????? 10 ????????','']
                        for chat in p['chat'][-10:]:lines+=['- '+str(chat.get('q','')).replace('\n',' ')]
                    lines+=['','### ????','- ??????????????????','- ????????????????????','']
                if not records:lines+=['????????????????????']
                tmp=target.with_suffix('.tmp');tmp.write_text('\n'.join(lines),encoding='utf-8');tmp.replace(target)
        return folder

    def export_csv(self,month):
        s=self.summary(month); out=io.StringIO(); writer=csv.writer(out); writer.writerow(['日期','已签到','签到来源','阅读秒数','阅读文献','读完文献'])
        def cell(value): return "'"+value if value.startswith(('=','+','-','@','\t','\r','\n')) else value
        for d in s['days']:
            if not (d['checked'] or d['seconds'] or d['completed']): continue
            writer.writerow([d['day'],'是' if d['checked'] else '否',{'manual':'主动签到','reading':'阅读达标','completed':'标记读完'}.get(d['reason'],''),d['seconds'],cell(' / '.join(p['title'] for p in d['papers'])),cell(' / '.join(p['title'] for p in d['completed']))])
        return '\ufeff'+out.getvalue()

def install(app,m):
    tracker=StudyTracker(lambda:m.DATA,m.paper); app.extensions['study_tracker']=tracker
    bp=Blueprint('study_tracker',__name__)
    @bp.get('/plugins/study-tracker/<path:name>')
    def assets(name): return send_from_directory(Path(__file__).parent/'static',name)
    @bp.get('/api/study/summary')
    def summary(): return jsonify(tracker.summary(request.args.get('month')))
    @bp.post('/api/study/checkin')
    def checkin(): return jsonify(tracker.checkin())
    @bp.post('/api/study/settings')
    def settings(): return jsonify(tracker.update_settings(request.json or {}))
    @bp.post('/api/study/heartbeat')
    def heartbeat(): return jsonify(tracker.heartbeat(request.json or {}))
    @bp.post('/api/study/papers/<pid>/complete')
    def complete(pid): return jsonify(tracker.complete(pid,(request.json or {}).get('completed')))
    @bp.get('/api/study/export')
    def export():
        month=request.args.get('month'); text=tracker.export_csv(month)
        return Response(text,mimetype='text/csv',headers={'Content-Disposition':'attachment; filename="pawsec-study.csv"'})
    @bp.get('/api/study/reviews')
    def reviews():
        folder=tracker.generate_reviews()
        return jsonify([{'day':p.stem,'url':'/api/study/reviews/'+p.stem} for p in sorted(folder.glob('*.md'),reverse=True)])
    @bp.get('/api/study/reviews/<day>')
    def review(day):
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}',day):raise ValueError('Invalid day')
        folder=tracker.generate_reviews()
        return send_from_directory(folder,day+'.md',as_attachment=True,download_name='PawSec-review-'+day+'.md')
    app.register_blueprint(bp)
    import threading
    def review_worker():
        while True:
            try:tracker.generate_reviews()
            except Exception:pass
            threading.Event().wait(60)
    # Only the actual local server runs a background scheduler, not imports or tests.
    app.extensions.setdefault('background_workers',[]).append(('daily-review',review_worker))
    if m.__name__=='__main__':threading.Thread(target=review_worker,daemon=True,name='daily-review').start()

