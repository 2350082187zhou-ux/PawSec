import {rows} from './translations.js';
export const extraRows=`
主动盖下的小爪印|A pawprint you checked in yourself|自分で残した足あと|직접 남긴 발자국
🐾 主动盖下的小爪印|🐾 You checked in today|🐾 自分で残した足あと|🐾 직접 남긴 발자국
🐾 阅读活动达标，自动签到|🐾 Automatically checked in after reading|🐾 読書活動で自動チェックイン|🐾 읽기 활동으로 자동 출석
🐾 标记读完，为努力留念|🐾 Finished a paper and checked in|🐾 読了を記念してチェックイン|🐾 완독을 기념한 출석
☁ 今天还没有签到记录|☁ No check-in on this day|☁ この日はまだ記録なし|☁ 이날 출석 기록 없음
完成首次签到|Your first check-in|初めてのチェックイン|첫 출석 완료
连续签到达到3天|Reach a 3-day streak|3日連続を達成|3일 연속 출석
确认读完一篇论文|Mark one paper finished|1本の読了を登録|논문 한 편 완독 표시
本月读完达到目标|Reach this month's goal|今月の目標を達成|이번 달 목표 달성
小目标达成啦，汪替你开心！|Goal reached. Your effort paid off!|目標達成！よく頑張ったね。|목표 달성! 노력이 결실을 맺었어요.
签到加载中|Loading check-in|記録を読み込み中|출석 불러오는 중
正在加载…|Loading…|読み込み中…|불러오는 중…
正在加载设置…|Loading settings…|設定を読み込み中…|설정 불러오는 중…
加载今日记录…|Loading today's journal…|今日の記録を読み込み中…|오늘 기록 불러오는 중…
学习记录暂时无法加载：|Could not load study records:|学習記録を読み込めません：|학습 기록을 불러올 수 없어요:
重试|Retry|再試行|다시 시도
论文阅读|Reading|論文閲覧|논문 읽기
展示工坊|Presentation studio|発表スタジオ|발표 스튜디오
我的模型 / My model|My model|マイモデル|내 모델
API protocol|API protocol|APIプロトコル|API 프로토콜
OpenAI-compatible · Chat Completions|OpenAI-compatible · Chat Completions|OpenAI互換・Chat Completions|OpenAI 호환 · Chat Completions
•••••••• (leave blank to keep)|•••••••• (leave blank to keep)|••••••••（空欄で保持）|•••••••• (비우면 유지)
保存设置|Save settings|設定を保存|설정 저장
Search keywords|Search keywords|検索キーワード|검색 키워드
未说明|Not reported|記載なし|명시되지 않음
共同方向：|Shared topics:|共通トピック：|공통 주제:
未找到公开 PDF，可在来源页面查找|No public PDF found; check the source page|公開PDFなし。掲載元を確認してください|공개 PDF를 찾지 못했어요. 출처 페이지를 확인하세요
尚未配置模型|No model configured|モデル未設定|모델 미설정
在模型连接中配置你的 API|Configure your API in Model connections|モデル接続でAPIを設定|모델 연결에서 API를 설정하세요
分析后会显示作者主张、AI 的贡献评价、原句证据和网安威胁模型。|Analysis shows author claims, AI assessments, original evidence and the threat model.|著者の主張、AI評価、原文の根拠、脅威モデルを表示します。|분석 후 저자 주장, AI 평가, 원문 근거, 위협 모델이 표시됩니다.
🐶 从威胁模型开始读，再看方法和实验证据。你可以生成全文精读，或直接在原文上标记疑问。|🐶 Start with the threat model, then inspect methods and evidence. Generate a review or highlight a question.|🐶 脅威モデルから読み、手法と実験を確認しよう。精読レポートや原文マーカーも使えます。|🐶 위협 모델부터 읽고 방법과 근거를 확인해요. 정독 보고서를 만들거나 원문에 질문을 표시해 보세요.
在左侧 PDF 或文字视图中选中文字，保存你的第一处高亮。|Select text in the PDF or text view to save your first highlight.|左のPDFやテキストで文字を選び、最初のマーカーを残そう。|PDF 또는 텍스트에서 글을 선택해 첫 강조를 저장하세요.
书架里暂时没有其他文献。可以先寻找在线论文，导入后再比较。|No other local papers yet. Find and import a paper before comparing.|他の論文がまだありません。検索して追加後に比較できます。|서재에 다른 논문이 없어요. 온라인에서 찾아 가져온 후 비교하세요.
自动填充会取每项前 220 字，请补齐必要条件与引用。已有重点不会自动覆盖。|Auto-fill takes the first 220 characters. Complete conditions and citations. Existing edits are preserved.|自動入力は先頭220文字です。条件と引用を補ってください。既存の編集は保持します。|자동 채움은 앞 220자를 사용합니다. 조건과 인용을 보완하세요. 기존 편집은 유지됩니다.
研究问题|Research question|研究課題|연구 질문
核心贡献（AI 整理，待核验）|Core contribution (AI draft, verify)|主な貢献（AI草案・要確認）|핵심 기여 (AI 초안, 확인 필요)
关键方法|Key method|主要手法|핵심 방법
实验结果|Experimental results|実験結果|실험 결과
局限与边界|Limits and scope|限界と範囲|한계와 범위
复现与启发|Reproduction and insights|再現と示唆|재현 및 시사점
网络安全论文阅读报告|Security paper reading report|セキュリティ論文読書レポート|보안 논문 읽기 보고서
待补充|To be completed|追記待ち|추가 예정
正在打开 PDF…|Opening PDF…|PDFを開いています…|PDF를 여는 중…
准备开始|Preparing|準備中|준비 중
已完成|Completed|完了|완료
正在查找论文…|Searching papers…|論文を検索中…|논문 검색 중…
没有检索结果，试试英文关键词。|No results. Try English keywords.|結果なし。英語のキーワードを試してください。|결과가 없습니다. 영어 키워드를 사용해 보세요.
连接配置已保存。|Connection saved.|接続設定を保存しました。|연결 설정을 저장했어요.
测试中…|Testing…|テスト中…|테스트 중…
PDF 已导入，可以选字高亮或开始精读。|PDF imported. Highlight text or start reviewing.|PDFを追加しました。マーカーや精読を始められます。|PDF를 가져왔어요. 강조하거나 정독을 시작하세요.
阅读笔记已保存|Reading notes saved|ノートを保存しました|읽기 노트를 저장했어요
高亮和批注已保存，可在笔记中回看和下载。|Highlight saved. Review or download it in Notes.|マーカー保存済み。ノートで確認・ダウンロードできます。|강조와 메모를 저장했어요. 노트에서 확인하고 다운로드하세요.
汪正在结合原文思考…|Paw is checking the original text…|ワンが原文を確認中…|멍멍이가 원문을 확인하는 중…
正在准备下载…|Preparing download…|ダウンロード準備中…|다운로드 준비 중…
文件已生成，浏览器开始下载。|File ready. Your browser is downloading it.|ファイル作成済み。ダウンロードを開始します。|파일이 준비되어 브라우저에서 다운로드합니다.
请先选中文字|Select some text first|先にテキストを選択してください|먼저 텍스트를 선택하세요
本页没有可朗读的文字|No text to read aloud on this page|読み上げるテキストがありません|이 페이지에 읽을 텍스트가 없습니다
展示内容已保存，可下载海报和 PPT。|Presentation saved. Download a poster or slides.|発表内容を保存しました。ポスターやPPTを取得できます。|발표 내용을 저장했어요. 포스터 또는 PPT를 다운로드하세요.
🐾 今日签到成功，汪把这份努力收好啦。|🐾 Checked in. Your effort is recorded.|🐾 チェックイン完了。頑張りを記録したよ。|🐾 출석 완료. 오늘의 노력을 기록했어요.
📚 读完一篇啦！这份收获已经记进足迹。|📚 A paper finished! Added to your journal.|📚 一冊読了！学習記録に残したよ。|📚 한 편 완독! 학습 기록에 남겼어요.
已撤销读完记录，阅读活动和签到仍保留。|Completion undone. Activity and check-ins are kept.|読了を取り消しました。活動とチェックインは保持します。|완독 표시를 취소했어요. 활동과 출석 기록은 유지됩니다.
小目标已保存，按自己的节奏来。|Goal saved. Go at your own pace.|目標保存済み。自分のペースで。|목표를 저장했어요. 나만의 속도로 가요.
阅读目标已保存|Reading goal saved|読書目標を保存しました|읽기 목표를 저장했어요
自动阅读统计已暂停|Automatic tracking paused|自動記録を停止しました|자동 읽기 기록을 일시 중지했어요
已恢复前台阅读统计|Foreground tracking resumed|前面での読書記録を再開|전경 읽기 기록을 재개했어요
签到每天只计一次，也可以在累计前台阅读 30 秒后自动签到。每篇论文在所选月份累计阅读活动至少 30 秒，或被你标记读完，计入该月“阅读过”。“读完”由你主动确认，每篇只保留首次读完日期；撤销会移除这条完成记录。导入文件不算读过，过去的阅读不会被自动推测。|One check-in per day, automatic after 30 seconds of foreground reading. A paper counts as read after 30 seconds in the selected month or a manual completion. Completion records the first confirmed date; undo removes it. Imports and past reading are never assumed.|チェックインは1日1回。前面で30秒読むと自動記録します。その月に30秒読んだ論文または読了登録した論文を集計。読了は最初の確認日を保存し、取消で削除。追加しただけの論文や過去の読書は推測しません。|출석은 하루 한 번이며 전경에서 30초 읽으면 자동 기록됩니다. 선택한 달에 30초 이상 읽거나 완독 표시한 논문을 집계합니다. 완독은 최초 확인일을 저장하며 취소 시 삭제됩니다. 가져오기나 과거 읽기는 추정하지 않습니다.
阅读活动每 15 秒记录一次。页面失焦、隐藏，或 2 分钟没有鼠标、键盘、触摸操作时暂停；它是保守的活动时间估算，不代表精确学习时长。多标签重叠时间去重。日期按电脑本地时区计算。修改月目标会同步用于所有月份的展示。|Activity is sampled every 15 seconds. Tracking pauses when unfocused, hidden or idle for 2 minutes. It estimates active time, not exact study time. Overlapping tabs are deduplicated. Dates use the computer timezone. The current goal is shown for all months.|15秒ごとに活動を記録。フォーカスなし・非表示・2分間無操作で停止します。正確な学習時間ではなく活動時間の推定です。複数タブの重複は除外。PCのタイムゾーンを使用し、現在の目標を全月に表示します。|15초마다 활동을 기록하며 초점 해제, 숨김 또는 2분간 무조작 시 중지합니다. 정확한 학습 시간이 아닌 활동 시간 추정치입니다. 겹치는 탭 시간은 중복 제외하고 컴퓨터 시간대를 사용합니다. 현재 목표를 모든 달에 표시합니다.
`;
