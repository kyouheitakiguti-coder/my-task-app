
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os

# ページ設定
st.set_page_config(
    page_title="スマートデイリープランナー", 
    page_icon="🎯", 
    layout="wide"
)

# CSVファイルのパス
CSV_FILE = "tasks.csv"

# CSVファイルの初期化・読み込み
def load_tasks():
    """タスクデータをCSVから読み込む。ファイルがなければ新規作成"""
    if os.path.exists(CSV_FILE):
        df = pd.read_csv(CSV_FILE)
        if df.empty:
            df = pd.DataFrame(columns=["タスク名", "所要時間", "期日", "カテゴリ", "完了"])
        # データ型を適切に変換
        if not df.empty:
            df["期日"] = pd.to_datetime(df["期日"])
            df["所要時間"] = df["所要時間"].astype(int)
            df["完了"] = df["完了"].astype(bool)
    else:
        df = pd.DataFrame(columns=["タスク名", "所要時間", "期日", "カテゴリ", "完了"])
    return df

# CSVファイルに保存
def save_tasks(df):
    """DataFrameをCSVファイルに保存"""
    df.to_csv(CSV_FILE, index=False, encoding="utf-8-sig")

# 優先度スコア計算関数（重要なアルゴリズム部分）
def calculate_priority_score(deadline, duration):
    """
    期日と所要時間から優先度スコアを計算する
    
    Parameters:
    - deadline: タスクの期日（datetime型）
    - duration: タスクの所要時間（分単位）
    
    Returns:
    - score: 優先度スコア（高いほど優先度が高い）
    
    計算ロジック:
    1. 期日までの残り時間が少ないほどスコアが高くなる
    2. 所要時間が短いほどスコアが高くなる（早く片付けられる）
    3. 両方を組み合わせて総合スコアを算出
    """
    now = datetime.now()
    
    # 期日までの残り時間を計算（時間単位）
    time_until_deadline = (deadline - now).total_seconds() / 3600  # 時間に変換
    
    # 期日が過ぎている場合は最高優先度
    if time_until_deadline <= 0:
        urgency_score = 1000  # 超高優先度
    else:
        # 残り時間が少ないほどスコアが高い（逆数を使用）
        # 最大24時間（1日）でクリップして、それ以上は同じ扱い
        urgency_score = 100 / max(time_until_deadline, 1)
    
    # 所要時間スコア: 短いタスクほど高スコア（すぐ終わるものを優先）
    # 最大120分（2時間）でクリップ
    efficiency_score = 50 / max(duration / 60, 0.5)  # 時間単位に変換
    
    # 重み付けして総合スコアを計算
    # 緊急度を重視（重みA = 0.7）、効率性も考慮（重みB = 0.3）
    weight_urgency = 0.7
    weight_efficiency = 0.3
    
    total_score = (urgency_score * weight_urgency) + (efficiency_score * weight_efficiency)
    
    return round(total_score, 2)

# タスクデータの読み込み（セッション状態で管理）
if "tasks_df" not in st.session_state:
    st.session_state.tasks_df = load_tasks()

# アプリのタイトル
st.title("🎯 スマートデイリープランナー")
st.markdown("**AIライクな優先度計算で、最も重要なタスクを自動提案します**")

# サイドバー: タスク入力フォーム
st.sidebar.header("📝 新規タスク追加")

with st.sidebar.form("add_task_form", clear_on_submit=True):
    task_name = st.text_input("タスク名", placeholder="例: プレゼン資料作成")
    task_duration = st.number_input("所要時間（分）", min_value=5, max_value=480, value=30, step=5)
    
    # 期日の入力（日付と時刻を別々に）
    task_date = st.date_input("期日（日付）", value=datetime.today())
    task_time = st.time_input("期日（時刻）", value=datetime.now().time())
    
    task_category = st.selectbox("カテゴリ", ["仕事", "プライベート", "学習", "健康", "その他"])
    
    submitted = st.form_submit_button("➕ タスクを追加", use_container_width=True)
    
    if submitted:
        if task_name.strip() == "":
            st.sidebar.error("タスク名を入力してください")
        else:
            # 日付と時刻を結合
            task_deadline = datetime.combine(task_date, task_time)
            
            # 新しいタスクを追加
            new_task = {
                "タスク名": task_name,
                "所要時間": task_duration,
                "期日": task_deadline,
                "カテゴリ": task_category,
                "完了": False
            }
            st.session_state.tasks_df = pd.concat(
                [st.session_state.tasks_df, pd.DataFrame([new_task])],
                ignore_index=True
            )
            save_tasks(st.session_state.tasks_df)
            st.sidebar.success(f"✅ 「{task_name}」を追加しました！")

# サイドバー統計情報
st.sidebar.markdown("---")
st.sidebar.subheader("📊 統計情報")
if not st.session_state.tasks_df.empty:
    total_tasks = len(st.session_state.tasks_df)
    completed_tasks = st.session_state.tasks_df["完了"].sum()
    pending_tasks = total_tasks - completed_tasks
    
    st.sidebar.metric("総タスク数", total_tasks)
    st.sidebar.metric("完了", completed_tasks)
    st.sidebar.metric("未完了", pending_tasks)
    
    if total_tasks > 0:
        completion_rate = (completed_tasks / total_tasks) * 100
        st.sidebar.progress(completion_rate / 100)
        st.sidebar.caption(f"完了率: {completion_rate:.1f}%")
else:
    st.sidebar.info("タスクがありません")

# メイン画面: 今日の優先タスク（上位3つ）
st.header("🔥 今日の優先タスク TOP3")

# 未完了タスクのみを抽出
if not st.session_state.tasks_df.empty:
    df_pending = st.session_state.tasks_df[st.session_state.tasks_df["完了"] == False].copy()
    
    if not df_pending.empty:
        # 各タスクの優先度スコアを計算
        df_pending["優先度スコア"] = df_pending.apply(
            lambda row: calculate_priority_score(row["期日"], row["所要時間"]),
            axis=1
        )
        
        # スコアの高い順にソート
        df_pending = df_pending.sort_values("優先度スコア", ascending=False)
        
        # 上位3つを取得
        top_tasks = df_pending.head(3)
        
        # 優先タスクを目立つように表示
        for idx, (_, row) in enumerate(top_tasks.iterrows(), 1):
            # 期日までの残り時間を計算
            time_left = row["期日"] - datetime.now()
            hours_left = time_left.total_seconds() / 3600
            
            # 緊急度に応じて色を変える
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
            
            # タスクカードとして表示
            with st.container():
                col1, col2, col3 = st.columns([0.5, 5, 2])
                
                with col1:
                    st.markdown(f"## {idx}")
                
                with col2:
                    st.markdown(f"### {color} {row['タスク名']}")
                    st.write(f"📂 {row['カテゴリ']} | ⏱️ {row['所要時間']}分 | 📅 {row['期日'].strftime('%m/%d %H:%M')}")
                
                with col3:
                    st.metric("優先度スコア", f"{row['優先度スコア']:.1f}")
                    st.caption(urgency_text)
                
                st.divider()
    else:
        st.success("🎉 すべてのタスクが完了しています！")
else:
    st.info("タスクを追加して始めましょう")

# メイン画面: 全タスクリスト
st.header("📋 全タスクリスト")

# タブで完了/未完了を切り替え
tab1, tab2 = st.tabs(["未完了タスク", "完了済みタスク"])

with tab1:
    if not st.session_state.tasks_df.empty:
        df_pending = st.session_state.tasks_df[st.session_state.tasks_df["完了"] == False].copy()
        
        if not df_pending.empty:
            # 優先度スコアを計算してソート
            df_pending["優先度スコア"] = df_pending.apply(
                lambda row: calculate_priority_score(row["期日"], row["所要時間"]),
                axis=1
            )
            df_pending = df_pending.sort_values("優先度スコア", ascending=False)
            
            # タスクごとに表示
            for original_idx in df_pending.index:
                row = st.session_state.tasks_df.loc[original_idx]
                
                col1, col2, col3 = st.columns([0.5, 6, 1.5])
                
                with col1:
                    # 完了チェックボックス
                    completed = st.checkbox("", key=f"check_{original_idx}", value=False)
                    if completed:
                        st.session_state.tasks_df.loc[original_idx, "完了"] = True
                        save_tasks(st.session_state.tasks_df)
                        st.rerun()
                
                with col2:
                    st.markdown(f"**{row['タスク名']}**")
                    st.caption(f"📂 {row['カテゴリ']} | ⏱️ {row['所要時間']}分 | 📅 {row['期日'].strftime('%Y/%m/%d %H:%M')}")
                
                with col3:
                    # 削除ボタン
                    if st.button("🗑️", key=f"del_{original_idx}"):
                        st.session_state.tasks_df = st.session_state.tasks_df.drop(original_idx).reset_index(drop=True)
                        save_tasks(st.session_state.tasks_df)
                        st.rerun()
                
                st.divider()
        else:
            st.info("未完了のタスクはありません")
    else:
        st.info("タスクがありません")

with tab2:
    if not st.session_state.tasks_df.empty:
        df_completed = st.session_state.tasks_df[st.session_state.tasks_df["完了"] == True].copy()
        
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
                    # 削除ボタン
                    if st.button("🗑️", key=f"del_comp_{original_idx}"):
                        st.session_state.tasks_df = st.session_state.tasks_df.drop(original_idx).reset_index(drop=true)
                        save_tasks(st.session_state.tasks_df)
                        st.rerun()
                
                st.divider()
        else:
            st.info("完了済みのタスクはありません")
    else:
        st.info("タスクがありません")

# フッター
st.markdown("---")
st.caption("💡 優先度スコアは、期日までの残り時間と所要時間から自動計算されます")
