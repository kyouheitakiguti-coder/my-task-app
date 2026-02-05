# app.py
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os
import calendar

st.set_page_config(
    page_title="スマートデイリープランナー", 
    page_icon="🎯", 
    layout="wide"
)

CSV_FILE = "tasks.csv"

def load_tasks():
    if os.path.exists(CSV_FILE):
        df = pd.read_csv(CSV_FILE)
        if df.empty:
            df = pd.DataFrame(columns=["タスク名", "所要時間", "期日", "カテゴリ", "完了", "Type"])
        if not df.empty:
            if "Type" not in df.columns:
                df["Type"] = "Task"
            if "所要時間" not in df.columns:
                df["所要時間"] = 30
            if "完了" not in df.columns:
                df["完了"] = False
            
            df["期日"] = pd.to_datetime(df["期日"])
            df["所要時間"] = df["所要時間"].astype(int)
            df["完了"] = df["完了"].astype(bool)
    else:
        df = pd.DataFrame(columns=["タスク名", "所要時間", "期日", "カテゴリ", "完了", "Type"])
    return df

def save_tasks(df):
    df.to_csv(CSV_FILE, index=False, encoding="utf-8-sig")

def calculate_priority_score(deadline, duration):
    now = datetime.now()
    time_until_deadline = (deadline - now).total_seconds() / 3600
    
    if time_until_deadline <= 0:
        urgency_score = 1000
    else:
        urgency_score = 100 / max(time_until_deadline, 1)
    
    efficiency_score = 50 / max(duration / 60, 0.5)
    
    weight_urgency = 0.7
    weight_efficiency = 0.3
    
    total_score = (urgency_score * weight_urgency) + (efficiency_score * weight_efficiency)
    
    return round(total_score, 2)

if "tasks_df" not in st.session_state:
    st.session_state.tasks_df = load_tasks()

if "edit_mode" not in st.session_state:
    st.session_state.edit_mode = None

st.title("🎯 スマートデイリープランナー")

st.sidebar.header("📝 新規追加")

with st.sidebar.form("add_task_form", clear_on_submit=True):
    item_type = st.radio("タイプ", ["タスク", "予定"], horizontal=True)
    
    task_name = st.text_input("名前", placeholder="例: プレゼン資料作成")
    
    if item_type == "タスク":
        task_duration = st.number_input("所要時間（分）", min_value=5, max_value=480, value=30, step=5)
        task_date = st.date_input("期日（日付）", value=datetime.today())
        task_time = st.time_input("期日（時刻）", value=datetime.now().time())
    else:
        task_duration = 0
        task_date = st.date_input("日付", value=datetime.today())
        task_time = st.time_input("開始時刻", value=datetime.now().time())
    
    task_category = st.selectbox("カテゴリ", ["仕事", "プライベート", "学習", "健康", "その他"])
    
    submitted = st.form_submit_button("➕ 追加", use_container_width=True)
    
    if submitted:
        if task_name.strip() == "":
            st.sidebar.error("名前を入力してください")
        else:
            task_deadline = datetime.combine(task_date, task_time)
            
            new_task = {
                "タスク名": task_name,
                "所要時間": task_duration,
                "期日": task_deadline,
                "カテゴリ": task_category,
                "完了": False if item_type == "タスク" else None,
                "Type": "Task" if item_type == "タスク" else "Event"
            }
            st.session_state.tasks_df = pd.concat(
                [st.session_state.tasks_df, pd.DataFrame([new_task])],
                ignore_index=True
            )
            save_tasks(st.session_state.tasks_df)
            st.sidebar.success(f"✅ 「{task_name}」を追加しました！")

st.sidebar.markdown("---")
st.sidebar.subheader("📊 統計情報")
if not st.session_state.tasks_df.empty:
    total_tasks = len(st.session_state.tasks_df[st.session_state.tasks_df["Type"] == "Task"])
    completed_tasks = st.session_state.tasks_df[(st.session_state.tasks_df["Type"] == "Task") & (st.session_state.tasks_df["完了"] == True)].shape[0]
    pending_tasks = total_tasks - completed_tasks
    total_events = len(st.session_state.tasks_df[st.session_state.tasks_df["Type"] == "Event"])
    
    st.sidebar.metric("タスク数", total_tasks)
    st.sidebar.metric("完了", completed_tasks)
    st.sidebar.metric("未完了", pending_tasks)
    st.sidebar.metric("予定数", total_events)
    
    if total_tasks > 0:
        completion_rate = (completed_tasks / total_tasks) * 100
        st.sidebar.progress(completion_rate / 100)
        st.sidebar.caption(f"完了率: {completion_rate:.1f}%")
else:
    st.sidebar.info("データがありません")

st.header("📅 今日の予定")

if not st.session_state.tasks_df.empty:
    today = datetime.now().date()
    df_events_today = st.session_state.tasks_df[
        (st.session_state.tasks_df["Type"] == "Event") & 
        (st.session_state.tasks_df["期日"].dt.date == today)
    ].copy()
    
    if not df_events_today.empty:
        df_events_today = df_events_today.sort_values("期日")
        
        for idx, (original_idx, row) in enumerate(df_events_today.iterrows(), 1):
            if st.session_state.edit_mode == f"event_today_{original_idx}":
                with st.form(key=f"edit_form_event_today_{original_idx}"):
                    st.markdown("### ✏️ 編集中")
                    edit_name = st.text_input("名前", value=row["タスク名"])
                    edit_date = st.date_input("日付", value=row["期日"].date())
                    edit_time = st.time_input("開始時刻", value=row["期日"].time())
                    edit_category = st.selectbox("カテゴリ", ["仕事", "プライベート", "学習", "健康", "その他"], 
                                                 index=["仕事", "プライベート", "学習", "健康", "その他"].index(row["カテゴリ"]))
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.form_submit_button("💾 保存", use_container_width=True):
                            st.session_state.tasks_df.loc[original_idx, "タスク名"] = edit_name
                            st.session_state.tasks_df.loc[original_idx, "期日"] = datetime.combine(edit_date, edit_time)
                            st.session_state.tasks_df.loc[original_idx, "カテゴリ"] = edit_category
                            save_tasks(st.session_state.tasks_df)
                            st.session_state.edit_mode = None
                            st.rerun()
                    with col2:
                        if st.form_submit_button("❌ キャンセル", use_container_width=True):
                            st.session_state.edit_mode = None
                            st.rerun()
            else:
                with st.container():
                    col1, col2, col3, col4 = st.columns([0.5, 6, 1, 1])
                    
                    with col1:
                        st.markdown(f"**{idx}**")
                    
                    with col2:
                        st.markdown(f"### 📌 {row['タスク名']}")
                        st.write(f"📂 {row['カテゴリ']} | ⏰ {row['期日'].strftime('%H:%M')}")
                    
                    with col3:
                        if st.button("✏️", key=f"edit_event_today_{original_idx}"):
                            st.session_state.edit_mode = f"event_today_{original_idx}"
                            st.rerun()
                    
                    with col4:
                        if st.button("🗑️", key=f"del_event_today_{original_idx}"):
                            st.session_state.tasks_df = st.session_state.tasks_df.drop(original_idx).reset_index(drop=True)
                            save_tasks(st.session_state.tasks_df)
                            st.rerun()
                    
                    st.divider()
    else:
        st.info("今日の予定はありません")
else:
    st.info("予定を追加してください")

st.header("🔥 優先タスク TOP3")

if not st.session_state.tasks_df.empty:
    df_pending = st.session_state.tasks_df[
        (st.session_state.tasks_df["Type"] == "Task") & 
        (st.session_state.tasks_df["完了"] == False)
    ].copy()
    
    if not df_pending.empty:
        df_pending["優先度スコア"] = df_pending.apply(
            lambda row: calculate_priority_score(row["期日"], row["所要時間"]),
            axis=1
        )
        df_pending = df_pending.sort_values("優先度スコア", ascending=False)
        top_tasks = df_pending.head(3)
        
        for idx, (original_idx, row) in enumerate(top_tasks.iterrows(), 1):
            if st.session_state.edit_mode == f"top_task_{original_idx}":
                with st.form(key=f"edit_form_top_{original_idx}"):
                    st.markdown("### ✏️ 編集中")
                    edit_name = st.text_input("タスク名", value=row["タスク名"])
                    edit_duration = st.number_input("所要時間（分）", min_value=5, max_value=480, value=int(row["所要時間"]), step=5)
                    edit_date = st.date_input("期日（日付）", value=row["期日"].date())
                    edit_time = st.time_input("期日（時刻）", value=row["期日"].time())
                    edit_category = st.selectbox("カテゴリ", ["仕事", "プライベート", "学習", "健康", "その他"], 
                                                 index=["仕事", "プライベート", "学習", "健康", "その他"].index(row["カテゴリ"]))
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.form_submit_button("💾 保存", use_container_width=True):
                            st.session_state.tasks_df.loc[original_idx, "タスク名"] = edit_name
                            st.session_state.tasks_df.loc[original_idx, "所要時間"] = edit_duration
                            st.session_state.tasks_df.loc[original_idx, "期日"] = datetime.combine(edit_date, edit_time)
                            st.session_state.tasks_df.loc[original_idx, "カテゴリ"] = edit_category
                            save_tasks(st.session_state.tasks_df)
                            st.session_state.edit_mode = None
                            st.rerun()
                    with col2:
                        if st.form_submit_button("❌ キャンセル", use_container_width=True):
                            st.session_state.edit_mode = None
                            st.rerun()
            else:
                time_left = row["期日"] - datetime.now()
                hours_left = time_left.total_seconds() / 3600
                
                if hours_left < 0:
                    color = "🔴"
                    urgency_text = "**期限切れ！**"
                elif hours_left < 24:
                    color = "🟠"
                    urgency_text = f"残り {int(hours_left)}時間"
                elif hours_left < 48:
                    color = "🟡"
                    urgency_text = f"残り {int(hours_left / 24)}日"
                else:
                    color = "🟢"
                    urgency_text = f"残り {int(hours_left / 24)}日"
                
                with st.container():
                    col1, col2, col3, col4 = st.columns([0.5, 4.5, 2, 0.5])
                    
                    with col1:
                        st.markdown(f"## {idx}")
                    
                    with col2:
                        st.markdown(f"### {color} {row['タスク名']}")
                        st.write(f"📂 {row['カテゴリ']} | ⏱️ {row['所要時間']}分 | 📅 {row['期日'].strftime('%m/%d %H:%M')}")
                    
                    with col3:
                        st.metric("優先度スコア", f"{row['優先度スコア']:.1f}")
                        st.caption(urgency_text)
                    
                    with col4:
                        if st.button("✏️", key=f"edit_top_task_{original_idx}"):
                            st.session_state.edit_mode = f"top_task_{original_idx}"
                            st.rerun()
                    
                    st.divider()
    else:
        st.success("🎉 すべてのタスクが完了しています！")
else:
    st.info("タスクを追加してください")

st.markdown("---")

tab1, tab2 = st.tabs(["📋 全リスト", "📅 カレンダー表示"])

with tab1:
    subtab1, subtab2, subtab3 = st.tabs(["未完了タスク", "完了済みタスク", "予定"])
    
    with subtab1:
        if not st.session_state.tasks_df.empty:
            df_pending = st.session_state.tasks_df[
                (st.session_state.tasks_df["Type"] == "Task") & 
                (st.session_state.tasks_df["完了"] == False)
            ].copy()
            
            if not df_pending.empty:
                df_pending["優先度スコア"] = df_pending.apply(
                    lambda row: calculate_priority_score(row["期日"], row["所要時間"]),
                    axis=1
                )
                df_pending = df_pending.sort_values("優先度スコア", ascending=False)
                
                for original_idx in df_pending.index:
                    row = st.session_state.tasks_df.loc[original_idx]
                    
                    if st.session_state.edit_mode == f"pending_{original_idx}":
                        with st.form(key=f"edit_form_pending_{original_idx}"):
                            st.markdown("### ✏️ 編集中")
                            edit_name = st.text_input("タスク名", value=row["タスク名"])
                            edit_duration = st.number_input("所要時間（分）", min_value=5, max_value=480, value=int(row["所要時間"]), step=5)
                            edit_date = st.date_input("期日（日付）", value=row["期日"].date())
                            edit_time = st.time_input("期日（時刻）", value=row["期日"].time())
                            edit_category = st.selectbox("カテゴリ", ["仕事", "プライベート", "学習", "健康", "その他"], 
                                                         index=["仕事", "プライベート", "学習", "健康", "その他"].index(row["カテゴリ"]))
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.form_submit_button("💾 保存", use_container_width=True):
                                    st.session_state.tasks_df.loc[original_idx, "タスク名"] = edit_name
                                    st.session_state.tasks_df.loc[original_idx, "所要時間"] = edit_duration
                                    st.session_state.tasks_df.loc[original_idx, "期日"] = datetime.combine(edit_date, edit_time)
                                    st.session_state.tasks_df.loc[original_idx, "カテゴリ"] = edit_category
                                    save_tasks(st.session_state.tasks_df)
                                    st.session_state.edit_mode = None
                                    st.rerun()
                            with col2:
                                if st.form_submit_button("❌ キャンセル", use_container_width=True):
                                    st.session_state.edit_mode = None
                                    st.rerun()
                    else:
                        col1, col2, col3, col4 = st.columns([0.5, 5.5, 1, 1])
                        
                        with col1:
                            completed = st.checkbox("", key=f"check_{original_idx}", value=False)
                            if completed:
                                st.session_state.tasks_df.loc[original_idx, "完了"] = True
                                save_tasks(st.session_state.tasks_df)
                                st.rerun()
                        
                        with col2:
                            st.markdown(f"**{row['タスク名']}**")
                            st.caption(f"📂 {row['カテゴリ']} | ⏱️ {row['所要時間']}分 | 📅 {row['期日'].strftime('%Y/%m/%d %H:%M')}")
                        
                        with col3:
                            if st.button("✏️", key=f"edit_pending_{original_idx}"):
                                st.session_state.edit_mode = f"pending_{original_idx}"
                                st.rerun()
                        
                        with col4:
                            if st.button("🗑️", key=f"del_{original_idx}"):
                                st.session_state.tasks_df = st.session_state.tasks_df.drop(original_idx).reset_index(drop=True)
                                save_tasks(st.session_state.tasks_df)
                                st.rerun()
                        
                        st.divider()
            else:
                st.info("未完了のタスクはありません")
        else:
            st.info("タスクがありません")
    
    with subtab2:
        if not st.session_state.tasks_df.empty:
            df_completed = st.session_state.tasks_df[
                (st.session_state.tasks_df["Type"] == "Task") & 
                (st.session_state.tasks_df["完了"] == True)
            ].copy()
            
            if not df_completed.empty:
                for original_idx in df_completed.index:
                    row = st.session_state.tasks_df.loc[original_idx]
                    
                    col1, col2, col3 = st.columns([0.5, 6, 1.5])
                    
                    with col1:
                        st.markdown("✅")
                    
                    with col2:
                        st.markdown(f"~~{row['タスク名']}~~")
                        st.caption(f"📂 {row['カテゴリ']} | ⏱️ {row['所要時間']}分")
                    
                    with col3:
                        if st.button("🗑️", key=f"del_comp_{original_idx}"):
                            st.session_state.tasks_df = st.session_state.tasks_df.drop(original_idx).reset_index(drop=True)
                            save_tasks(st.session_state.tasks_df)
                            st.rerun()
                    
                    st.divider()
            else:
                st.info("完了済みのタスクはありません")
        else:
            st.info("タスクがありません")
    
    with subtab3:
        if not st.session_state.tasks_df.empty:
            df_events = st.session_state.tasks_df[st.session_state.tasks_df["Type"] == "Event"].copy()
            
            if not df_events.empty:
                df_events = df_events.sort_values("期日", ascending=False)
                
                for original_idx in df_events.index:
                    row = st.session_state.tasks_df.loc[original_idx]
                    
                    if st.session_state.edit_mode == f"event_{original_idx}":
                        with st.form(key=f"edit_form_event_{original_idx}"):
                            st.markdown("### ✏️ 編集中")
                            edit_name = st.text_input("名前", value=row["タスク名"])
                            edit_date = st.date_input("日付", value=row["期日"].date())
                            edit_time = st.time_input("開始時刻", value=row["期日"].time())
                            edit_category = st.selectbox("カテゴリ", ["仕事", "プライベート", "学習", "健康", "その他"], 
                                                         index=["仕事", "プライベート", "学習", "健康", "その他"].index(row["カテゴリ"]))
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.form_submit_button("💾 保存", use_container_width=True):
                                    st.session_state.tasks_df.loc[original_idx, "タスク名"] = edit_name
                                    st.session_state.tasks_df.loc[original_idx, "期日"] = datetime.combine(edit_date, edit_time)
                                    st.session_state.tasks_df.loc[original_idx, "カテゴリ"] = edit_category
                                    save_tasks(st.session_state.tasks_df)
                                    st.session_state.edit_mode = None
                                    st.rerun()
                            with col2:
                                if st.form_submit_button("❌ キャンセル", use_container_width=True):
                                    st.session_state.edit_mode = None
                                    st.rerun()
                    else:
                        col1, col2, col3, col4 = st.columns([0.5, 5.5, 1, 1])
                        
                        with col1:
                            st.markdown("📌")
                        
                        with col2:
                            st.markdown(f"**{row['タスク名']}**")
                            st.caption(f"📂 {row['カテゴリ']} | 📅 {row['期日'].strftime('%Y/%m/%d %H:%M')}")
                        
                        with col3:
                            if st.button("✏️", key=f"edit_event_{original_idx}"):
                                st.session_state.edit_mode = f"event_{original_idx}"
                                st.rerun()
                        
                        with col4:
                            if st.button("🗑️", key=f"del_event_{original_idx}"):
                                st.session_state.tasks_df = st.session_state.tasks_df.drop(original_idx).reset_index(drop=True)
                                save_tasks(st.session_state.tasks_df)
                                st.rerun()
                        
                        st.divider()
            else:
                st.info("予定がありません")
        else:
            st.info("予定がありません")

with tab2:
    st.header("📅 カレンダー表示")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if "calendar_date" not in st.session_state:
            st.session_state.calendar_date = datetime.now()
        
        selected_month = st.date_input(
            "表示月",
            value=st.session_state.calendar_date,
            key="month_selector"
        )
        st.session_state.calendar_date = selected_month
    
    year = selected_month.year
    month = selected_month.month
    
    cal = calendar.monthcalendar(year, month)
    
    month_name = f"{year}年 {month}月"
    st.subheader(month_name)
    
    if not st.session_state.tasks_df.empty:
        df_month = st.session_state.tasks_df.copy()
        df_month["日付"] = df_month["期日"].dt.date
    else:
        df_month = pd.DataFrame()
    
    weekdays = ["月", "火", "水", "木", "金", "土", "日"]
    cols = st.columns(7)
    for i, day in enumerate(weekdays):
        with cols[i]:
            st.markdown(f"**{day}**")
    
    for week in cal:
        cols = st.columns(7)
        for i, day in enumerate(week):
            with cols[i]:
                if day == 0:
                    st.markdown("")
                else:
                    current_date = datetime(year, month, day).date()
                    
                    if not df_month.empty:
                        day_items = df_month[df_month["日付"] == current_date]
                        pending_tasks = day_items[
                            (day_items["Type"] == "Task") & 
                            (day_items["完了"] == False)
                        ]
                        events = day_items[day_items["Type"] == "Event"]
                        
                        task_count = len(pending_tasks)
                        event_count = len(events)
                    else:
                        task_count = 0
                        event_count = 0
                    
                    if current_date == datetime.now().date():
                        st.markdown(f"**:blue[{day}]**")
                    else:
                        st.markdown(f"{day}
