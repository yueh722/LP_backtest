import pandas as pd
import numpy as np
import csv
import os
import Backtest_v3 as btv3
from decimal import Decimal


is_file_round = False

is_show_round = False #True
base = 0

def get_data(start_date, end_date):

    _candles = pd.read_csv('./uniswap_backtest_subgraph.csv')

    #tmp_df = pd.DataFrame(_candles)
    #df = tmp_df.sort_values(by='periodStartUnix', ascending=False)

    df = pd.DataFrame(_candles)

    df['date'] = pd.to_datetime(df['periodStartUnix'], unit='s')
    df['Date'] = df['date']
    df.set_index('Date', inplace=True)

            
    decimal0 = int(df['pool.token0.decimals'].iloc[0])
    decimal1 = int(df['pool.token1.decimals'].iloc[0])
    decimal = decimal1 - decimal0

    # Convert the columns to numeric values
    df['fg0']=((df['feeGrowthGlobal0X128'].apply(float))/(2**128))/(10**decimal0)
    df['fg1']=((df['feeGrowthGlobal1X128'].apply(float))/(2**128))/(10**decimal1)

    #df['fg0'] = ((df['feeGrowthGlobal0X128'].apply(lambda x: Decimal(x)) / (2 ** 128)) / (10 ** decimal0))
    #df['fg1'] = ((df['feeGrowthGlobal1X128'].apply(lambda x: Decimal(x)) / (2 ** 128)) / (10 ** decimal1))

    
    #Calculate F0G and F1G (fee earned by an unbounded unit of liquidity in one period)
    
    #df['fg0shift'] = (df['fg0'].shift(-1))
    #df['fg1shift'] = (df['fg1'].shift(-1))
    df['fg0shift'] = (df['fg0'].shift(1))
    df['fg1shift'] = (df['fg1'].shift(1))

    
    df['fee0token'] = (df['fg0'] - df['fg0shift'])
    df['fee1token'] = (df['fg1'] - df['fg1shift'])

    
    #df.to_csv(f'uniswap_backtest_subgraph_start.csv', index=False)
    return df

def simulate_trades(dpd, balance, add, sub):

    in_trade = False
    trades = []
    lp_trades = []
    stop_loss = None
    take_profit = None
    trail_price = None

    dpd['price0'] = None
    dpd['amount0'] = None
    dpd['amount1'] = None
    dpd['amount0unb'] = None
    dpd['amount1unb'] = None
    dpd['ActiveLiq'] = None
    dpd['myliquidity'] = None
    dpd['myfee0'] = None
    dpd['myfee1'] = None
    dpd['type'] = None

    for i, row in dpd.iterrows():
        if row['signal'] == 1 and not in_trade:
            in_trade = True
            
            entry_price = row['close']
            #stop_loss = entry_price * (1 - buy_stop_loss) if stop_loss_and_tp else None
            #take_profit = entry_price * (1 + buy_tp) if stop_loss_and_tp else None
            stop_loss = entry_price - sub
            take_profit = entry_price + add
            start_date = row["date"]
            start_row  = row[0]
            row['type'] = 1
            

            dpd.at[i] = btv3.backtest(row, stop_loss, take_profit, balance, base)

            round = len(trades) + 1

            continue

        if in_trade and (row['high'] >= take_profit or row['low'] <= stop_loss) : 
            # 超出上下限(出場)
            row['entry_price'] = entry_price
            row['type'] = 3

            dpd.at[i] = btv3.backtest(row, stop_loss, take_profit, balance, base)
            exit_price = row['close']
            end_date = row["date"]
            end_row  = row[0]

            profit = (exit_price - entry_price) * balance #/ entry_price
            #balance += profit
            trades.append(profit)

            dict = btv3.calculate_report_round(dpd.loc[start_date:])
            net_profit = dict["total_myfee"] + profit
            lp_trades.append(net_profit)

            result_dict_round = {
                "Round" : round,

                "Start Date" : start_date,
                "Etry Price" : entry_price,
                "Stop Loss" : stop_loss,
                "Take Profit" : take_profit,
                "Balance": balance,

                "End Date" : end_date,
                "Exit Price" : exit_price,

                "Total Trades" : dict["total_trades"],
                "Net Profit" : net_profit,
                "Total Fee" : dict["total_myfee"],
                "Market Profit" : profit,
                "start_row" : start_row,
                "end_row" : end_row,
            }
            if is_show_round :
                btv3.show_report_round( result_dict_round)
                dpd.to_csv(f'dpd_start1_{round}.csv', index=False)

            if is_file_round :
                report_round_filename = 'report_round.csv'
                if round==1:
                    with open(report_round_filename, mode='w', newline='') as file:
                        writer = csv.DictWriter(file, fieldnames=result_dict_round.keys())
                        writer.writeheader()
                        writer.writerow(result_dict_round)
                else:
                    # Append result_dict_round to file
                    with open(report_round_filename, mode='a', newline='') as file:
                        writer = csv.DictWriter(file, fieldnames=result_dict_round.keys())
                        writer.writerow(result_dict_round)

            #if(row['high'] >= take_profit):
            #    print(f"出場價格 : {exit_price} 超出上限 : high[{row['high']}] >= take_profit[{take_profit}] \n")
            #else:
            #    print(f"出場價格 : {exit_price} 低於下限 : low[{row['low']}] <= stop_loss[{stop_loss}] \n")
            
            in_trade = False
            stop_loss = None
            take_profit = None
            
        elif in_trade and (row['high'] < take_profit and row['low'] > stop_loss) : 
            #已進場沒有超出上下限
            row["entry_price"] = entry_price
            row['type'] = 2
            dpd.at[i] = btv3.backtest(row, stop_loss, take_profit, balance, base)
            

    #print(lp_trades)
    report_overall_filename = 'report_overall.csv'
    print(f'LP 回測結果 =====================================\n')
    #result_dict_LP = btv3.calculate_report_metrics(lp_trades)
    result_dict_LP = analyze_trades("LP", trades, lp_trades, add, sub, balance)
    show_report( dpd["date"].iloc[0], dpd["date"].iloc[-1], result_dict_LP)

    file_exists = os.path.exists(report_overall_filename)

    # Open the file in 'a' (append) mode if it exists, otherwise in 'w' (write) mode
    with open(report_overall_filename, mode='a' if file_exists else 'w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=result_dict_LP.keys())
    
        # Write the header only if the file is newly created
        if not file_exists:
            writer.writeheader()
    
        writer.writerow(result_dict_LP)


def analyze_trades(type, trades, lp_trades, add, sub, balance, annual_risk_free_rate=0.03):
    

    net_profit = sum(lp_trades)
    market_profit = sum(trades)
    total_fee = net_profit - market_profit

    total_closed_trades = len(lp_trades)
    percent_profitable = sum(1 for t in lp_trades if t > 0) / total_closed_trades

    positive_trades = [t for t in lp_trades if t > 0]
    negative_trades = [t for t in lp_trades if t < 0]

    profit_factor = sum(positive_trades) / abs(sum(negative_trades)) if negative_trades else np.nan

    max_drawdown = min(sum(lp_trades[:i]) - min(lp_trades[i:]) for i in range(len(lp_trades)))
    avg_trade = net_profit / total_closed_trades
    avg_bars_in_trades = len(lp_trades) / total_closed_trades

    std_dev = np.std(lp_trades)
    if len(negative_trades) >= 2:
        downside_dev = np.std(negative_trades)
    else:
        downside_dev = np.nan
    excess_return = avg_trade
    risk_free_return = annual_risk_free_rate / 252  # Assuming daily trading
    
    
    # 檢查std_dev是否為0
    if np.isclose(std_dev, 0.0):  # 使用np.isclose處理小數點精度問題
        sharpe_ratio = np.nan
    else:
        sharpe_ratio = (excess_return - risk_free_return) / std_dev

    if np.isclose(downside_dev, 0.0):  # 使用np.isclose處理小數點精度問題
        sortino_ratio = np.nan
    else:
        sortino_ratio = (excess_return - risk_free_return) / downside_dev

    
    #return net_profit, total_closed_trades, percent_profitable, profit_factor, max_drawdown, avg_trade, avg_bars_in_trades
    result_dict = {
        "Type" : type, #"Market",
        "Net Profit": net_profit,
        "Total Closed Trades": total_closed_trades,
        "Percent Profitable": percent_profitable,
        "Profit Factor": profit_factor,
        "Max Drawdown": max_drawdown,
        "Avg Trade": avg_trade,
        "Avg # Bars in Trades": avg_bars_in_trades,
        "Sharpe Ratio": sharpe_ratio,
        "Sortino Ratio": sortino_ratio,

        "Total Fee": total_fee,
        "Market Profit": market_profit,
        "Add" : add,
        "Sub" : sub,
        "Balance" : balance,
    }

    return result_dict


def show_report( start_date, end_date, result_dict) :
    #sharpe_ratio, sortino_ratio = calculate_ratios(trades)
    #print(f"\n==============================================\n")
    print(f"Start Date: {start_date}")
    print(f"End Date  : {end_date}\n")
    print(f"Net Profit: {result_dict['Net Profit']:.2f}")
    print(f"Total Closed Trades: {result_dict['Total Closed Trades']}")
    print(f"Percent Profitable : {result_dict['Percent Profitable']:.2%}")
    print(f"Profit Factor: {result_dict['Profit Factor']:.2f}")
    print(f"Max Drawdown : {result_dict['Max Drawdown']:.2f}")
    print(f"Avg Trade    : {result_dict['Avg Trade']:.2f}")
    #print(f"Avg # Bars in Trades: {result_dict['Avg # Bars in Trades']:.2f}")
    print(f"Sharpe Ratio : {result_dict['Sharpe Ratio']:.2f}")
    print(f"Sortino Ratio: {result_dict['Sortino Ratio']:.2f}\n")

    print(f"Total Fee: {result_dict['Total Fee']:.6f}n")
    print(f"Market Profit: {result_dict['Market Profit']:.6f}\n")
 
    print(f"Balance : {result_dict['Balance']:.0f}")
    print(f"Add     : {result_dict['Add']:.0f}")
    print(f"Sub     : {result_dict['Sub']:.0f}\n")
    print(f"\n==============================================\n")
    

