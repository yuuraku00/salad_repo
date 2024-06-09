import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import datetime
import calendar
import openai

# Streamlit secretsからAPIキーと設定を取得
openai.api_key = st.secrets["OpenAIAPI"]["openai_api_key"]
chatbot_setting = st.secrets["AppSettings"]["chatbot_setting"]

# データフレームの初期化
@st.cache(allow_output_mutation=True)
def get_data():
    return pd.DataFrame(columns=["職員番号", "日付", "摂取グラム数"])

data = get_data()

def generate_comment(intake):
    prompt = f"{chatbot_setting}\n\nToday's salad intake is {intake} grams. Please provide a positive and encouraging comment."

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ]
    )

    comment = response['choices'][0]['message']['content'].strip()
    return comment

# ログインセクション
st.title("サラダ摂取量記録アプリ")
employee_id = st.text_input("職員番号を入力してください (6桁)", max_chars=6)

if employee_id:
    st.write(f"職員番号: {employee_id}")

    # 毎日の摂取量記録
    intake = st.number_input("今日のサラダ摂取量 (グラム)を入力してください", min_value=0)
    record_button = st.button("記録")

    if record_button:
        new_record = {"職員番号": employee_id, "日付": datetime.date.today(), "摂取グラム数": intake}
        data = pd.concat([data, pd.DataFrame([new_record])], ignore_index=True)
        data.to_csv("salad_intake.csv", index=False)
        st.success("記録が追加されました")

        # OpenAI APIを使ってコメントを生成
        try:
            comment = generate_comment(intake)
            st.write(comment)
        except Exception as e:
            st.error(f"コメントの生成に失敗しました: {e}")

    # 月間累計摂取量の表示
    if not data.empty:
        data["日付"] = pd.to_datetime(data["日付"])
        user_data = data[data["職員番号"] == employee_id]
        if not user_data.empty:
            user_data = user_data.set_index("日付").resample("D").sum().fillna(0)
            user_data["累計摂取グラム数"] = user_data["摂取グラム数"].cumsum()

            st.write("月間累計摂取量")
            st.write("この表は各月のサラダ摂取量を積み上げで折れ線グラフにしています")
            fig, ax = plt.subplots()
            ax.plot(user_data.index, user_data["累計摂取グラム数"], marker='o', linestyle='-')
            ax.set_title("graph")
            ax.set_xlabel("date")
            ax.set_ylabel("(g)")
            st.pyplot(fig)

            # カレンダー表示
            st.write("摂取日カレンダー")
            st.write("サラダを食べた日に印が付きます。サラダ習慣を身につけましょう。")
            current_month = datetime.date.today().replace(day=1)
            first_day, last_day = calendar.monthrange(current_month.year, current_month.month)
            days = pd.date_range(start=current_month, periods=last_day, freq='D')
            days_df = pd.DataFrame(days, columns=["日付"])
            days_df["摂取グラム数"] = 0
            days_df.set_index("日付", inplace=True)
            days_df.update(user_data)

            fig, ax = plt.subplots(figsize=(10, 6))
            ax.axis('off')
            table_data = []

            for i in range(6):
                week = []
                for j in range(7):
                    day = i * 7 + j - first_day + 1
                    if day > 0 and day <= last_day:
                        if days_df.iloc[day - 1]["摂取グラム数"] > 0:
                            week.append(f"{day}\n〇")
                        else:
                            week.append(f"{day}")
                    else:
                        week.append("")
                table_data.append(week)

            col_labels = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
            ax.table(cellText=table_data, cellLoc='center', loc='center', colLabels=col_labels, colColours=['#f0f0f0']*7)
            st.pyplot(fig)

        else:
            st.write("まだデータがありません。")

    # ランキング表示
    if not data.empty:
        st.write("月間サラダ摂取量ランキング")
        st.write("あなたの今月のサラダ摂取量の累計が、社内でどれくらいの位置にいるかがわかります。社内ランキングを見て、社内の仲間と一緒に盛り上がりましょう。")
        monthly_rank = data.groupby(["職員番号", data["日付"].dt.to_period("M")])["摂取グラム数"].sum().reset_index()
        monthly_rank = monthly_rank.groupby("職員番号")["摂取グラム数"].sum().sort_values(ascending=False).reset_index()

        # 自分の順位を計算
        rank = monthly_rank[monthly_rank["職員番号"] == employee_id].index[0] + 1
        st.write(f"あなたの順位: {rank}位")

        # ランキング表示
        st.dataframe(monthly_rank)

        # 自分のデータを強調表示
        monthly_rank["順位"] = monthly_rank.index + 1
        st.dataframe(monthly_rank.style.apply(lambda x: ["background-color: yellow" if x["職員番号"] == employee_id else "" for i in x], axis=1))
