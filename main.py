import strategy as st
import simulate as sl

def main():

    # 設定回測參數
    start_date = "2021-08-01"
    end_date   = "2023-07-31"

    #start_date = "2022-07-10"
    #end_date   = "2023-07-18"
    balance = 100

    # 載入回測資料
    df = sl.get_data( start_date, end_date)

    # 策略計算
    df = st.my_strategy(df)

    # 回測  'signal' = 1
    df = df.loc[start_date:end_date]

    add = 30
    sub = 5
    sl.simulate_trades(df, balance, add, sub)


if __name__ == "__main__":
    main()
